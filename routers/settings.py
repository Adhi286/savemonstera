from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import supabase
from routers.auth import get_current_user

router = APIRouter()

class SettingsUpdate(BaseModel):
    weekly_limit: float
    monthly_limit: float
    agent_threshold: float

@router.get("/")
def get_settings(user_id: str = Depends(get_current_user)):
    try:
        response = supabase.table("budgets").select("*").eq("user_id", user_id).execute()
        if not response.data:
            # Create default settings if not exist
            default_data = {
                "user_id": user_id,
                "weekly_limit": 500.0,
                "monthly_limit": 2000.0,
                "agent_threshold": 100.0
            }
            res = supabase.table("budgets").insert(default_data).execute()
            return res.data[0]
        return response.data[0]
    except Exception as e:
        return {"error": str(e), "weekly_limit": 500.0, "monthly_limit": 2000.0, "agent_threshold": 100.0}

@router.post("/")
def update_settings(settings: SettingsUpdate, user_id: str = Depends(get_current_user)):
    try:
        # Check if settings exist
        existing = supabase.table("budgets").select("id").eq("user_id", user_id).execute()
        data = settings.dict()
        data["user_id"] = user_id
        if existing.data:
            res = supabase.table("budgets").update(data).eq("user_id", user_id).execute()
        else:
            res = supabase.table("budgets").insert(data).execute()
        return res.data[0] if res.data else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
