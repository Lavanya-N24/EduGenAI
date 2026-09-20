"""
EduGenAI - JSON to Database Migration Utility
Migrates legacy user_progress.json and sharing_data.json into the relational database.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import select
from db.database import get_session_factory
from db.models import User, QuizAttempt, TopicStat, VideoRecord, ShareLink
from config import MODELS_DIR

logger = logging.getLogger("EduGenAI.DBMigration")

USER_PROGRESS_FILE = MODELS_DIR / "user_progress.json"
SHARING_DATA_FILE = MODELS_DIR / "sharing_data.json"


async def migrate_legacy_data():
    """Migrate JSON data into PostgreSQL / SQLite database if not already present."""
    session_factory = get_session_factory()
    
    # ── 1. Migrate user_progress.json ──────────────────────────────
    if USER_PROGRESS_FILE.exists():
        try:
            content = json.loads(USER_PROGRESS_FILE.read_text(encoding="utf-8"))
            users_data = content.get("users", {})
            
            async with session_factory() as session:
                for user_id, udata in users_data.items():
                    # Check if user already exists
                    result = await session.execute(select(User).where(User.id == user_id))
                    user = result.scalar_one_or_none()
                    
                    if not user:
                        user = User(
                            id=user_id,
                            current_difficulty=udata.get("current_difficulty", "medium"),
                            total_quizzes=udata.get("total_quizzes", 0),
                            total_correct=udata.get("total_correct", 0),
                            total_questions=udata.get("total_questions", 0),
                        )
                        session.add(user)
                        await session.flush()
                        
                        # Migrate topic stats
                        for topic_name, tdata in udata.get("topics", {}).items():
                            stat = TopicStat(
                                user_id=user_id,
                                topic=topic_name,
                                avg_score=tdata.get("avg_score", 0.0),
                                attempts=tdata.get("attempts", 0),
                                last_difficulty=tdata.get("last_difficulty", "medium"),
                                recent_scores=tdata.get("scores", []),
                            )
                            session.add(stat)
                        
                        # Migrate sessions
                        for s in udata.get("sessions", []):
                            ts_str = s.get("timestamp")
                            ts = datetime.fromisoformat(ts_str) if ts_str else datetime.utcnow()
                            attempt = QuizAttempt(
                                user_id=user_id,
                                topic=s.get("topic", "General"),
                                correct=s.get("correct", 0),
                                total=s.get("total", 0),
                                score=s.get("score", 0.0),
                                difficulty=s.get("difficulty", "medium"),
                                created_at=ts,
                            )
                            session.add(attempt)
                            
                await session.commit()
                logger.info("Migrated user progress data from user_progress.json into database.")
        except Exception as e:
            logger.warning(f"Note: Legacy user_progress migration skipped or encountered: {e}")

    # ── 2. Migrate sharing_data.json ──────────────────────────────
    if SHARING_DATA_FILE.exists():
        try:
            content = json.loads(SHARING_DATA_FILE.read_text(encoding="utf-8"))
            user_videos = content.get("user_videos", {})
            share_links = content.get("share_links", {})
            
            async with session_factory() as session:
                for user_id, videos in user_videos.items():
                    for v in videos:
                        vid = v.get("id") or v.get("filename")
                        result = await session.execute(select(VideoRecord).where(VideoRecord.filename == v.get("filename")))
                        if not result.scalar_one_or_none():
                            created_at_str = v.get("created_at")
                            dt = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                            rec = VideoRecord(
                                id=vid,
                                user_id=user_id,
                                filename=v.get("filename", ""),
                                title=v.get("title", "Untitled"),
                                duration=v.get("duration", 0.0),
                                scenes=v.get("scenes", 1),
                                language=v.get("language", "en"),
                                learning_mode=v.get("learning_mode", "beginner"),
                                render_time=v.get("render_time", 0.0),
                                video_url=v.get("video_url", f"/outputs/video/{v.get('filename')}"),
                                share_token=v.get("share_token"),
                                created_at=dt,
                            )
                            session.add(rec)

                for token, s in share_links.items():
                    result = await session.execute(select(ShareLink).where(ShareLink.token == token))
                    if not result.scalar_one_or_none():
                        created_at_str = s.get("created_at")
                        dt = datetime.fromisoformat(created_at_str) if created_at_str else datetime.utcnow()
                        link = ShareLink(
                            token=token,
                            user_id=s.get("user_id", "default_user"),
                            filename=s.get("filename", ""),
                            title=s.get("title", "Untitled"),
                            duration=s.get("duration", 0.0),
                            views=s.get("views", 0),
                            created_at=dt,
                        )
                        session.add(link)

                await session.commit()
                logger.info("Migrated sharing data from sharing_data.json into database.")
        except Exception as e:
            logger.warning(f"Note: Legacy sharing migration skipped or encountered: {e}")
