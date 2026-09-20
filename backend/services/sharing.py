"""
EduGenAI - Sharing & Video History Service
Manages share links, user video history, and progress tracking using PostgreSQL / SQLite.
"""
import uuid
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select, desc
from db.database import get_session_factory
from db.models import VideoRecord, ShareLink
from config import VIDEO_DIR

logger = logging.getLogger(__name__)
BASE_URL = "http://localhost:8000"


async def save_video_record(
    user_id: str,
    filename: str,
    title: str,
    duration: float,
    scenes: int,
    language: str,
    learning_mode: str,
    render_time: float = 0.0,
    video_url: Optional[str] = None,
) -> dict:
    """Save a generated video to user history in the database."""
    session_factory = get_session_factory()
    record_id = uuid.uuid4().hex[:10]
    final_video_url = video_url or f"/outputs/video/{filename}"

    async with session_factory() as session:
        # Check if record for this filename already exists
        res = await session.execute(select(VideoRecord).where(VideoRecord.filename == filename))
        record = res.scalar_one_or_none()

        if record:
            record.title = title
            record.duration = duration
            record.scenes = scenes
            record.language = language
            record.learning_mode = learning_mode
            record.render_time = render_time
            if video_url:
                record.video_url = video_url
        else:
            record = VideoRecord(
                id=record_id,
                user_id=user_id,
                filename=filename,
                title=title,
                duration=duration,
                scenes=scenes,
                language=language,
                learning_mode=learning_mode,
                render_time=render_time,
                video_url=final_video_url,
                share_token=None,
                created_at=datetime.utcnow(),
            )
            session.add(record)

        await session.commit()
        logger.info(f"Saved video record to database for user {user_id}: {filename}")
        return record.to_dict()


async def get_user_videos(user_id: str) -> list[dict]:
    """Return all videos for a user, newest first, enriched with live status."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        res = await session.execute(
            select(VideoRecord)
            .where(VideoRecord.user_id == user_id)
            .order_by(desc(VideoRecord.created_at))
            .limit(50)
        )
        records = res.scalars().all()

        video_list = []
        for v in records:
            v_dict = v.to_dict()
            if v.share_token:
                v_dict["share_url"] = f"{BASE_URL}/api/share/{v.share_token}"
            v_dict["exists"] = (VIDEO_DIR / v.filename).exists()
            video_list.append(v_dict)

        return video_list


async def create_share_link(
    user_id: str,
    filename: str,
    title: str,
    duration: float,
) -> dict:
    """Create a public shareable link for a video in the database."""
    session_factory = get_session_factory()
    token = uuid.uuid4().hex[:16]

    async with session_factory() as session:
        # Create share link record
        share_link = ShareLink(
            token=token,
            user_id=user_id,
            filename=filename,
            title=title,
            duration=duration,
            views=0,
            created_at=datetime.utcnow(),
        )
        session.add(share_link)

        # Update matching VideoRecord share_token if it exists
        res = await session.execute(
            select(VideoRecord).where(VideoRecord.filename == filename)
        )
        video = res.scalar_one_or_none()
        if video:
            video.share_token = token

        await session.commit()

        share_url = f"{BASE_URL}/api/share/{token}"
        logger.info(f"Share link created in database: {share_url}")
        res_dict = share_link.to_dict()
        res_dict["share_url"] = share_url
        return res_dict


async def get_shared_video(token: str) -> Optional[dict]:
    """Retrieve share link metadata from the database and increment view count."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        res = await session.execute(select(ShareLink).where(ShareLink.token == token))
        record = res.scalar_one_or_none()
        if not record:
            return None

        record.views += 1
        await session.commit()

        res_dict = record.to_dict()
        res_dict["video_url"] = f"/outputs/video/{record.filename}"
        res_dict["exists"] = (VIDEO_DIR / record.filename).exists()
        return res_dict
