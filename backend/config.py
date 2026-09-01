"""
EduGenAI - Configuration Module
Loads environment variables and sets up paths.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Base Paths ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "outputs")
AUDIO_DIR = BASE_DIR / os.getenv("AUDIO_DIR", "outputs/audio")
VIDEO_DIR = BASE_DIR / os.getenv("VIDEO_DIR", "outputs/video")
IMAGE_DIR = BASE_DIR / "outputs" / "images"
SUBTITLE_DIR = BASE_DIR / os.getenv("SUBTITLE_DIR", "outputs/subtitles")
UPLOAD_DIR = BASE_DIR / "uploads"
MODELS_DIR = BASE_DIR / "models"

# Create directories if they don't exist
for d in [OUTPUT_DIR, AUDIO_DIR, VIDEO_DIR, SUBTITLE_DIR, IMAGE_DIR, UPLOAD_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── API Keys & Video Provider ──────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
PIXAZO_API_KEY = os.getenv("PIXAZO_API_KEY", "")
PIXAZO_MODEL = os.getenv("PIXAZO_MODEL", "ltx-2-5-pro")
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "pixazo").lower().strip()

# ── Server ──────────────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

# ── Tesseract OCR ──────────────────────────────────────────
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# ── Supported Languages ────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "ja": "Japanese",
    "zh-cn": "Chinese (Simplified)",
    "ar": "Arabic",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
}

# ── Edge TTS Voice Map ─────────────────────────────────────
# Maps language code to best neural TTS voice
EDGE_TTS_VOICES = {
    "en": "en-US-AriaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "ml": "ml-IN-SobhanaNeural",
    "kn": "kn-IN-SapnaNeural",
    "bn": "bn-IN-TanishaaNeural",
    "mr": "mr-IN-AarohiNeural",
    "gu": "gu-IN-DhwaniNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "de": "de-DE-KatjaNeural",
    "ja": "ja-JP-NanamiNeural",
    "zh-cn": "zh-CN-XiaoxiaoNeural",
    "ar": "ar-SA-ZariyahNeural",
    "ko": "ko-KR-SunHiNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ru": "ru-RU-SvetlanaNeural",
}

# ── Emotion to TTS Style Map ──────────────────────────────
EMOTION_VOICE_STYLES = {
    "joy": {"rate": "+10%", "pitch": "+5Hz"},
    "sadness": {"rate": "-15%", "pitch": "-5Hz"},
    "anger": {"rate": "+5%", "pitch": "+10Hz"},
    "fear": {"rate": "+20%", "pitch": "+8Hz"},
    "surprise": {"rate": "+15%", "pitch": "+12Hz"},
    "neutral": {"rate": "+0%", "pitch": "+0Hz"},
    "curious": {"rate": "+5%", "pitch": "+3Hz"},
    "excited": {"rate": "+12%", "pitch": "+8Hz"},
}
