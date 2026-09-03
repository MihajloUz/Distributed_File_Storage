FROM rust:1.97-bookworm AS builder
WORKDIR /app
COPY rust_backend/Cargo.toml rust_backend/Cargo.lock ./
COPY rust_backend/src ./src
COPY login.html ./login.html
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/data_parser /usr/local/bin/data_parser
COPY --from=builder /app/login.html /app/login.html
WORKDIR /app
CMD ["data_parser"]
