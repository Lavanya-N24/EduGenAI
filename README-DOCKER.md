# 🐳 Running EduGenAI with Docker & Docker Compose

Run the entire **EduGenAI** stack (FastAPI Backend + AI Media Services + Supabase PostgreSQL + Flutter Web Frontend) in isolated containers on any OS (Windows, macOS, Linux, or Cloud VM).

---

## 📋 Prerequisites

Install **Docker Desktop** (or Docker Engine + Docker Compose plugin):
* [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## 🚀 Quick Start (1 Command)

### 1. Configure Environment Variables
Ensure your `backend/.env` has your API keys and PostgreSQL connection string:
```bash
cp .env.example backend/.env
# Edit backend/.env with your GROQ_API_KEY and DATABASE_URL
```

### 2. Build and Start All Containers
From the project root:
```bash
docker compose up --build
```

---

## 🌐 Access Points

| Service | URL | Description |
| :--- | :--- | :--- |
| **Flutter Web App** | [http://localhost:3000](http://localhost:3000) | Main Frontend UI |
| **FastAPI Backend** | [http://localhost:8000](http://localhost:8000) | REST API Server |
| **Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger OpenAPI Docs |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Container Health Endpoint |

---

## 🛠️ Common Docker Commands

### Run in background (Detached mode):
```bash
docker compose up -d
```

### View live logs:
```bash
docker compose logs -f
```

### View backend logs only:
```bash
docker compose logs -f backend
```

### Stop all containers:
```bash
docker compose down
```

### Rebuild after code changes:
```bash
docker compose up --build -d
```
