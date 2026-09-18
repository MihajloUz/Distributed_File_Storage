import os
import httpx
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File, Form, Cookie, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

class UserAuth(BaseModel):
    email: EmailStr
    password: str

class VerificationCode(BaseModel):
    verification_code: str

def get_db_connection():
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
@app.get("/email_verification", response_class=HTMLResponse)
async def get_email_verification_page(request: Request):
    return templates.TemplateResponse (
            request=request, 
            name="email_verification.html" 
    )

@app.get("/view/{file_id}", response_class=HTMLResponse)
async def view_file_page (request: Request, file_id: str):
    return templates.TemplateResponse (
            request=request, 
            name="txt.html",
            context = {"file_id": str(file_id)}
    )

@app.post("/api/sign_up")
async def sign_up_page(
    data: UserAuth
):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT verified FROM email_verification WHERE email_verification.email = %s"
        cursor.execute(query, (data.email, ))
        result = cursor.fetchone()
        
        if result is not None and result[0]:
            query = "INSERT INTO users (email, password) VALUES (%s, %s)"
            cursor.execute(query, (data.email, data.password))
            conn.commit()

            cursor.close()
            return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post("http://rust:8001/api/email_verification", json={"email": str(data.email)})
            rust_data = response.json()
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = "INSERT INTO email_verification (email, verification_code, verified) VALUES (%s, %s, %s)"
            cursor.execute(query, (str(data.email), rust_data["verification_code"], False))
            conn.commit()

            return RedirectResponse(url=f"/email_verification?email={data.email}", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        if conn:
            conn.rollback()
        return RedirectResponse(url="/sign_up?error=db_error", status_code=status.HTTP_303_SEE_OTHER)
    finally:
        if conn:
            conn.close()


@app.post("/api/email_verification")
async def email_verification(
    data: VerificationCode,
    email: EmailStr
):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT verification_code FROM email_verification WHERE email = %s"
        cursor.execute(query, (str(email), ))
        result = cursor.fetchone()
        if result is not None and str(result["verification_code"]) == str(data.verification_code):
            query = "UPDATE email_verification SET verified = TRUE WHERE email = %s"
            cursor.execute(query, (str(email), ))
            conn.commit()
            cursor.close()
            return RedirectResponse(url="/sign_up", status_code=status.HTTP_303_SEE_OTHER)
        else:
            return RedirectResponse(url="/sign_up", status_code=status.HTTP_303_SEE_OTHER)
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

#эндпоинт для аплоаду
@app.post("/api/upload")
async def upload_file(
    request: Request 
):
    filename = request.headers.get("Filename") # python sends the file name 
    cookie = request.headers.get("Cookie") # and the cookie aswell
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://rust:8001/api/upload",
                content=request.stream(),
                headers={
                    "Filename": filename or "", # in case of an empty file name rust would just name it as "Unnamed"
                    "Cookie": cookie or ""
                }
            )
        rust_data = response.json()
        if not rust_data["success"]:
            return JSONResponse(
                content=rust_data,
                status_code = 400
            )
        return JSONResponse(
            content=rust_data,
            status_code = 200
        )

    except Exception as e:
        print(f"Upload proxy error: {e}")
        return RedirectResponse(
            url="/?error=server_error", 
            status_code=status.HTTP_303_SEE_OTHER
        )


#уже есть аккаунт редирект
@app.get("/redirect-to-login")
async def redirect_to_login():
    return RedirectResponse(
        url="/login", 
        status_code=status.HTTP_303_SEE_OTHER
    )

@app.get("/api/files")
async def get_user_files(
    session_id: str | None = Cookie(default=None)
):
    if not session_id:
        return JSONResponse(
            content={
                "success": False,
                "message": "Not authenticated"
            },
            status_code=401
        )
    try:
        async with httpx.AsyncClient() as client:
            rust_response = await client.get(
                "http://rust:8001/api/files",
                cookies={"session_id": session_id}
            )


        if rust_response.status_code != 200:
            content={
                "success": False,
                "message": "Internal Server error" # change the error to smoething more coherent later
            },
            status_code=500

        rust_data = rust_response.json();

        return RedirectResponse(
            url=f"/view/{rust_data["id"]}",
            status_code=status.HTTP_303_SEE_OTHER
        )

        return JSONResponse(content=rust_response.json())
    except Exception as e:
        print(f"Error proxying files request: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error":"Failes to fetch files"}
        )



@app.get("/api/files/{file_id}")
async def download_file(
        file_id: str,
        session_id: str | None = Cookie(default=None)
):
    try:
        async with httpx.AsyncClient() as client:
            rust_response = await client.get(
                f"http://rust:8001/api/files/{file_id}",
                cookies={"session_id": session_id}
            )
        if rust_response.status_code != 200:
            content={
                "success": False,
                "message": "Internal Server error" # change the error to smoething more coherent later
            },
            status_code=500
        return Response(
                content=rust_response.content,
                status_code=rust_response.status_code,
                headers={
                    "Content-Type": rust_response.headers["Content-Type"],
                    "Content-Disposition": rust_response.headers["Content-Disposition"],
                }
            )
    except Exception as e:
        print(f"Error proxying files request: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error":"Failes to fetch files"}
        )


class FileRequest(BaseModel):
    file_id: str

@app.post("/api/view/")
async def view_txt( #remake to be universal with switch( which is 'match' in python ))
        data: FileRequest,
        session_id: str | None = Cookie(default=None)
):
    conn = None
    try:
        rust_response = await client.get(
            f"http://rust:8001/api/files/{data.file_id}",
            cookies={"session_id": session_id}
        )

        content = rust_response.content.decode("utf-8")
        return Response(
            content=content,
            media_type="text/plain"
        )
    except Exception as e:
        print(f"Error proxying files request: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error":"Failes to fetch files"}
        )


