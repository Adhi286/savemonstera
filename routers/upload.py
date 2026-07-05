from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import pandas as pd
import pdfplumber
import io
from typing import List, Dict, Any
from database import supabase
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

def clean_date(val) -> str:
    try:
        if pd.isna(val): return None
        return pd.to_datetime(val).strftime('%Y-%m-%d')
    except:
        return None

def clean_amount(val) -> float:
    try:
        if pd.isna(val): return 0.0
        val_str = str(val)
        # Keep only digits, decimals, and negative signs
        cleaned = ''.join(c for c in val_str if c.isdigit() or c in '.-')
        if not cleaned or cleaned == '.' or cleaned == '-': return 0.0
        return abs(float(cleaned))
    except:
        return 0.0

@router.post("/")
async def upload_statement(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    filename = file.filename.lower()
    content = await file.read()
    
    # Max size check (5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    valid_rows = []
    
    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            valid_rows = parse_dataframe(df)
        elif filename.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content))
            valid_rows = parse_dataframe(df)
        elif filename.endswith(".pdf"):
            valid_rows = parse_pdf(content)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        if not valid_rows:
            return {"message": "No valid transaction rows found", "imported": 0, "skipped": 0, "failed": 0}

        # Insert to DB
        inserts = []
        for row in valid_rows:
            row["user_id"] = user_id
            row["mode"] = "file_upload"
            row["status"] = "approved"
            row["category"] = "Other" # Basic default, AI mode can do better
            inserts.append(row)
            
        res = supabase.table("expenses").insert(inserts).execute()
        
        return {
            "message": "File processed successfully",
            "imported": len(res.data) if res.data else 0,
            "skipped": 0,
            "failed": 0
        }
    except Exception as e:
        return {"error": str(e), "imported": 0, "skipped": 0, "failed": 1}

def parse_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    # Attempt to find date, description, amount columns
    # This is a very naive heuristics based parser
    rows = []
    cols = [str(c).lower() for c in df.columns]
    
    date_col = next((c for c in cols if 'date' in c), None)
    desc_col = next((c for c in cols if 'desc' in c or 'particular' in c or 'narr' in c), None)
    amt_col = next((c for c in cols if 'amount' in c or 'debit' in c or 'credit' in c or 'withdrawal' in c), None)
    
    if not (date_col and desc_col and amt_col):
        # Fallback to column index if no headers found
        if len(cols) >= 3:
            date_col, desc_col, amt_col = cols[0], cols[1], cols[2]
        else:
            return rows

    for idx, row in df.iterrows():
        d = clean_date(row.get(df.columns[cols.index(date_col)] if date_col in cols else date_col))
        amt = clean_amount(row.get(df.columns[cols.index(amt_col)] if amt_col in cols else amt_col))
        desc = str(row.get(df.columns[cols.index(desc_col)] if desc_col in cols else desc_col))
        
        if d and amt > 0:
            type_val = "debit" if "debit" in amt_col or "withdrawal" in amt_col else "credit"
            # simple heuristic: if there's a withdrawal and deposit column, check which has value
            rows.append({
                "date": d,
                "description": desc[:255] if desc else "Unknown",
                "amount": amt,
                "type": type_val
            })
    return rows

def parse_pdf(content: bytes) -> List[Dict[str, Any]]:
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 3: continue
                    # heuristic: first column date, second desc, third/fourth amount
                    d = clean_date(row[0])
                    if d:
                        amt = 0.0
                        for cell in row[2:]:
                            a = clean_amount(cell)
                            if a > 0:
                                amt = a
                                break
                        if amt > 0:
                            desc = str(row[1]) if row[1] else "Unknown"
                            rows.append({
                                "date": d,
                                "description": desc[:255],
                                "amount": amt,
                                "type": "debit" # Assuming debit for simplicity in PDF
                            })
    return rows
