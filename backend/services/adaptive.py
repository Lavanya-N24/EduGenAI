"""
EduGenAI - Adaptive Learning Service
Tracks user performance and adjusts difficulty based on quiz results.

Algorithm: Simple adaptive algorithm based on performance windows.
- Tracks last N quiz scores per topic
- Adjusts difficulty: if avg score > 80% → harder, < 50% → easier
- Identifies weak areas by topic
- Generates learning recommendations
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from config import MODELS_DIR

logger = logging.getLogger(__name__)

PROGRESS_FILE = MODELS_DIR / "user_progress.json"


def _load_progress() -> dict:
    """Load user progress data from JSON file."""
    try:
        if PROGRESS_FILE.exists():
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        pass
    return {"users": {}, "schema_version": "1.0"}


def _save_progress(data: dict):
    """Save user progress data to JSON file."""
    PROGRESS_FILE.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def _ensure_user(data: dict, user_id: str) -> dict:
    """Ensure user entry exists in progress data."""
    if user_id not in data["users"]:
        data["users"][user_id] = {
            "created_at": datetime.now().isoformat(),
            "current_difficulty": "medium",
            "total_quizzes": 0,
            "total_correct": 0,
            "total_questions": 0,
            "topics": {},
            "sessions": [],
            "weak_areas": [],
            "strong_areas": [],
        }
    return data["users"][user_id]


async def record_quiz_result(
    user_id: str,
    topic: str,
    correct: int,
    total: int,
    difficulty: str,
    question_details: list[dict] = None,
) -> dict:
    """
    Record a quiz result and update user adaptive state.

    Args:
        user_id: Unique user identifier
        topic: Topic/subject of the quiz
        correct: Number of correct answers
        total: Total number of questions
        difficulty: Difficulty level of the quiz
        question_details: Optional list of per-question results

    Returns:
        dict with updated difficulty, feedback, and recommendations
    """
    data = _load_progress()
    user = _ensure_user(data, user_id)

    score = (correct / total * 100) if total > 0 else 0

    # Update global stats
    user["total_quizzes"] += 1
    user["total_correct"] += correct
    user["total_questions"] += total

    # Update topic-specific stats
    if topic not in user["topics"]:
        user["topics"][topic] = {
            "scores": [],
            "avg_score": 0,
            "attempts": 0,
            "last_difficulty": difficulty,
        }

    topic_data = user["topics"][topic]
    topic_data["scores"].append(score)
    topic_data["scores"] = topic_data["scores"][-10:]  # Keep last 10 scores
    topic_data["avg_score"] = sum(topic_data["scores"]) / len(topic_data["scores"])
    topic_data["attempts"] += 1

    # Record session
    user["sessions"].append({
        "timestamp": datetime.now().isoformat(),
        "topic": topic,
        "score": score,
        "correct": correct,
        "total": total,
        "difficulty": difficulty,
    })
    user["sessions"] = user["sessions"][-50:]  # Keep last 50 sessions

    # ── Adaptive Difficulty Algorithm ───────────────────────
    new_difficulty = _calculate_new_difficulty(topic_data, difficulty)
    topic_data["last_difficulty"] = new_difficulty
    user["current_difficulty"] = new_difficulty

    # ── Identify Weak/Strong Areas ─────────────────────────
    user["weak_areas"] = [
        t for t, d in user["topics"].items()
        if d["avg_score"] < 50 and d["attempts"] >= 2
    ]
    user["strong_areas"] = [
        t for t, d in user["topics"].items()
        if d["avg_score"] >= 80 and d["attempts"] >= 2
    ]

    _save_progress(data)

    # Generate feedback
    feedback = _generate_feedback(score, new_difficulty, user)

    logger.info(
        f"User {user_id}: {topic} → {score:.0f}% | "
        f"Difficulty: {difficulty} → {new_difficulty}"
    )

    return {
        "score": round(score, 1),
        "new_difficulty": new_difficulty,
        "previous_difficulty": difficulty,
        "difficulty_changed": new_difficulty != difficulty,
        "feedback": feedback,
        "topic_avg_score": round(topic_data["avg_score"], 1),
        "weak_areas": user["weak_areas"],
        "strong_areas": user["strong_areas"],
        "total_quizzes_taken": user["total_quizzes"],
    }


def _calculate_new_difficulty(topic_data: dict, current: str) -> str:
    """
    Adaptive difficulty algorithm.
    Uses a sliding window of recent scores to adjust difficulty.
    """
    levels = ["easy", "medium", "hard"]
    current_idx = levels.index(current) if current in levels else 1

    avg = topic_data["avg_score"]
    attempts = topic_data["attempts"]

    # Need at least 2 attempts before changing difficulty
    if attempts < 2:
        return current

    if avg >= 80 and current_idx < 2:
        return levels[current_idx + 1]  # Increase difficulty
    elif avg < 50 and current_idx > 0:
        return levels[current_idx - 1]  # Decrease difficulty

    return current


def _generate_feedback(score: float, difficulty: str, user: dict) -> dict:
    """Generate personalized feedback based on performance."""
    if score >= 90:
        message = "🌟 Excellent! You've mastered this topic!"
        recommendation = "Try the next difficulty level or explore related topics."
    elif score >= 70:
        message = "👍 Good job! You're on the right track."
        recommendation = "Review the concepts you missed and try again."
    elif score >= 50:
        message = "📚 Keep practicing! You're making progress."
        recommendation = "Re-watch the video sections for topics you found difficult."
    else:
        message = "💪 Don't give up! Let's review together."
        recommendation = "Use the AI Tutor to go through the concepts step by step."

    return {
        "message": message,
        "recommendation": recommendation,
        "weak_topics": user["weak_areas"],
        "next_difficulty": difficulty,
    }


async def get_user_analytics(user_id: str) -> dict:
    """
    Get comprehensive learning analytics for a user.

    Returns:
        dict with performance metrics, trends, and recommendations
    """
    data = _load_progress()

    if user_id not in data["users"]:
        return {
            "user_id": user_id,
            "has_data": False,
            "message": "No learning history found. Take a quiz to get started!",
        }

    user = data["users"][user_id]

    # Calculate overall accuracy
    overall_accuracy = (
        (user["total_correct"] / user["total_questions"] * 100)
        if user["total_questions"] > 0
        else 0
    )

    # Performance trend (last 5 sessions)
    recent_sessions = user["sessions"][-5:]
    trend = [s["score"] for s in recent_sessions]
    trend_direction = "improving" if len(trend) >= 2 and trend[-1] > trend[0] else "needs_attention"

    # Topic breakdown
    topic_breakdown = {
        topic: {
            "average_score": round(d["avg_score"], 1),
            "attempts": d["attempts"],
            "difficulty": d["last_difficulty"],
            "status": "strong" if d["avg_score"] >= 70 else "weak",
        }
        for topic, d in user["topics"].items()
    }

    return {
        "user_id": user_id,
        "has_data": True,
        "overall_accuracy": round(overall_accuracy, 1),
        "total_quizzes": user["total_quizzes"],
        "total_questions_answered": user["total_questions"],
        "current_difficulty": user["current_difficulty"],
        "weak_areas": user["weak_areas"],
        "strong_areas": user["strong_areas"],
        "performance_trend": trend,
        "trend_direction": trend_direction,
        "topic_breakdown": topic_breakdown,
        "recent_sessions": recent_sessions,
    }
