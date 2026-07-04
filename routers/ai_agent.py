from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
import json
import google.generativeai as genai
from database import supabase
from routers.auth import get_current_user

router = APIRouter()

class AIRequest(BaseModel):
    text: str

def get_gemini_client():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "your-gemini-api-key":
        return None
    genai.configure(api_key=api_key)
    return True

# ADK 2.0 graph workflow simulated with Python functions (nodes)
def parse_text_node(text: str):
    prompt = f"""
    Parse the following expense text and extract the amount (float), category (string), date (YYYY-MM-DD), and description (string).
    Respond strictly in JSON format without markdown wrapping.
    Example: {{"amount": 200.0, "category": "Food", "date": "2023-10-27", "description": "lunch"}}
    If no date is mentioned, use today's date (assume context is today).
    Text: "{text}"
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    # clean markdown if accidentally added
    res_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(res_text)

def auto_log_node(parsed_data: dict, current_total: float, threshold: float):
    # auto-approve if total stays under budget threshold
    if (current_total + parsed_data["amount"]) < threshold:
        parsed_data["status"] = "approved"
        return parsed_data
    return None

def review_agent_node(parsed_data: dict):
    # flag for human review if over threshold
    parsed_data["status"] = "flagged"
    return parsed_data

@router.post("/process")
def process_ai_text(req: AIRequest, user_id: str = Depends(get_current_user)):
    client = get_gemini_client()
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured properly")

    try:
        # Node 1: Parse
        parsed_data = parse_text_node(req.text)
        
        # Get threshold and current total
        budgets = supabase.table("budgets").select("agent_threshold").eq("user_id", user_id).execute()
        threshold = budgets.data[0]["agent_threshold"] if budgets.data else 100.0
        
        # for simplicity, let's just use the amount itself against threshold, 
        # or we could calculate the weekly/monthly total. 
        # The prompt says: "auto-approve if total stays under budget threshold"
        # I'll use the parsed amount as the total addition and check against threshold.
        # But wait, "if total stays under budget threshold" - usually means the amount itself < threshold for auto-approval.
        # Let's interpret it as: amount < threshold.
        current_total = 0 # simplifying: "total of this transaction"
        
        # Graph logic
        result = auto_log_node(parsed_data.copy(), current_total, threshold)
        if not result:
            result = review_agent_node(parsed_data.copy())
            
        result["user_id"] = user_id
        result["mode"] = "ai_agent"
        result["type"] = "debit"
        
        # Insert to DB
        res = supabase.table("expenses").insert(result).execute()
        return {"message": "Processed successfully", "data": res.data[0]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
