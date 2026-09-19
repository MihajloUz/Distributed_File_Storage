FROM rust:1.97-alpine AS builder
WORKDIR /app
COPY rust_backend/Cargo.toml rust_backend/Cargo.lock ./
COPY rust_backend/src ./src

RUN apk add --no-cache \
    musl-dev \
    openssl-dev \
    openssl-libs-static \
    pkgconfig


RUN cargo build --release

FROM alpine:latest
RUN apk add --no-cache openssl ca-certificates
COPY --from=builder /app/target/release/rust_backend /usr/local/bin/rust_backend
WORKDIR /app
CMD ["rust_backend"]
