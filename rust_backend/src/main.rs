use std::os::unix::fs::OpenOptionsExt;
use serde::Deserialize;
use axum::{
    Router,
    body::Body,
    body::BodyDataStream,
    extract::{
        Path,
        State,
        Json,
    }
    http::{
        HeaderMap,
        Method,
        StatusCode
    },
    response::{
        IntoResponse,
        Html,
        Redirect,
    },
    routing::{
        get,
        post
    }, 
};
use rust_backend::*;
use tokio::fs;
use tokio::fs::OpenOptions;
use tokio::io::AsyncWriteExt;
use axum::body::to_bytes;
use axum_extra::extract::cookie::{Cookie, CookieJar};
use futures_util::StreamExt;  

#[derive(Deserialize)]
struct UserJson{
    email: String,
}

async fn create_cookie(
    State(state): State<AppState>,
    jar: CookieJar, 
    Json(data): Json<UserJson> 
    ) -> Result<(CookieJar, Json), ServerError> {

    let client = state.db.get().await?;
    let row = client.query_opt(
        "SELECT id FROM users WHERE email = $1", 
        &[&data.email]
    ).await?;

    let Some(row) = row else{
        return Ok((
            jar,
            Json(serde_json::json!({
                "success": false,
                "message": "Unsuccessful login",
            })),
        ));
    };

    let user_id: uuid::Uuid = row.get("id");

    let row = client.query_one(
        "INSERT INTO sessions (user_id) VALUES ($1) RETURNING session_id",
        &[&user_id]
    ).await?;

    let session_id: uuid::Uuid = row.get("session_id");

    let cookie = Cookie::build(("session_id", session_id.to_string()))
        .path("/")
        .http_only(true)
        .build();

    return Ok((
        jar.add(cookie), 
        Json(serde_json::json!({
            "success": true,
            "message": "Cookie was created successfully",
        })),
    ));
}

async fn upload_on_server(
    jar: CookieJar,
    body: Body,
    headers: HeaderMap,
    State(state): State<AppState>

) -> Result<impl IntoResponse, ServerError>{
    let filename = headers.get("Filename")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("Unnamed");

    if let Some(value) = get_cookie(&jar, "session_id"){
        let session_id: uuid::Uuid = value.parse()?;  
        
        let client = state.db.get().await?;
       
        let row = client.query_opt(
            "SELECT user_id FROM sessions WHERE sessions.session_id = $1",
            &[&session_id]
        ).await?;

        let Some(row) = row else{
            return ServerError::GeneralIo; //refactor for real error
        }
        
        let user_id: uuid::Uuid = row.get("user_id");

        let mut stream = body.into_data_stream();   

        let path = format!("/app/user_data/{}/{}", user_id, filename);

        if let Some(parent) = std::path::Path::new(&path).parent() {
            tokio::fs::create_dir_all(parent).await.map_err(ServerError::Io)?;
        }

        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&path)
            .await
            .map_err(ServerError::Io)?; //change later to
        
        while let Some(chunk_result) = stream.next().await{
            match chunk_result{
                Ok(chunk) => {
                    file.write_all(&chunk).await.map_err(ServerError::Io)?;                   
                },
                Err(e) => {
                    return Err(ServerError::Axum(e));
                },
            }
        }
        Ok((StatusCode::OK, "Data uploaded successfully").into_response())
    }else{

    }
}

fn create_app(state: AppState) -> Router{
    Router::new()
        .route("/api/upload", post(upload_on_server)) 
        .with_state(state)
}

#[tokio::main]
async fn main() -> Result<(), ServerError>{

    dotenvy::dotenv().ok();
    let (client, connection) = tokio_postgres::connect(
        format!("host={} user={} password={} dbname={}",
                std::env::var("POSTGRES_HOST")?,
                std::env::var("POSTGRES_USER")?,
                std::env::var("POSTGRES_PASSWORD")?,
                "postgres".to_string()).as_str(), 
            tokio_postgres::NoTls
    ).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await{
            eprintln!("Error connecting to db: {}", e);
        }
    });

    match client.batch_execute(
        &format!("CREATE DATABASE {}", std::env::var("POSTGRES_DB")?)
    ).await{
        Ok(_) => {},
        Err(_) => {println!("Database was already created. Skipping creating another one");}
    } 
    dotenvy::dotenv().ok();
    
    let (client, connection) = tokio_postgres::connect(
        format!("host={} user={} password={} dbname={}",
                std::env::var("POSTGRES_HOST")?,
                std::env::var("POSTGRES_USER")?,
                std::env::var("POSTGRES_PASSWORD")?,
                std::env::var("POSTGRES_DB")?).as_str(), 
            tokio_postgres::NoTls
    ).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await{
            eprintln!("Error connecting to db: {}", e);
        }
    });

    let pool = create_pool()?;
    setting_up_db(&pool).await;

    let state = AppState{
        db: pool, 
    };

    let app = create_app(state);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8001").await?;

    axum::serve(listener, app).await?;
    Ok(())
}

