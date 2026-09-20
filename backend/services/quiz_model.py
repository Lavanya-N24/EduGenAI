"""
EduGenAI - Quiz Generation Service
Uses Groq LLM to generate proper MCQ quiz questions.
Falls back gracefully if the trained T5 model isn't available.
"""
import logging
import json
from services.model_loader import get_quiz_model

logger = logging.getLogger(__name__)

MAX_INPUT_TOKENS  = 128
MAX_OUTPUT_TOKENS = 64
NUM_BEAMS         = 4


from services.cache import get_cached_json, set_cached_json, make_cache_key


async def generate_quiz_from_model(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    language: str = "English",
) -> dict:
    """
    Generate proper 4-option MCQ quiz questions.
    Uses Redis caching to deliver sub-millisecond responses on recurring topics.
    """
    # ── 1. Check Redis Cache ─────────────────────────────────
    cache_key = make_cache_key("quiz", language, difficulty, str(num_questions), content[:100])
    cached_quiz = await get_cached_json(cache_key)
    if cached_quiz:
        logger.info(f"⚡ Returning cached quiz for topic ({cache_key})")
        return cached_quiz

    # ── 2. Generate with LLM ─────────────────────────────────
    logger.info(f"Generating {num_questions} {difficulty} quiz questions via Groq LLM...")
    quiz = await _generate_with_groq(content, num_questions, difficulty, language)

    # ── 3. Store in Cache ────────────────────────────────────
    if quiz and quiz.get("questions"):
        await set_cached_json(cache_key, quiz, ttl_seconds=86400)

    return quiz


def _normalize_quiz_data(quiz: dict, difficulty: str, fallback_title: str) -> dict:
    """Ensure all questions have both string and integer correct answer indicators."""
    questions = quiz.get("questions", [])
    normalized_questions = []

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            continue

        raw_options = q.get("options", [])
        if not isinstance(raw_options, list) or len(raw_options) < 2:
            raw_options = ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"]

        # Parse correct answer
        raw_correct = q.get("correct_answer") or q.get("correctAnswer") or "A"
        correct_idx = 0
        correct_letter = "A"

        if isinstance(raw_correct, int):
            correct_idx = max(0, min(raw_correct, len(raw_options) - 1))
            correct_letter = chr(65 + correct_idx)
        elif isinstance(raw_correct, str):
            c_str = raw_correct.strip().upper()
            if c_str.startswith("A") or c_str == "0":
                correct_idx = 0
                correct_letter = "A"
            elif c_str.startswith("B") or c_str == "1":
                correct_idx = 1
                correct_letter = "B"
            elif c_str.startswith("C") or c_str == "2":
                correct_idx = 2
                correct_letter = "C"
            elif c_str.startswith("D") or c_str == "3":
                correct_idx = 3
                correct_letter = "D"
            else:
                for idx, opt in enumerate(raw_options):
                    if c_str in str(opt).upper():
                        correct_idx = idx
                        correct_letter = chr(65 + idx)
                        break

        normalized_questions.append({
            "id": q.get("id", i + 1),
            "question": q.get("question", f"Question {i + 1}"),
            "options": [str(opt) for opt in raw_options],
            "correct_answer": correct_letter,
            "correctAnswer": correct_idx,
            "difficulty": q.get("difficulty", difficulty),
            "explanation": q.get("explanation", "Review the key points of the lesson."),
            "concept_tested": q.get("concept_tested", "Core Concept"),
        })

    quiz["questions"] = normalized_questions
    quiz["total_questions"] = len(normalized_questions)
    quiz.setdefault("quiz_title", fallback_title)
    return quiz


async def _generate_with_groq(
    content: str,
    num_questions: int,
    difficulty: str,
    language: str,
) -> dict:
    """Generate proper MCQ quiz via LLM (Groq / Gemini fallback)."""
    from services.llm import _call_llm

    prompt = f"""Generate a {difficulty} difficulty quiz with exactly {num_questions} multiple-choice questions based on this content.

CONTENT:
{content[:3000]}

LANGUAGE: {language}

Return ONLY valid JSON in this exact format:
{{
  "quiz_title": "Quiz on the Topic",
  "total_questions": {num_questions},
  "questions": [
    {{
      "id": 1,
      "question": "Clear question text?",
      "options": ["A) First option", "B) Second option", "C) Third option", "D) Fourth option"],
      "correct_answer": "A",
      "difficulty": "{difficulty}",
      "explanation": "Brief explanation why A is correct.",
      "concept_tested": "Key concept being tested"
    }}
  ]
}}"""

    try:
        raw = await _call_llm(
            messages=[
                {"role": "system", "content": "You are an expert educational assessment creator. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.5,
            is_json=True,
        )

        quiz = json.loads(raw.strip())
        quiz["model_used"] = "llm_fallback"
        return _normalize_quiz_data(quiz, difficulty, f"Quiz ({difficulty.title()})")

    except Exception as e:
        logger.error(f"LLM quiz generation failed: {e}")
        # Safety fallback
        fallback = {
            "quiz_title": "Knowledge Check",
            "total_questions": 1,
            "questions": [
                {
                    "id": 1,
                    "question": f"Which concept is most essential for understanding this topic?",
                    "options": [
                        "A) Understanding fundamental processes and components",
                        "B) Memorizing arbitrary unrelated terms",
                        "C) Ignoring experimental data",
                        "D) None of the above"
                    ],
                    "correct_answer": "A",
                    "correctAnswer": 0,
                    "difficulty": difficulty,
                    "explanation": "Understanding fundamental processes is the core goal of this topic.",
                    "concept_tested": "Fundamentals"
                }
            ],
            "model_used": "emergency_template",
        }
        return _normalize_quiz_data(fallback, difficulty, "Knowledge Check")


async def _generate_with_t5(
    content: str,
    num_questions: int,
    difficulty: str,
    tokenizer,
    model,
) -> dict:
    """Generate questions with the trained T5 model."""
    try:
        import torch
        paragraphs = _get_context_chunks(content, num_questions)
        enriched = []

        for i, para in enumerate(paragraphs):
            input_text = "generate question: " + para
            inputs = tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=MAX_INPUT_TOKENS,
                padding="max_length",
            )

            with torch.no_grad():
                outputs = model.generate(
                    inputs["input_ids"],
                    max_length=MAX_OUTPUT_TOKENS,
                    num_beams=NUM_BEAMS,
                    early_stopping=True,
                )

            question_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            enriched.append({
                "id": i + 1,
                "question": question_text,
                "options": ["A) True", "B) False", "C) Not mentioned", "D) Cannot determine"],
                "correct_answer": "A",
                "difficulty": difficulty,
                "explanation": f"Based on: {para[:100]}...",
                "concept_tested": "General Comprehension",
            })

        logger.info(f"Quiz generated via T5: {len(enriched)} questions")
        return {
            "quiz_title": "Generated Quiz",
            "total_questions": len(enriched),
            "questions": enriched,
            "model_used": "trained_t5_quiz",
        }

    except Exception as e:
        logger.error(f"T5 quiz inference failed: {e}")
        return await _generate_with_groq(content, num_questions, difficulty, "English")


def _get_context_chunks(text: str, num_chunks: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and len(p.strip()) > 30]

    if len(paragraphs) >= num_chunks:
        step = len(paragraphs) // num_chunks
        return [paragraphs[i * step] for i in range(num_chunks)]

    sentences = [s.strip() for s in text.replace(". ", ".\n").split("\n") if len(s.strip()) > 20]
    step = max(1, len(sentences) // num_chunks)
    chunks = []
    for i in range(min(num_chunks, len(sentences))):
        start = i * step
        chunk = " ".join(sentences[start: start + step])
        if chunk:
            chunks.append(chunk)

    return chunks if chunks else [text[:400]] * min(num_chunks, 1)
