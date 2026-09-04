use std::os::unix::fs::OpenOptionsExt;

use axum::{
    Router,
    body::Body,
    body::BodyDataStream,
    extract::Path,
    http::{
        HeaderMap,
        Method,
        StatusCode
    },
    response::{
        IntoResponse,
        Html,
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
use futures_util::StreamExt;  
async fn upload_on_server(
    method: Method,
    headers: HeaderMap,
    Path((user_id, relative_path)): Path<(String, String)>,
    body: Body,

) -> Result<impl IntoResponse, ServerError>{
    let mut stream = body.into_data_stream();   

    let mut file = OpenOptions::new()
        .write(true)
        .append(true)
        .open(format!("/{}/{}", user_id, relative_path))
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
}

fn create_app(state: AppState) -> Router{
    Router::new()
        .route("/upload_file/{user_id}/{relative_path}", post(upload_on_server))
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
    setting_up_db(&pool);

    let state = AppState{
        db: pool, 
    };

    let app = create_app(state);
    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000").await?;

    axum::serve(listener, app).await?;
    Ok(())
}

