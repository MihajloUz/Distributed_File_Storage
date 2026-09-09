import os
import httpx
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File, Form, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class UserAuth(BaseModel):
    email: EmailStr
    password: str

def get_db_connection():
    print("HOST:", os.getenv("POSTGRES_HOST"))
    print("PORT:", os.getenv("POSTGRES_PORT"))
    print("USER:", os.getenv("POSTGRES_USER"))
    print("DB:", os.getenv("POSTGRES_DB"))

    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
        dbname=os.getenv("POSTGRES_DB", "dfs_db"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

@app.get("/", response_class=HTMLResponse)
async def get_home_page(
    request: Request,
    session_id: str | None = Cookie(default=None)
):
    if session_id is None:
        return RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER
        )
    return templates.TemplateResponse (
            request=request, 
            name="main.html" 
    )

@app.get("/sign_up", response_class=HTMLResponse)
async def get_signup_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="sign_up_page.html"
    )
@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse (
            request=request, 
            name="login_page.html" 
    )


@app.post("/api/sign_up")
def sign_up_page(
        data: UserAuth
):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(query, (data.email, data.password))

        conn.commit()
        cursor.close()

        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        if conn:
            conn.rollback()
        return RedirectResponse(url="/sign_up?error=db_error", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        if conn:
            conn.close()

@app.post("/api/login")
async def login_user(
    data: UserAuth
):
    conn = None 
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (data.email, data.password))
        existing_user = cursor.fetchone()
        cursor.close()

        if existing_user:
            # creating cookie here
            async with httpx.AsyncClient() as client:
                response = await client.post("http://rust:8001/login_successful", json={"email": data.email})
            rust_data = response.json()
            if not rust_data["success"]:
                return rust_data
                
            redirect = RedirectResponse(
                url="/",
                status_code=status.HTTP_303_SEE_OTHER
            )

            session_id = rust_data["session_id"]
            redirect.set_cookie(
                key="session_id",
                value=session_id,
                httponly=True,
                path="/"
            )
            return redirect 
        else:
            return RedirectResponse(url="/login?error=invalid_credentials", status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"ERROR TYPE: {type(e)}")
        print(f"ERROR: {e}")
        return RedirectResponse(url="/login?error=server_error", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        if conn:
            conn.close()

# Константи для завантаження
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...)
):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    total_bytes_written = 0

    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_bytes_written += len(chunk)
                if total_bytes_written > MAX_FILE_SIZE:
                    buffer.close()
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return RedirectResponse(
                        url="/?error=file_too_large",
                        status_code=status.HTTP_303_SEE_OTHER
                    )
                buffer.write(chunk)

        return RedirectResponse(
            url="/?success=upload_complete",
            status_code=status.HTTP_303_SEE_OTHER
        )
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"Upload file: {e}")
        return RedirectResponse(
            url="/?error=upload_failed",
            status_code=status.HTTP_303_SEE_OTHER
        )

#@app.get("/rust")
#async def get_rust_response():
#    async with httpx.AsyncClient() as client:
#        response = await client.get("http://rust:8001/rust")
#    return HTMLResponse(
#        content=response.text,
#        status_code=response.status_code
#    )

# later create the endpoint for talking with rust on user sending/reading files 
