"""
EduGenAI - Quiz Route
API endpoints for quiz generation, submission, and evaluation.
"""
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.request_models import QuizRequest, QuizSubmission
from models.response_models import QuizResponse, QuizSubmissionResponse

from services.quiz_model import generate_quiz_from_model
from services.adaptive import record_quiz_result
from config import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quiz", tags=["Quiz"])


@router.post("/generate", response_model=QuizResponse)
async def create_quiz(request: QuizRequest):
    """
    Generate an MCQ quiz from educational content.
    Uses LLM (Gemini) to create questions at specified difficulty.
    """
    if not request.content.strip():
        raise HTTPException(400, "Content cannot be empty.")

    language_name = SUPPORTED_LANGUAGES.get(request.language, "English")

    quiz = await generate_quiz_from_model(
        content=request.content,
        num_questions=request.num_questions,
        difficulty=request.difficulty,
        language=language_name,
    )

    return {"status": "completed", "quiz": quiz}


@router.post("/submit", response_model=QuizSubmissionResponse)
async def submit_quiz(submission: QuizSubmission):
    """
    Submit quiz answers and get adaptive feedback.
    Updates user progress and adjusts difficulty for next quiz.
    """
    # Calculate score
    correct = sum(
        1 for a in submission.answers
        if a.get("selected") == a.get("correct")
    )
    total = len(submission.answers)

    # Record result and get adaptive feedback
    result = await record_quiz_result(
        user_id=submission.user_id,
        topic=submission.topic,
        correct=correct,
        total=total,
        difficulty=submission.difficulty,
        question_details=submission.answers,
    )

    return {
        "status": "completed",
        "result": result,
    }
