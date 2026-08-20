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


async def generate_quiz_from_model(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    language: str = "English",
) -> dict:
    """
    Generate MCQ quiz questions.

    Strategy:
      1. Try the trained T5 model first.
      2. If T5 not available (common), fall back to Groq LLM which
         generates proper 4-option MCQs with correct answers.
    """
    tokenizer, model = get_quiz_model()

    if model is not None and tokenizer is not None:
        return await _generate_with_t5(content, num_questions, difficulty, tokenizer, model)

    # Groq fallback — proper MCQ generation
    logger.info("Quiz T5 model not available — using Groq LLM fallback for quiz generation")
    return await _generate_with_groq(content, num_questions, difficulty, language)


async def _generate_with_groq(
    content: str,
    num_questions: int,
    difficulty: str,
    language: str,
) -> dict:
    """Generate proper MCQ quiz via Groq LLM."""
    try:
        from groq import AsyncGroq
        from config import GROQ_API_KEY

        client = AsyncGroq(api_key=GROQ_API_KEY)

        prompt = f"""Generate a {difficulty} difficulty quiz with exactly {num_questions} multiple-choice questions based on this content.

CONTENT:
{content[:3000]}

LANGUAGE: {language}

Return ONLY valid JSON in this exact format:
{{
  "quiz_title": "Quiz on [topic]",
  "total_questions": {num_questions},
  "questions": [
    {{
      "id": 1,
      "question": "The question text?",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": "A",
      "difficulty": "{difficulty}",
      "explanation": "Brief explanation of why A is correct.",
      "concept_tested": "Key concept being tested"
    }}
  ]
}}"""

        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are an expert quiz generator. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.6,
        )

        quiz = json.loads(response.choices[0].message.content.strip())
        quiz["model_used"] = "groq_llm"

        # Validate structure
        if "questions" not in quiz or not quiz["questions"]:
            raise ValueError("Empty questions list from Groq")

        logger.info(f"Quiz generated via Groq: {quiz.get('total_questions', 0)} questions")
        return quiz

    except Exception as e:
        logger.error(f"Groq quiz generation failed: {e}")
        # Hard fallback with a simple quiz
        return {
            "quiz_title": "Quiz",
            "total_questions": 0,
            "questions": [],
            "model_used": "error_fallback",
            "error": str(e),
        }


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
