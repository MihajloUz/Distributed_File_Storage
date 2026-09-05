import psycopg2
# import asyncpg
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

app = FastAPI()

DB_CONFIG = {
    'dbname':'dfs_db',
    'user':'postgres',
    'password':'password_for_db',
    'host':'localhost',
    'port':'5432'
}

class UserAuth(BaseModel):
    email: EmailStr
    password: str

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.get("/sign_up_page", response_class=HTMLResponse)
async def get_signup_page(
    request: Request
)-> TemplateResponse:
   return templates.TemplateResponse(
        request=request, 
        name="register.html"
    )
@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})