"""
EduGenAI - Generate Route
Main API endpoint for the complete content → video pipeline.
Handles file uploads (text, image, PDF) and orchestrates all AI modules.
"""
import logging
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from services.ocr import extract_text_from_image, extract_text_from_pdf
from services.document_reader import extract_text_from_docx, extract_text_from_pptx
from services.audio_input import extract_text_from_audio
from services.knowledge_base import enrich_with_knowledge_base
from services.filter_model import filter_content
from services.summarizer_model import summarize_text
from services.llm import generate_scenes
from services.translation import translate_scenes
from services.emotion import detect_scene_emotions
from services.tts import generate_scene_audio
from services.video import generate_video
from services.subtitle import generate_subtitles
from services.quiz_model import generate_quiz_from_model
from services.sharing import save_video_record
from config import SUPPORTED_LANGUAGES

from utils.file_handler import handle_uploaded_file
from utils.helpers import generate_job_id
from models.response_models import GenerateResponse, OCRResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/generate", tags=["Generate"])


@router.post("/full-pipeline", response_model=GenerateResponse)
async def full_pipeline(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    target_language: str = Form("en"),
    generate_video_flag: bool = Form(True),
    learning_mode: str = Form("beginner"),
    user_id: str = Form("default_user"),
):
    """
    🚀 MAIN ENDPOINT: Complete content-to-video pipeline.

    Accepts: text, image (OCR), or PDF upload
    Returns: Video, audio, subtitles, scene data

    Pipeline: Input → Text → Scenes → Emotion → Translation → TTS → Video → Subtitles
    """
    job_id = generate_job_id()
    logger.info(f"[{job_id}] Starting full pipeline")

    # ── Step 1: Extract Text ────────────────────────────────
    content = ""

    if text:
        content = text
        input_type = "text"
    elif file:
        file_bytes, input_type = await handle_uploaded_file(file)
        
        if input_type == "image_ocr":
            result = await extract_text_from_image(file_bytes)
            content = result["text"]
        elif input_type == "pdf":
            result = await extract_text_from_pdf(file_bytes)
            content = result["text"]
        elif input_type == "pptx":
            result = await extract_text_from_pptx(file_bytes)
            content = result["text"]
        elif input_type == "docx":
            result = await extract_text_from_docx(file_bytes)
            content = result["text"]
        elif input_type == "audio":
            import os
            _, ext = os.path.splitext(file.filename)
            result = await extract_text_from_audio(file_bytes, ext)
            content = result["text"]
        elif input_type == "text_file":
            content = file_bytes.decode("utf-8")
    else:
        raise HTTPException(400, "Please provide either 'text' or upload a 'file'.")

    if not content.strip():
        raise HTTPException(400, "No text could be extracted from the input.")

    logger.info(f"[{job_id}] Step 1 complete: Extracted {len(content)} chars via {input_type}")

    # ── Step 1.05: Knowledge Base Enrichment ────────────────
    kb_result = await enrich_with_knowledge_base(content)
    enriched_content = kb_result["enriched_text"]
    if kb_result["was_enriched"]:
        logger.info(f"[{job_id}] Step 1.05 complete: Enriched via {kb_result['source']}")

    # ── Step 1.1: Content Filtering (Trained Model 🔥) ──────
    filter_result = await filter_content(enriched_content)
    filtered_text = filter_result["filtered_text"]
    logger.info(f"[{job_id}] Step 1.1 complete: Filtered text ({filter_result['removed_ratio']*100:.1f}% noise removed)")

    # ── Step 1.2: Summarization (Trained Model 🔥) ──────────
    summary_result = await summarize_text(filtered_text)
    summarized_text = summary_result["summary"]
    logger.info(f"[{job_id}] Step 1.2 complete: Summarized text ({summary_result['compression_ratio']*100:.1f}% compression)")

    # ── Step 2: Generate Scenes (LLM) ──────────────────────
    language_name = SUPPORTED_LANGUAGES.get(target_language, "English")
    scenes = await generate_scenes(summarized_text, language_name, learning_mode)
    logger.info(f"[{job_id}] Step 2 complete: {scenes.get('total_scenes', 0)} scenes generated [{learning_mode}]")

    # ── Steps 2.1 + 3 in PARALLEL (quiz + emotions don't depend on each other)
    import asyncio as _asyncio

    quiz_data, scenes = await _asyncio.gather(
        generate_quiz_from_model(
            content=summarized_text,
            num_questions=5,
            difficulty="medium",
            language=language_name,
        ),
        detect_scene_emotions(scenes),   # returns updated scenes
    )
    logger.info(f"[{job_id}] Steps 2.1+3 complete: quiz={quiz_data.get('total_questions',0)}q, emotions done")

    # ── Step 4: Translate (if not English) ──────────────────
    if target_language != "en":
        scenes = await translate_scenes(scenes, target_language)
        logger.info(f"[{job_id}] Step 4 complete: Translated to {language_name}")

    # ── Step 5: Generate TTS Audio ──────────────────────────
    scenes = await generate_scene_audio(scenes, target_language)
    logger.info(f"[{job_id}] Step 5 complete: Audio generated")

    # ── Step 6: Generate Subtitles ──────────────────────────
    subtitle_result = await generate_subtitles(scenes)
    logger.info(f"[{job_id}] Step 6 complete: {subtitle_result['total_entries']} subtitle entries")

    # ── Step 7: Generate Video ──────────────────────────────
    video_result = None
    if generate_video_flag:
        video_result = await generate_video(scenes, lang_code=target_language)
        logger.info(f"[{job_id}] Step 7 complete: Video rendered ({video_result['duration']}s)")

        # ── Step 7.1: Save to history & return share info ───
        vid_record = save_video_record(
            user_id=user_id,
            filename=video_result["filename"],
            title=scenes.get("title", "EduGenAI Video"),
            duration=video_result["duration"],
            scenes=video_result["total_scenes"],
            language=target_language,
            learning_mode=learning_mode,
            render_time=video_result.get("render_time_s", 0),
        )
        video_result["video_record_id"] = vid_record["id"]
        video_result["share_token"] = vid_record["share_token"]

    # ── Build Response ──────────────────────────────────────
    response = {
        "job_id": job_id,
        "status": "completed",
        "input_type": input_type,
        "input_length": len(content),
        "target_language": target_language,
        "scenes": scenes,
        "subtitle": subtitle_result,
        "quiz": quiz_data, # Added quiz data to response
        "knowledge_base": {
            "was_enriched": kb_result["was_enriched"],
            "source": kb_result["source"]
        },
        "models_used": {
            "filter": filter_result["model_used"],
            "summarizer": summary_result["model_used"],
            "quiz": quiz_data.get("model_used", "unknown")
        }
    }

    if video_result:
        response["video"] = video_result

    logger.info(f"[{job_id}] ✅ Pipeline complete!")
    return response


@router.post("/text-only")
async def generate_from_text(
    text: str = Form(...),
    target_language: str = Form("en"),
):
    """
    Generate scenes from text input only (no video rendering).
    Faster — useful for previewing scenes before full generation.
    """
    language_name = SUPPORTED_LANGUAGES.get(target_language, "English")
    scenes = await generate_scenes(text, language_name)
    scenes = await detect_scene_emotions(scenes)

    if target_language != "en":
        scenes = await translate_scenes(scenes, target_language)

    return {
        "status": "completed",
        "scenes": scenes,
        "target_language": target_language,
    }


@router.post("/ocr")
async def extract_text(
    file: UploadFile = File(...),
    language: str = Form("eng"),
):
    """
    Extract text from an image or PDF (OCR only, no generation).
    """
    file_bytes = await file.read()
    filename = file.filename.lower()

    if filename.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")):
        result = await extract_text_from_image(file_bytes, language)
    elif filename.endswith(".pdf"):
        result = await extract_text_from_pdf(file_bytes)
    else:
        raise HTTPException(400, "Unsupported file format. Use image or PDF.")

    return {"status": "completed", "result": result}


@router.get("/languages")
async def list_languages():
    """List all supported output languages."""
    return {"languages": SUPPORTED_LANGUAGES}
