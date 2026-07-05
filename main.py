from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db

# Lifespan context to initialize DB on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="SaveMonstera API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://savemonstera.onrender.com", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Import routers (we will create these next)
from routers import auth, expenses, upload, ai_agent, settings, export, dashboard

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(ai_agent.router, prefix="/api/ai", tags=["AI Agent"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Frontend routes
@app.get("/")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.get("/terms")
async def terms_page(request: Request):
    return templates.TemplateResponse(request=request, name="terms.html")

@app.get("/dashboard")
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/add_expense")
async def add_expense_page(request: Request):
    return templates.TemplateResponse(request=request, name="add_expense.html")

@app.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse(request=request, name="history.html")

@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse(request=request, name="settings.html")
