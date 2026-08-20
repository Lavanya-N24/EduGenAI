"""
EduGenAI - Analytics Route
API endpoints for learning analytics dashboard.
"""
import logging
from fastapi import APIRouter

from services.adaptive import get_user_analytics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/{user_id}")
async def get_analytics(user_id: str):
    """
    Get comprehensive learning analytics for a user.

    Returns:
    - Overall accuracy
    - Topic-wise breakdown
    - Performance trends
    - Weak/strong areas
    - Recommendations
    """
    analytics = await get_user_analytics(user_id)
    return {"status": "completed", "analytics": analytics}


@router.get("/{user_id}/weak-areas")
async def get_weak_areas(user_id: str):
    """Get just the weak areas for targeted review."""
    analytics = await get_user_analytics(user_id)

    if not analytics.get("has_data"):
        return {"weak_areas": [], "message": "No data yet. Take a quiz first!"}

    return {
        "weak_areas": analytics.get("weak_areas", []),
        "topic_details": {
            topic: details
            for topic, details in analytics.get("topic_breakdown", {}).items()
            if details.get("status") == "weak"
        },
    }


@router.get("/{user_id}/summary")
async def get_summary(user_id: str):
    """Get a quick summary for the Flutter dashboard."""
    analytics = await get_user_analytics(user_id)

    if not analytics.get("has_data"):
        return {
            "overall_accuracy": 0,
            "total_quizzes": 0,
            "current_level": "beginner",
            "trend": "neutral",
        }

    return {
        "overall_accuracy": analytics.get("overall_accuracy", 0),
        "total_quizzes": analytics.get("total_quizzes", 0),
        "current_level": analytics.get("current_difficulty", "medium"),
        "trend": analytics.get("trend_direction", "neutral"),
        "weak_count": len(analytics.get("weak_areas", [])),
        "strong_count": len(analytics.get("strong_areas", [])),
    }
