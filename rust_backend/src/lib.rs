use axum::{http::StatusCode, response::IntoResponse};
use axum_extra::extract::cookie::CookieJar;
use axum::extract::State;
use std::{fmt, env};
use deadpool_postgres::{
    Config, 
    Runtime, 
};


#[derive(Debug)]
pub enum ServerError{
    TokioDb(tokio_postgres::Error),
    DeadpoolDb(deadpool_postgres::PoolError),
    PoolCreation(deadpool_postgres::CreatePoolError),
    Io(std::io::Error),
    Env(env::VarError),
    SerdeJson(serde_json::Error),
    Axum(axum::Error),
    
    Parsing,
    NotFound,
    NoCookie,  
    ResponseCreation,  
}


impl fmt::Display for ServerError{
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result{
        match self{
            ServerError::TokioDb(e) => {
                write!(f, "tokio_postgres database erorr: {}", e)
            }
            ServerError::DeadpoolDb(e) => {
                write!(f, "deadpool_postgres database erorr: {}", e)
            }
            ServerError::PoolCreation(e) => {
                write!(f, "Failed to create database: {}", e)
            }
            ServerError::Io(e) => {
                write!(f, "I/O erorr: {}", e)
            }
            ServerError::Env(e) => {
                write!(f, ".env erorr: {}", e)
            }
            ServerError::SerdeJson(e) => {
                write!(f, "{}", e)
            }
            ServerError::Axum(e) => {
                write!(f, "{}", e)
            }
            ServerError::Parsing => {
                write!(f, "Error parsing value")
            }
            ServerError::NotFound => {
                write!(f, "Value not found")
            }
            ServerError::NoCookie => {
                write!(f, "Could not read a cookie")
            }
            ServerError::ResponseCreation => {
                write!(f, "Could not build a response")
            }
        }
    }
}
impl IntoResponse for ServerError{
    fn into_response(self) -> axum::response::Response {
        let status = match self{
            ServerError::TokioDb(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::DeadpoolDb(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::PoolCreation(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::Io(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::Env(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::SerdeJson(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::Axum(_) => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::Parsing => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::NotFound => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::NoCookie => StatusCode::INTERNAL_SERVER_ERROR,
            ServerError::ResponseCreation => StatusCode::INTERNAL_SERVER_ERROR,
        };

        (status, self.to_string()).into_response()
    }
}


impl From<tokio_postgres::Error> for ServerError{
    fn from(e: tokio_postgres::Error) -> Self{
        ServerError::TokioDb(e)
    }
} 

impl From<deadpool_postgres::PoolError> for ServerError{
    fn from(e: deadpool_postgres::PoolError) -> Self {
        ServerError::DeadpoolDb(e)
    }
}

impl From<deadpool_postgres::CreatePoolError> for ServerError{
    fn from(e: deadpool_postgres::CreatePoolError) -> Self {
        ServerError::PoolCreation(e) 
    }
}

impl From<std::io::Error> for ServerError{
    fn from(e: std::io::Error) -> Self{
        ServerError::Io(e)
    }
} 

impl From<env::VarError> for ServerError{
    fn from(e: env::VarError) -> Self {
        ServerError::Env(e) 
    }
}

impl From<serde_json::Error> for ServerError{
    fn from(e: serde_json::Error) -> Self {
        ServerError::SerdeJson(e) 
    }
}

impl From<axum::Error> for ServerError{
    fn from(e: axum::Error) -> Self {
        ServerError::Axum(e) 
    }
}


impl std::error::Error for ServerError{}

//db
pub fn create_pool() -> Result<deadpool_postgres::Pool, ServerError>{
    let mut cfg = Config::new();

    cfg.host = Some(std::env::var("POSTGRES_HOST")?);
    cfg.user = Some(std::env::var("POSTGRES_USER")?);
    cfg.password = Some(std::env::var("POSTGRES_PASSWORD")?);
    cfg.dbname = Some(std::env::var("POSTGRES_DB")?);

    Ok(cfg.create_pool(Some(Runtime::Tokio1), tokio_postgres::NoTls)?)
}

//App state and msg receiving
#[derive(Clone)]
pub struct AppState{
    pub db: deadpool_postgres::Pool,
}



pub async fn setting_up_db(pool: &deadpool_postgres::Pool) -> Result<(), deadpool_postgres::PoolError>{
    let client = pool.get().await?;

    client.batch_execute(
        "
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS user_files(
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id),
            file_name TEXT NOT NULL,
            uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS sessions(
            user_id UUID NOT NULL REFERENCES users(id),
            session_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '7 days'
        );
        "
    ).await?;

    Ok(())
}

pub fn get_cookie(jar: &CookieJar, cookie_name: &str) -> Option<String> {
    jar.get(cookie_name).map(|cookie| cookie.value().to_string())
}

fn session_cookie_check(
    jar: CookieJar,
) ->Result<String, ServerError>{
    match get_cookie(&jar, "session_id"){
        Some(value) => Ok(value),
        None => Err(ServerError::NoCookie),
    }
}

pub async fn get_user_id_from_cookie(
    jar: CookieJar,
    State(state): State<AppState>,
) -> Result<(deadpool_postgres::Object, uuid::Uuid), ServerError> { 
    let value = session_cookie_check(jar)?;
    let session_id: uuid::Uuid = value.parse().map_err(|_| ServerError::Parsing)?;
    let client = state.db.get().await?;
   
    let row = client.query_opt(
        "SELECT user_id FROM sessions WHERE sessions.session_id = $1",
        &[&session_id]
    ).await?;

    let Some(row) = row else{
        return Err(ServerError::Parsing);
    };
    
    let user_id: uuid::Uuid = row.get("user_id");
    Ok((client, user_id))
}
