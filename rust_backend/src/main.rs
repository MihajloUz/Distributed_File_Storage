use serde::Deserialize;
use axum::{
    Router,
    body::Body,
    extract::{
        State,
        Json,
    },
    http::{
        HeaderMap,
        StatusCode
    },
    response::{
        IntoResponse,
    },
    routing::{
        post
    }, 
};
use rust_backend::*;
use tokio::fs::OpenOptions;
use tokio::io::AsyncWriteExt;
use axum_extra::extract::cookie::CookieJar;
use futures_util::StreamExt;  

#[derive(Deserialize)]
struct UserJson{
    email: String,
}

async fn create_cookie(
    State(state): State<AppState>,
    Json(data): Json<UserJson> 
    ) -> Result<Json<serde_json::Value>, ServerError> {

    let client = state.db.get().await?;
    let row = client.query_opt(
        "SELECT id FROM users WHERE email = $1", 
        &[&data.email]
    ).await?;

    let Some(row) = row else{
        return Ok(
            Json(serde_json::json!({
                "success": false,
                "session_id": "No session id was created"
            })),
        );
    };

    let user_id: uuid::Uuid = row.get("id");

    let row = client.query_one(
        "INSERT INTO sessions (user_id) VALUES ($1) RETURNING session_id",
        &[&user_id]
    ).await?;

    let session_id: uuid::Uuid = row.get("session_id");

    return Ok(
        Json(serde_json::json!({
            "success": true,
            "session_id": session_id
        })),
    );
}


// here i should upload file ot the server based on the users id that
// I get from session id and sessions table
// then i upload file onto the server and return json about success
// or failure
// and add data about the file to table user_files



// now it reutrn json correctly 
async fn post_on_server(
    jar: CookieJar,
    headers: HeaderMap,
    State(state): State<AppState>,
    body: Body

) -> Result<Json<serde_json::Value>, ServerError>{
    let filename = headers.get("Filename")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("Unnamed");
    if let Some(value) = get_cookie(&jar, "session_id"){
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
            .map_err(ServerError::Io)?;
        
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
        let row = client.execute(
            "INSERT INTO user_files (user_id, file_name) VALUES ($1, $2)",
            &[&user_id, &filename]
        ).await?;
        Ok(
            Json(serde_json::json!({
                "success": true,
            })),
        )
    }else{
        Err(ServerError::NoCookie)
    }
}



async fn get_from_server(
    jar: CookieJar,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, ServerError>{
    
    if let Some(value) = get_cookie(&jar, "session_id"){
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
        
        let rows = client.query(
            "SELECT id, file_name, uploaded_at FROM user_files WHERE user_files.user_id = $1", 
            &[&user_id]
        ).await?;
        
        let files: Vec<_> = rows.iter().map(|row| {
            let id: uuid::Uuid= row.get("id");
            let file_name: String = row.get("file_name");
            let uploaded_at: chrono::DateTime<chrono::Utc> = row.get("uploaded_at");
            serde_json::json!({
                "id": id,
                "file_name": file_name,
                "uploaded_at": uploaded_at.to_rfc3339(),
            })
        }).collect();

        Ok(Json(serde_json::json!({"files": files})))
    }
    else{
        Err(ServerError::NoCookie)
    }
}


fn create_app(state: AppState) -> Router{
    Router::new()
        .route("/login_successful", post(create_cookie)) 
        .route("/api/upload", post(post_on_server)) 
        .route("/api/files", post(get_from_server)) 
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
    
    let (_client, connection) = tokio_postgres::connect(
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
    setting_up_db(&pool).await?;

    let state = AppState{
        db: pool, 
    };

    let app = create_app(state);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8001").await?;

    axum::serve(listener, app).await?;
    Ok(())
}
