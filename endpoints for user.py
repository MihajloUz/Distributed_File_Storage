import os
import shutil
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import TemplateResponse
from pydantic import BaseModel, EmailStr

app = FastAPI()
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024

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

@app.get("/Sign_up_page", response_class=HTMLResponse)
async def get_signup_page(
    request: Request
):
   return templates.TemplateResponse(
        request=request, 
        name="Sing_up_page.html"
    )
@app.get("/login_page", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.post("/api/Sign_up_page")
def sign_up_page(user: UserAuth):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "INSERT INTO users (email, password) VALUES (%s, %s)"
        cursor.execute(query, (user.email, user.password))

        conn.commit()
        cursor.close()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "message": "Registration successful",
                "redirect_url": "/main"
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
    conn = True
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM users WHERE email = %s AND password = %s"
        cursor.execute(query, (user.email, user.password))
        existing_user = cursor.fetchone()

        cursor.close()

        if existing_user:
            return JSONResponse(
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

#загрузка файлов эндпоинты
@app.get("/main", response_model=HTMLResponse)
async def get_main_page(request: Request) -> TemplateResponse:
    return templates.TemplatesResponse(request=request, name="main.html")

@app.post("/api/upload")
def upload_file(file: UploadFile = File(...)):
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size too large. Max size: 10GB"
        )

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
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="The file exceeds the 10 GB limit."
                    )
                buffer.write(chunk)
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            INSERT INTO user_files (filename, filepath, file_size)
            VALUES (%s, %s, %s)
            RETURNING id;
        """
        cursor.execute(query, (file.filename, file_path, total_bytes_written))
        file_id = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={"message": "File upload successful!", "id": file_id}
        )

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, 
                            detail="Error uploading the file")

#отримати список завантажених файлів
@app.get("/api/files")
def get_files_list():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT id, filename, file_size, uploaded_at FROM user_files ORDER BY id DESC"
    cursor.execute(query)
    files = cursor.fetchall()
    
    cursor.close()
    conn.close()

    for f in files:
        f['uploaded_at'] = f['uploaded_at'].strftime("%Y-%m-%d %H:%M:%S")

    return JSONResponse(content={"files": files})

#скачати великий файл
@app.get("/api/files/{file_id}")
def download_file(file_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT filename, filepath FROM user_files WHERE id = %s"
    cursor.execute(query, (file_id,))
    file_record = cursor.fetchone()
    
    cursor.close()
    conn.close()

    if not file_record or not os.path.exists(file_record['filepath']):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # FileResponse отдаёт файлы со страницы по частям
    return FileResponse(
        path=file_record['filepath'],
        filename=file_record['filename'],
        media_type='application/octet-stream'
    )
