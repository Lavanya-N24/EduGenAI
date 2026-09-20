"""
EduGenAI - Adaptive Learning Service
Tracks user performance and adjusts difficulty based on quiz results using PostgreSQL / SQLite.

Algorithm: Simple adaptive algorithm based on performance windows.
- Tracks last N quiz scores per topic
- Adjusts difficulty: if avg score > 80% → harder, < 50% → easier
- Identifies weak areas by topic
- Generates learning recommendations
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, desc
from db.database import get_session_factory
from db.models import User, QuizAttempt, TopicStat

logger = logging.getLogger(__name__)


def _calculate_new_difficulty(avg_score: float, current: str) -> str:
    """
    Adaptive difficulty algorithm.
    Uses score averages to adjust difficulty level.
    """
    levels = ["easy", "medium", "hard"]
    current_idx = levels.index(current) if current in levels else 1

    if avg_score >= 80 and current_idx < 2:
        return levels[current_idx + 1]  # Increase difficulty
    elif avg_score < 50 and current_idx > 0:
        return levels[current_idx - 1]  # Decrease difficulty

    return current


def _generate_feedback(score: float, difficulty: str, weak_topics: list[str]) -> dict:
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
        "weak_topics": weak_topics,
        "next_difficulty": difficulty,
    }


async def record_quiz_result(
    user_id: str,
    topic: str,
    correct: int,
    total: int,
    difficulty: str,
    question_details: list[dict] = None,
) -> dict:
    """
    Record a quiz result and update user adaptive state in the database.
    """
    session_factory = get_session_factory()
    score = (correct / total * 100) if total > 0 else 0.0

    async with session_factory() as session:
        # 1. Fetch or create User
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                id=user_id,
                current_difficulty=difficulty or "medium",
                total_quizzes=0,
                total_correct=0,
                total_questions=0,
            )
            session.add(user)
            await session.flush()

        # Update global user metrics
        user.total_quizzes += 1
        user.total_correct += correct
        user.total_questions += total

        # 2. Record Quiz Attempt
        attempt = QuizAttempt(
            user_id=user_id,
            topic=topic,
            correct=correct,
            total=total,
            score=round(score, 1),
            difficulty=difficulty,
            question_details=question_details or [],
            created_at=datetime.utcnow(),
        )
        session.add(attempt)

        # 3. Fetch or create TopicStat
        res = await session.execute(
            select(TopicStat).where(TopicStat.user_id == user_id, TopicStat.topic == topic)
        )
        topic_stat = res.scalar_one_or_none()
        if not topic_stat:
            topic_stat = TopicStat(
                user_id=user_id,
                topic=topic,
                avg_score=score,
                attempts=1,
                last_difficulty=difficulty,
                recent_scores=[score],
            )
            session.add(topic_stat)
        else:
            scores = list(topic_stat.recent_scores or [])
            scores.append(score)
            scores = scores[-10:]  # Keep last 10 scores
            topic_stat.recent_scores = scores
            topic_stat.avg_score = round(sum(scores) / len(scores), 1)
            topic_stat.attempts += 1

        # 4. Calculate new adaptive difficulty
        new_difficulty = _calculate_new_difficulty(topic_stat.avg_score, difficulty)
        topic_stat.last_difficulty = new_difficulty
        user.current_difficulty = new_difficulty

        await session.commit()

        # 5. Fetch all user topic stats to determine weak/strong areas
        res_all_topics = await session.execute(
            select(TopicStat).where(TopicStat.user_id == user_id)
        )
        all_topics = res_all_topics.scalars().all()

        weak_areas = [t.topic for t in all_topics if t.avg_score < 60 and t.attempts >= 1]
        strong_areas = [t.topic for t in all_topics if t.avg_score >= 70 and t.attempts >= 1]

        feedback = _generate_feedback(score, new_difficulty, weak_areas)

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
            "topic_avg_score": round(topic_stat.avg_score, 1),
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "total_quizzes_taken": user.total_quizzes,
        }


async def get_user_analytics(user_id: str) -> dict:
    """
    Get comprehensive learning analytics for a user from the database.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        # Check if user exists
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalar_one_or_none()

        if not user:
            # Fallback to any user if exists
            res_any = await session.execute(select(User).limit(1))
            user = res_any.scalar_one_or_none()

        if not user:
            return {
                "user_id": user_id,
                "has_data": False,
                "overall_accuracy": 0,
                "total_quizzes": 0,
                "total_questions_answered": 0,
                "current_difficulty": "medium",
                "weak_areas": [],
                "strong_areas": [],
                "performance_trend": [],
                "trend_direction": "neutral",
                "topic_breakdown": {},
                "recent_sessions": [],
            }

        target_id = user.id

        # Calculate overall accuracy
        overall_accuracy = (
            (user.total_correct / user.total_questions * 100)
            if user.total_questions > 0
            else 0.0
        )

        # Get recent quiz attempts (last 10)
        res_attempts = await session.execute(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == target_id)
            .order_by(desc(QuizAttempt.created_at))
            .limit(10)
        )
        recent_attempts = list(reversed(res_attempts.scalars().all()))

        trend = [a.score for a in recent_attempts]
        trend_direction = "improving" if len(trend) >= 2 and trend[-1] >= trend[0] else "steady"

        # Get topic stats
        res_topics = await session.execute(
            select(TopicStat).where(TopicStat.user_id == target_id)
        )
        topics = res_topics.scalars().all()

        topic_breakdown = {
            t.topic: {
                "average_score": round(t.avg_score, 1),
                "attempts": t.attempts,
                "difficulty": t.last_difficulty,
                "status": "strong" if t.avg_score >= 70 else "weak",
            }
            for t in topics
        }

        weak_areas = [t.topic for t in topics if t.avg_score < 60 and t.attempts >= 1]
        strong_areas = [t.topic for t in topics if t.avg_score >= 70 and t.attempts >= 1]

        recent_sessions = [a.to_dict() for a in recent_attempts]

        return {
            "user_id": user_id,
            "has_data": True,
            "overall_accuracy": round(overall_accuracy, 1),
            "total_quizzes": user.total_quizzes,
            "total_questions_answered": user.total_questions,
            "current_difficulty": user.current_difficulty or "medium",
            "weak_areas": weak_areas,
            "strong_areas": strong_areas,
            "performance_trend": trend,
            "trend_direction": trend_direction,
            "topic_breakdown": topic_breakdown,
            "recent_sessions": recent_sessions,
        }
