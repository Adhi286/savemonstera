from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from database import supabase
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

class ExpenseCreate(BaseModel):
    date: str
    description: str
    amount: float
    category: str
    type: str

@router.post("/")
def add_expense(expense: ExpenseCreate, user_id: str = Depends(get_current_user)):
    try:
        data = expense.dict()
        data["user_id"] = user_id
        data["mode"] = "manual"
        data["status"] = "approved"
        res = supabase.table("expenses").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
def get_expenses(
    user_id: str = Depends(get_current_user),
    mode: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None)
):
    try:
        query = supabase.table("expenses").select("*").eq("user_id", user_id).order("date", desc=True)
        if mode:
            query = query.eq("mode", mode)
        if category:
            query = query.eq("category", category)
        if date_from:
            query = query.gte("date", date_from)
        if date_to:
            query = query.lte("date", date_to)
            
        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        return []

@router.get("/dashboard-stats")
def get_dashboard_stats(user_id: str = Depends(get_current_user)):
    try:
        budgets = supabase.table("budgets").select("*").eq("user_id", user_id).execute()
        monthly_limit = budgets.data[0]["monthly_limit"] if budgets.data else 2000.0
        weekly_limit = budgets.data[0]["weekly_limit"] if budgets.data else 500.0
        
        # We fetch all expenses for the user and filter in Python since SQLite mock has limited query builder
        expenses_req = supabase.table("expenses").select("*").eq("user_id", user_id).execute()
        all_expenses = expenses_req.data if expenses_req.data else []
        
        now = datetime.now()
        current_month_str = now.strftime("%Y-%m")
        # simple weekly check: past 7 days
        from datetime import timedelta
        week_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        
        monthly_total = 0.0
        weekly_total = 0.0
        category_totals = {}
        
        for ex in all_expenses:
            if ex.get("type") == "debit":
                date_str = ex.get("date", "")
                amt = ex.get("amount", 0.0)
                
                if date_str.startswith(current_month_str):
                    monthly_total += amt
                    cat = ex.get("category", "Other")
                    category_totals[cat] = category_totals.get(cat, 0) + amt
                    
                if date_str >= week_ago_str:
                    weekly_total += amt
                    
        recent = supabase.table("expenses").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
        
        return {
            "monthly_total": monthly_total,
            "monthly_limit": monthly_limit,
            "monthly_remaining": monthly_limit - monthly_total,
            "weekly_total": weekly_total,
            "weekly_limit": weekly_limit,
            "weekly_remaining": weekly_limit - weekly_total,
            "category_breakdown": category_totals,
            "recent_activity": recent.data if recent.data else []
        }
    except Exception as e:
        return {
            "monthly_total": 0, "monthly_limit": 2000.0, "monthly_remaining": 2000.0,
            "weekly_total": 0, "weekly_limit": 500.0, "weekly_remaining": 500.0,
            "category_breakdown": {}, "recent_activity": []
        }
