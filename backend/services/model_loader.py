"""
EduGenAI - Model Loader
Loads all 3 trained custom models ONCE at startup and keeps them in memory.

Models:
  - Filter Model   : DistilBERT (sequence classification) → relevant / irrelevant
  - Summarizer     : T5-small   (seq2seq)                 → condensed summary
  - Quiz Model     : T5-small   (seq2seq)                 → question generation
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Resolve model directories relative to the project root ──
_BASE = Path(__file__).resolve().parent.parent.parent  # EduGenAI/
FILTER_MODEL_DIR    = _BASE / "training" / "filter_model"      / "models"
SUMMARIZER_MODEL_DIR= _BASE / "training" / "summarization_model"/ "models"
# Quiz model was only checkpointed; use that checkpoint directly
QUIZ_MODEL_DIR      = _BASE / "training" / "quiz_model" / "models" / "quiz_model"

# ── In-memory model cache ────────────────────────────────────
_filter_tokenizer   = None
_filter_model       = None

_summarizer_tokenizer = None
_summarizer_model     = None

_quiz_tokenizer     = None
_quiz_model         = None

_models_loaded      = False


def load_all_models() -> dict:
    """
    Load all 3 trained models into memory.
    Call this once during FastAPI startup.
    Returns a status dict indicating which models loaded successfully.
    """
    global _filter_tokenizer, _filter_model
    global _summarizer_tokenizer, _summarizer_model
    global _quiz_tokenizer, _quiz_model
    global _models_loaded

    status = {}

    # ── Filter Model (DistilBERT classification) ─────────────
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch

        logger.info(f"Loading Filter model from: {FILTER_MODEL_DIR}")
        _filter_tokenizer = AutoTokenizer.from_pretrained(FILTER_MODEL_DIR.as_posix())
        _filter_model     = AutoModelForSequenceClassification.from_pretrained(FILTER_MODEL_DIR.as_posix())
        _filter_model.eval()
        status["filter"] = "✅ loaded"
        logger.info("Filter model loaded successfully")
    except Exception as e:
        logger.warning(f"Filter model failed to load: {e}")
        status["filter"] = f"❌ {e}"

    # ── Summarizer Model (T5-small) ───────────────────────────
    try:
        from transformers import T5Tokenizer, T5ForConditionalGeneration

        logger.info(f"Loading Summarizer model from: {SUMMARIZER_MODEL_DIR}")
        _summarizer_tokenizer = T5Tokenizer.from_pretrained(SUMMARIZER_MODEL_DIR.as_posix())
        _summarizer_model     = T5ForConditionalGeneration.from_pretrained(SUMMARIZER_MODEL_DIR.as_posix())
        _summarizer_model.eval()
        status["summarizer"] = "✅ loaded"
        logger.info("Summarizer model loaded successfully")
    except Exception as e:
        logger.warning(f"Summarizer model failed to load: {e}")
        status["summarizer"] = f"❌ {e}"

    # ── Quiz Model (T5-small checkpoint-500) ─────────────────
    try:
        from transformers import T5Tokenizer, T5ForConditionalGeneration

        logger.info(f"Loading Quiz model from: {QUIZ_MODEL_DIR}")
        _quiz_tokenizer = T5Tokenizer.from_pretrained(QUIZ_MODEL_DIR.as_posix())
        _quiz_model     = T5ForConditionalGeneration.from_pretrained(QUIZ_MODEL_DIR.as_posix())
        _quiz_model.eval()
        status["quiz"] = "✅ loaded"
        logger.info("Quiz model loaded successfully")
    except Exception as e:
        logger.warning(f"Quiz model failed to load: {e}")
        status["quiz"] = f"❌ {e}"

    _models_loaded = True
    logger.info(f"Model loading complete: {status}")
    return status


# ── Getters ──────────────────────────────────────────────────

def get_filter_model():
    """Return (tokenizer, model) for the Filter model. Returns (None, None) if not loaded."""
    return _filter_tokenizer, _filter_model


def get_summarizer_model():
    """Return (tokenizer, model) for the Summarizer. Returns (None, None) if not loaded."""
    return _summarizer_tokenizer, _summarizer_model


def get_quiz_model():
    """Return (tokenizer, model) for the Quiz model. Returns (None, None) if not loaded."""
    return _quiz_tokenizer, _quiz_model


def models_ready() -> bool:
    """True if at least one model has been attempted to load."""
    return _models_loaded
