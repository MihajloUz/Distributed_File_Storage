use axum::{
    Router,
    body::Body,
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

async fn upload_on_server(
    method: Method,
    headers: HeaderMap,
    Path((user_id, relative_path)): Path<(String, String)>,
    body: Body,

) -> Result<impl IntoResponse, ServerError>{
     


    Ok((StatusCode::OK, "Data uploaded successfully").into_response())
}

async fn login_page() -> Html<String>{
    let page = tokio::fs::read_to_string("../login.html").async?; 

    
    Html(page)
}

fn create_app(state: AppState) -> Router{
    Router::new()
        .route("/", post(login_page))
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
                std::env::var("POSTGRES_DB")?).as_str(), 
            tokio_postgres::NoTls
    ).await?;
    tokio::spawn(async move {
        if let Err(e) = connection.await{
            eprintln!("Error connecting to db: {}", e);
        }
    });

    let pool = create_pool()?;

    let state = AppState{
        db: pool, 
    };

    let app = create_app(state);
    let listener = tokio::net::TcpListener::bind("0.0.0.0:80").await?;

    axum::serve(listener, app).await?;
    Ok(())
}

