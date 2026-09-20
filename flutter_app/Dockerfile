# ============================================================
# EduGenAI Flutter Web - Multi-stage Dockerfile
# Stage 1: Build Flutter Web App
# Stage 2: Serve with Nginx Alpine
# ============================================================

# ── Stage 1: Build Flutter Web ──────────────────────────────
FROM ghcr.io/cirruslabs/flutter:stable AS builder

WORKDIR /app

# Copy dependency definition
COPY pubspec.yaml pubspec.lock ./

# Download Flutter packages
RUN flutter pub get

# Copy source code
COPY . .

# Build web release bundle
RUN flutter build web --release

# ── Stage 2: Nginx Web Server ──────────────────────────────
FROM nginx:alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled Flutter web assets from builder
COPY --from=builder /app/build/web /usr/share/nginx/html

# Expose web port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
