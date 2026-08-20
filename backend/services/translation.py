"""
EduGenAI - Translation Service
Translates text between languages using Google Translate (free, no API key needed).

ML Algorithm: Neural Machine Translation (NMT) using Transformer encoder-decoder.
Google Translate uses a sequence-to-sequence model with attention mechanism
to translate between language pairs.
"""
import logging
from deep_translator import GoogleTranslator

from config import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Language code mapping: our codes → Google Translate codes
LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "ml": "ml",
    "kn": "kn",
    "bn": "bn",
    "mr": "mr",
    "gu": "gu",
    "pa": "pa",
    "ur": "ur",
    "fr": "fr",
    "es": "es",
    "de": "de",
    "ja": "ja",
    "zh-cn": "zh-CN",
    "ar": "ar",
    "ko": "ko",
    "pt": "pt",
    "ru": "ru",
}


async def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "auto",
) -> dict:
    """
    Translate text to the target language.

    Args:
        text: Text to translate
        target_lang: Target language code (e.g., "hi", "ta", "fr")
        source_lang: Source language code or "auto" for auto-detection

    Returns:
        dict with translated text and language info
    """
    if target_lang == "en" and source_lang in ("en", "auto"):
        # No translation needed
        return {
            "original": text,
            "translated": text,
            "source_lang": "en",
            "target_lang": "en",
            "was_translated": False,
        }

    try:
        src = LANG_MAP.get(source_lang, "auto")
        tgt = LANG_MAP.get(target_lang, target_lang)

        # Split long texts into chunks (Google Translate limit: ~5000 chars)
        max_chunk = 4500
        if len(text) <= max_chunk:
            translated = GoogleTranslator(source=src, target=tgt).translate(text)
        else:
            # Chunk by sentences to preserve meaning
            chunks = _split_text(text, max_chunk)
            translated_chunks = []
            for chunk in chunks:
                t = GoogleTranslator(source=src, target=tgt).translate(chunk)
                translated_chunks.append(t)
            translated = " ".join(translated_chunks)

        lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
        logger.info(f"Translated {len(text)} chars to {lang_name}")

        return {
            "original": text,
            "translated": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "target_language_name": lang_name,
            "was_translated": True,
        }

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise RuntimeError(f"Translation to {target_lang} failed: {str(e)}")


async def translate_scenes(scenes: dict, target_lang: str) -> dict:
    """
    Translate all narration text in scene data to the target language.
    Only translates narration (what the voice says) and title.
    Visual descriptions stay in English for the video generator.

    Args:
        scenes: Scene data dict from LLM
        target_lang: Target language code

    Returns:
        Scene data with translated narration
    """
    if target_lang == "en":
        return scenes

    try:
        for scene in scenes.get("scenes", []):
            # Translate narration
            narration_result = await translate_text(
                scene["narration"], target_lang
            )
            scene["narration"] = narration_result["translated"]
            scene["original_narration"] = narration_result["original"]

            # Translate title
            title_result = await translate_text(scene["title"], target_lang)
            scene["title"] = title_result["translated"]

        # Translate video title
        title_result = await translate_text(scenes["title"], target_lang)
        scenes["title"] = title_result["translated"]

        logger.info(f"Translated all scenes to {target_lang}")
        return scenes

    except Exception as e:
        logger.error(f"Scene translation failed: {e}")
        raise RuntimeError(f"Scene translation failed: {str(e)}")


def _split_text(text: str, max_length: int) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    sentences = text.replace(". ", ".\n").split("\n")
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) < max_length:
            current += sentence + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sentence + " "

    if current.strip():
        chunks.append(current.strip())

    return chunks
