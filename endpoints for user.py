import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import TemplateResponse
from pydantic import BaseModel, EmailStr

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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
