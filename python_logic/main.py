import os
import httpx
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DB_CONFIG = {
    'dbname':'dfs_db',
    'user':'postgres',
    'password':'password_for_db',
    'host':'db',
    'port':'5432'
}

class UserAuth(BaseModel):
    email: EmailStr
    password: str

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

@app.get("/", response_class=HTMLResponse)
async def get_signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="main.html"
    )

# /api/upload

@app.get("/sign_up_page", response_class=HTMLResponse)
async def get_signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="sign_up_page.html"
    )
@app.get("/login_page", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse (
            request=request, 
            name="login_page.html" 
    )

@app.post("/api/sign_up_page")
def sign_up_page(user: UserAuth):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(query, (user.email, user.password))

        conn.commit()
        cursor.close()

        return JSONResponse( # краще для пайтона самому перенаправляти на іншу сторіку, а не кидати це на джс
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "Registration successful",
                "redirect_url": "/main" # 
            }
        )
    except Exception as e:
        if conn:
            conn.rollback()
            print(f"Database error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error"
            )
    finally:
        if conn:
            conn.close()

@app.post("/api/login")
def login_user(user: UserAuth):
    conn = None 
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (user.email, user.password))
        existing_user = cursor.fetchone()

        cursor.close()

        if existing_user:
            # json with user email
            return JSONResponse( # тут так само, просто перенаправити в пайтоні. а не в джс
                status_code=status.HTTP_200_OK,
                content={
                    "success": True,
                    "message": "Login successful",
                    "redirect_url": "/main"
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong email or password"
            )
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server error"
        )
    finally:
        if conn:
            conn.close()

# тут будеш отримувати повідомлення про те, чи вийшло в мене завантажити файл від користувача  


# тут будеш отримувати дані з бд про файли користувача, які є на сервері.
# Ну і генерувати сторінку з показом тих файлів типу.
# Чи може я буду цим займатись.
# Короче ще обсудимо

# я тут трошки подивлюсь як працюють повідомлення між растом і пайтоном
@app.get("/rust") # короче ця хуйня відправляє повідомлення на порт :8001, я на расті ловлю повідомлення про сторінку(в цьому випадку це "/rust") і запускаю свої функції якісь. потім просто відправляю тобі сторінку, яку потрібно завантажити. і ти на пайтоні вже завантажуєш її 
async def get_rust_response():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://rust:8001/rust")
    return HTMLResponse(
        content=response.text,
        status_code=response.status_code
    )
