FROM rust:1.97-bookworm AS builder
WORKDIR /app
COPY rust_backend/Cargo.toml rust_backend/Cargo.lock ./
COPY rust_backend/src ./src
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y libssl3 ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/rust_backend /usr/local/bin/rust_backend
WORKDIR /app
CMD ["rust_backend"]
