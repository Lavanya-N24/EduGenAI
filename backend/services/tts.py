"""
EduGenAI - Text-to-Speech Service
Generates speech using Google TTS (gTTS).
"""
import asyncio
import logging
import uuid
import os
from pathlib import Path
from gtts import gTTS

from config import AUDIO_DIR

logger = logging.getLogger(__name__)

# Basic supported languages for gTTS mapped from our config
GTTS_LANG_MAP = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "ml": "ml",
    "kn": "kn",
    "bn": "bn",
    "mr": "mr",
    "gu": "gu",
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

async def generate_speech(
    text: str,
    language: str = "en",
    emotion: str = "neutral",
    output_filename: str = None,
) -> dict:
    """
    Generate speech audio from text using gTTS.

    Args:
        text: Text to convert to speech
        language: Language code (e.g., "en", "hi", "ta")
        emotion: (Ignored for gTTS, kept for signature compatibility)
        output_filename: Custom filename (auto-generated if None)

    Returns:
        dict with audio file path, duration, and metadata
    """
    try:
        # Select voice for language
        gtts_lang = GTTS_LANG_MAP.get(language, "en")

        # Generate unique filename
        if not output_filename:
            output_filename = f"speech_{uuid.uuid4().hex[:8]}.mp3"

        output_path = AUDIO_DIR / output_filename

        # Run gTTS in an executor since it's blocking
        def _run_gtts():
            tts = gTTS(text=text, lang=gtts_lang, slow=False)
            tts.save(str(output_path))
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _run_gtts)

        # Get audio duration estimate (rough: ~150 words per minute)
        word_count = len(text.split())
        estimated_duration = (word_count / 150) * 60  # seconds
        
        # If librosa is installed, try to get exact duration
        try:
            import librosa
            y, sr = librosa.load(str(output_path), sr=None)
            estimated_duration = librosa.get_duration(y=y, sr=sr)
        except Exception as e:
            logger.warning(f"Could not calculate exact duration with librosa, using estimate: {e}")

        logger.info(
            f"TTS generated: {output_filename} | Language: {gtts_lang} | Words: {word_count}"
        )

        return {
            "audio_path": str(output_path),
            "filename": output_filename,
            "voice": "gTTS Default",
            "language": language,
            "emotion": "neutral",
            "word_count": word_count,
            "estimated_duration": round(estimated_duration, 1),
        }

    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        raise RuntimeError(f"Speech generation failed: {str(e)}")


async def generate_scene_audio(scenes: dict, language: str = "en") -> dict:
    """
    Generate audio for ALL scenes in PARALLEL using asyncio.gather.
    This is ~Nx faster than serial generation (where N = number of scenes).
    """
    import asyncio

    scene_list = scenes.get("scenes", [])

    async def _gen_one(scene):
        narration = scene.get("narration", "")
        if not narration:
            return None
        emotion  = scene.get("detected_emotion", scene.get("emotion", "neutral"))
        scene_id = scene.get("scene_id", 0)
        filename = f"scene_{scene_id}_{uuid.uuid4().hex[:6]}.mp3"
        result   = await generate_speech(
            text=narration, language=language, emotion=emotion, output_filename=filename
        )
        scene["audio_path"]     = result["audio_path"]
        scene["audio_duration"] = result["estimated_duration"]
        return result

    results = await asyncio.gather(*[_gen_one(s) for s in scene_list], return_exceptions=True)
    audio_files = [r for r in results if r and not isinstance(r, Exception)]

    scenes["audio_files"] = audio_files
    logger.info(f"Generated audio for {len(audio_files)} scenes (parallel)")
    return scenes


async def list_available_voices(language: str = None) -> list[dict]:
    """
    Return a dummy list of voices since gTTS doesn't support multiple voices per language.
    """
    return [
        {
            "name": "gTTS Standard Voice",
            "locale": language or "en",
            "gender": "Female",
        }
    ]
