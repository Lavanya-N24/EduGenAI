"""
EduGenAI - Tutor Route
API endpoint for the AI Tutor chat-based learning system.
Uses RAG (Retrieval-Augmented Generation) with lesson content as context.
"""
import logging
from fastapi import APIRouter
from models.request_models import TutorRequest
from models.response_models import TutorResponse

from services.llm import tutor_chat
from services.adaptive import get_user_analytics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])


@router.post("/chat", response_model=TutorResponse)
async def chat_with_tutor(request: TutorRequest):
    """
    Chat with the AI Tutor.
    The tutor uses the lesson content as context (RAG) and adapts to
    the student's learning level based on their quiz history.
    """
    # Get user's learning state for personalization
    analytics = await get_user_analytics(request.user_id)

    difficulty = "medium"
    weak_areas = "none identified yet"

    if analytics.get("has_data"):
        difficulty = analytics.get("current_difficulty", "medium")
        weak = analytics.get("weak_areas", [])
        weak_areas = ", ".join(weak) if weak else "none identified yet"

    # Convert chat history to dict format
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.chat_history
    ]

    # Get tutor response
    response = await tutor_chat(
        message=request.message,
        context=request.context,
        chat_history=history,
        difficulty=difficulty,
        weak_areas=weak_areas,
        language=request.language,
    )

    return {
        "status": "completed",
        "response": response,
        "tutor_name": "EduBot",
        "student_level": difficulty,
    }
