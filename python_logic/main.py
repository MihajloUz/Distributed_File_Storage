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
            url="/sign_up",
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
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
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

@app.post("/api/upload")
async def upload_file(
    request: Request 
):
    filename = request.headers.get("Filename")
    cookie = request.headers.get("Cookie")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://rust:8001/api/upload",
                content=request.stream(),
                headers={
                    "Filename": filename or "",
                    "Cookie": cookie or ""
                }
            )
        rust_data = response.json()
        if not rust_data["success"]:
            return rust_data # do something in case of ERROR

        file_path = rust_data["full_path"]
        print(file_path) # its returnign the full path now 
        # the task is to append the file onto the main page as loaded one


        return RedirectResponse(url="/login",status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"Upload proxy error: {e}")
        return RedirectResponse(
            url="/?error=server_error", 
            status_code=status.HTTP_303_SEE_OTHER
        )

@app.get("/redirect-to-login")
async def redirect_to_login():
    return RedirectResponse(
        url="/login", 
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
