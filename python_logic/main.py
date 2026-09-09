import os
import httpx
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from starlette.responses import TemplateResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024

class UserAuth(BaseModel):
    email: EmailStr
    password: str

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
        dbname=os.getenv("POSTGRES_DB", "dfs_db"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

@app.get("/", response_class=HTMLResponse)
async def get_home_page(request: Request) -> TemplateResponse:
    return templates.TemplateResponse(
        request=request, 
        name="main.html"
    )

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
def sign_up_page(
    email: str = Form(...),
    password: str = Form(...)
):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(query, (email, password))

        conn.commit()
        cursor.close()

        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
        return RedirectResponse(url="/sign_up_page?error=db_error", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        if conn:
            conn.close()

@app.post("/api/login")
def login_user(
    email: str = Form(...),
    password: str = Form(...)
):
    conn = None 
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (email, password))
        existing_user = cursor.fetchone()
        cursor.close()

        if existing_user:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/login_page?error=invalid_credentials", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Database error: {e}")
        return RedirectResponse(url="/login_page?error=server_error", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        if conn:
            conn.close()

@app.get("/rust")
async def get_rust_response():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://rust:8001/rust")
    return HTMLResponse(
        content=response.text,
        status_code=response.status_code
    )

@app.get("/", response_class=HTMLResponse)
async def get_home_page(request: Request) -> TemplateResponse:
    return templates.TemplateResponse(
        request=request,
        name="main.html"
    )

@app.post("/api/upload")
def upload_file(
    user_id: int = Form(...),
    file: UploadFile = File(...)
):
    conn = None
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    total_bytes_written = 0

    try:
        with open(file_path, "wb") as buffer:
            while chunk := file.file.read(1024 * 1024):
                total_bytes_written += len(chunk)
                if total_bytes_written > MAX_FILE_SIZE:
                    buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return RedirectResponse(url="/?error=too_large", status_code=status.HTTP_303_SEE_OTHER)
                buffer.write(chunk)

        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "INSERT INTO user_files (user_id, filename) VALUES (%s, %s);"
        cursor.execute(query, (user_id, file.filename))

        conn.commit()
        cursor.close()

        return RedirectResponse(url="/?success=uploaded", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        if conn:
            conn.rollback()
        if os.path.exists(file_path):
            os.remove(file_path)
        return RedirectResponse(url="/?error=upload_failed", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        if conn:
            conn.close()
            conn.close()