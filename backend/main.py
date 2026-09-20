"""
EduGenAI - FastAPI Main Application
Entry point for the backend server.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import HOST, PORT, DEBUG, OUTPUT_DIR, VIDEO_DIR
from routes import generate, quiz, tutor, analytics, sharing
from services.model_loader import load_all_models


# ── Logging Setup ───────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("EduGenAI")


from db.database import init_db
from db.migrate_json import migrate_legacy_data
from services.cache import init_redis


# ── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Database connection and schema...")
    try:
        await init_db()
        await migrate_legacy_data()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    # Initialize Redis Cache
    try:
        await init_redis()
    except Exception as e:
        logger.warning(f"Redis cache init: {e}")

    logger.info("Loading trained ML models...")
    status = load_all_models()
    logger.info(f"Model load status: {status}")

    yield

    logger.info("Shutting down EduGenAI...")


# ── FastAPI App ─────────────────────────────────────────────

app = FastAPI(
    title="EduGenAI API",
    lifespan=lifespan,
    description=(
        "AI-Based Multilingual Animated Audio & Video Generator for Education. "
        "Upload text, images, or PDFs and get back animated educational videos "
        "with AI narration, subtitles, quizzes, and an interactive tutor."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS ────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Generated files ─────────────────────────────────────────
#
# /outputs/...  -> all normal generated output files
# /videos/...   -> FINAL MP4 files created by services.video
#
# The important fix is /videos because video.py writes to VIDEO_DIR.

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

VIDEO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="outputs",
)

app.mount(
    "/videos",
    StaticFiles(directory=str(VIDEO_DIR)),
    name="videos",
)


# ── Register Routes ─────────────────────────────────────────

app.include_router(generate.router)
app.include_router(quiz.router)
app.include_router(tutor.router)
app.include_router(analytics.router)
app.include_router(sharing.router)


# ── Root Endpoint ───────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "EduGenAI API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "video_base_url": "/videos/",
        "endpoints": {
            "generate_video": "POST /api/generate/full-pipeline",
            "generate_scenes": "POST /api/generate/text-only",
            "ocr": "POST /api/generate/ocr",
            "languages": "GET /api/generate/languages",
            "quiz_generate": "POST /api/quiz/generate",
            "quiz_submit": "POST /api/quiz/submit",
            "tutor_chat": "POST /api/tutor/chat",
            "analytics": "GET /api/analytics/{user_id}",
        },
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "video_directory": str(VIDEO_DIR),
        "video_directory_exists": VIDEO_DIR.exists(),
    }


# ── Run Server ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting EduGenAI Server...")
    logger.info(f"📄 API Docs: http://localhost:{PORT}/docs")

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
    )
