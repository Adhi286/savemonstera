from fastapi import APIRouter, Depends, HTTPException
from database import supabase
from routers.auth import get_current_user
from datetime import datetime

router = APIRouter()

@router.get("/")
def get_dashboard_stats(user_id: str = Depends(get_current_user)):
    try:
        budgets = supabase.table("budgets").select("*").eq("user_id", user_id).execute()
        monthly_limit = budgets.data[0]["monthly_limit"] if budgets.data else 2000.0
        weekly_limit = budgets.data[0]["weekly_limit"] if budgets.data else 500.0
        
        # We fetch all expenses for the user
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
            # 5. Make sure SUM(amount) calculation only includes debit transactions, not credits
            if ex.get("type", "").lower() == "debit":
                date_str = ex.get("date", "")
                amt = float(ex.get("amount", 0.0))
                
                if date_str and date_str.startswith(current_month_str):
                    monthly_total += amt
                    cat = ex.get("category", "Other")
                    category_totals[cat] = category_totals.get(cat, 0) + amt
                    
                if date_str and date_str >= week_ago_str:
                    weekly_total += amt
                    
        # Order by created_at desc so newly uploaded old-date transactions still show up!
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
            "monthly_total": 0, "monthly_limit": 2000, "monthly_remaining": 2000,
            "weekly_total": 0, "weekly_limit": 500, "weekly_remaining": 500,
            "category_breakdown": {}, "recent_activity": []
        }
