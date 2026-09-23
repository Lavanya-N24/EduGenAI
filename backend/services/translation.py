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


import re
from typing import Optional

# Script Unicode ranges for language verification
_SCRIPT_REGEXES = {
    "kn": re.compile(r"[\u0C80-\u0CFF]"),
    "hi": re.compile(r"[\u0900-\u097F]"),
    "mr": re.compile(r"[\u0900-\u097F]"),
    "sa": re.compile(r"[\u0900-\u097F]"),
    "ta": re.compile(r"[\u0B80-\u0BFF]"),
    "te": re.compile(r"[\u0C00-\u0C7F]"),
    "ml": re.compile(r"[\u0D00-\u0D7F]"),
    "bn": re.compile(r"[\u0980-\u09FF]"),
    "as": re.compile(r"[\u0980-\u09FF]"),
    "gu": re.compile(r"[\u0A80-\u0AFF]"),
    "pa": re.compile(r"[\u0A00-\u0A7F]"),
    "ur": re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF]"),
    "ar": re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF]"),
    "ja": re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF]"),
    "zh-cn": re.compile(r"[\u4E00-\u9FFF]"),
    "zh": re.compile(r"[\u4E00-\u9FFF]"),
    "ko": re.compile(r"[\uAC00-\uD7AF]"),
    "ru": re.compile(r"[\u0400-\u04FF]"),
}


def _is_already_target_language(text: str, target_lang: str) -> bool:
    """Check if the text is already written in the target language script."""
    regex = _SCRIPT_REGEXES.get(target_lang.lower())
    if not regex:
        return False
    # If there are at least 3 script characters, it's already in the target language
    matches = regex.findall(text)
    return len(matches) >= 3


def _is_error_response(translated: str) -> bool:
    """Check if the translation output is actually a Google 500 error page / message."""
    if not translated or not str(translated).strip():
        return True
    t_lower = translated.lower()
    error_signatures = (
        "error 500", "500 (server error)", "that's an error",
        "please try again later", "that's all we know", "<html", "<!doctype",
        "error 4", "error 5", "server error!!", "unusual traffic",
    )
    return any(sig in t_lower for sig in error_signatures)


async def _translate_via_llm(text: str, target_lang_name: str) -> Optional[str]:
    """Fallback translator using Groq / Gemini LLM if Google Translate is unavailable or rate-limited."""
    try:
        from services.llm import _call_llm
        prompt = (
            f"Translate the following educational text into natural, accurate {target_lang_name}.\n"
            f"Preserve technical terms, numbers, and formulas. Return ONLY the translation, nothing else.\n\n"
            f"Text to translate:\n{text}"
        )
        res = await _call_llm(
            messages=[
                {"role": "system", "content": f"You are an expert educational translator specializing in {target_lang_name}."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.2,
            is_json=False,
        )
        cleaned = (res or "").strip()
        if cleaned and not _is_error_response(cleaned):
            return cleaned
    except Exception as e:
        logger.warning("LLM translation fallback failed: %s", e)
    return None


async def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "auto",
) -> dict:
    """
    Translate text to the target language.
    Validates output to prevent Google 500 error strings from corrupting narration.
    """
    text_str = str(text or "").strip()
    if not text_str:
        return {
            "original": "",
            "translated": "",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "was_translated": False,
        }

    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    # 1. If target is English or already in target language script, return immediately
    if target_lang == "en" and source_lang in ("en", "auto"):
        return {
            "original": text_str,
            "translated": text_str,
            "source_lang": "en",
            "target_lang": "en",
            "was_translated": False,
        }

    if _is_already_target_language(text_str, target_lang):
        logger.info("Text is already in target script (%s), skipping translation", target_lang)
        return {
            "original": text_str,
            "translated": text_str,
            "source_lang": target_lang,
            "target_lang": target_lang,
            "target_language_name": lang_name,
            "was_translated": False,
        }

    # 2. Try Google Translate
    translated = ""
    try:
        src = LANG_MAP.get(source_lang, "auto")
        tgt = LANG_MAP.get(target_lang, target_lang)

        max_chunk = 4500
        if len(text_str) <= max_chunk:
            res = GoogleTranslator(source=src, target=tgt).translate(text_str)
            if res and not _is_error_response(res):
                translated = res
        else:
            chunks = _split_text(text_str, max_chunk)
            translated_chunks = []
            for chunk in chunks:
                t = GoogleTranslator(source=src, target=tgt).translate(chunk)
                if t and not _is_error_response(t):
                    translated_chunks.append(t)
                else:
                    raise RuntimeError("Chunk translation returned error signature")
            translated = " ".join(translated_chunks)
    except Exception as e:
        logger.warning("Google Translate failed or returned error page: %s", e)

    # 3. If Google Translate failed or returned error string, fallback to LLM
    if not translated or _is_error_response(translated):
        logger.info("Using LLM translation fallback for %s...", lang_name)
        llm_trans = await _translate_via_llm(text_str, lang_name)
        if llm_trans:
            translated = llm_trans
        else:
            # Fallback to original text rather than corrupting with error text
            logger.warning("Translation fallback failed, retaining original text")
            translated = text_str

    return {
        "original": text_str,
        "translated": translated,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "target_language_name": lang_name,
        "was_translated": True,
    }


async def translate_scenes(scenes: dict, target_lang: str) -> dict:
    """
    Translate all narration text in scene data to the target language safely in parallel.
    Only translates narration (what the voice says) and title.
    Visual descriptions stay in English for the video generator.
    """
    if target_lang == "en":
        return scenes

    try:
        scene_list = scenes.get("scenes", [])

        async def _translate_single_scene(scene: dict):
            # Translate narration and title concurrently for each scene
            coros = []
            keys = []
            if scene.get("narration"):
                coros.append(translate_text(scene["narration"], target_lang))
                keys.append("narration")
            if scene.get("title"):
                coros.append(translate_text(scene["title"], target_lang))
                keys.append("title")

            if coros:
                results = await asyncio.gather(*coros)
                for k, res in zip(keys, results):
                    if k == "narration":
                        scene["original_narration"] = res["original"]
                        scene["narration"] = res["translated"]
                    elif k == "title":
                        scene["original_title"] = res["original"]
                        scene["title"] = res["translated"]

        tasks = [_translate_single_scene(s) for s in scene_list]

        if scenes.get("title"):
            async def _translate_main_title():
                res = await translate_text(scenes["title"], target_lang)
                scenes["original_title"] = res["original"]
                scenes["title"] = res["translated"]
            tasks.append(_translate_main_title())

        await asyncio.gather(*tasks)
        logger.info(f"Translated all {len(scene_list)} scenes to {target_lang} (parallel)")
        return scenes

    except Exception as e:
        logger.error(f"Scene translation failed: {e}")
        return scenes


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
