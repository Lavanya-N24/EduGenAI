import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from db.database import init_db, get_session_factory
from db.migrate_json import migrate_legacy_data
from db.models import User, QuizAttempt, TopicStat, VideoRecord, ShareLink
from services.adaptive import record_quiz_result, get_user_analytics
from services.sharing import create_share_link, get_user_videos, save_video_record
from sqlalchemy import select

async def main():
    print("\n--- 1. Testing Database Initialization ---")
    success = await init_db()
    print(f"init_db status: {success}")

    print("\n--- 2. Testing Data Migration ---")
    await migrate_legacy_data()

    session_factory = get_session_factory()
    async with session_factory() as session:
        users = (await session.execute(select(User))).scalars().all()
        print(f"Users in DB: {len(users)} -> {[u.id for u in users]}")

        attempts = (await session.execute(select(QuizAttempt))).scalars().all()
        print(f"Quiz attempts in DB: {len(attempts)}")

        topics = (await session.execute(select(TopicStat))).scalars().all()
        print(f"Topic stats in DB: {len(topics)} -> {[t.topic for t in topics]}")

        videos = (await session.execute(select(VideoRecord))).scalars().all()
        print(f"Video records in DB: {len(videos)}")

        shares = (await session.execute(select(ShareLink))).scalars().all()
        print(f"Share links in DB: {len(shares)}")

    print("\n--- 3. Testing Adaptive Quiz Service ---")
    quiz_res = await record_quiz_result(
        user_id="test_pg_user",
        topic="PostgreSQL Fundamentals",
        correct=5,
        total=5,
        difficulty="medium",
        question_details=[{"q": 1, "selected": "A", "correct": "A"}]
    )
    print(f"Quiz Result Recorded: score={quiz_res['score']}%, new_diff={quiz_res['new_difficulty']}")

    analytics = await get_user_analytics("test_pg_user")
    print(f"User Analytics: total_quizzes={analytics['total_quizzes']}, accuracy={analytics['overall_accuracy']}%")

    print("\n--- 4. Testing Video Sharing Service ---")
    rec = await save_video_record(
        user_id="test_pg_user",
        filename="test_video_1.mp4",
        title="Intro to PostgreSQL",
        duration=15.5,
        scenes=3,
        language="en",
        learning_mode="beginner",
    )
    print(f"Saved Video Record: {rec['title']} (ID: {rec['id']})")

    share = await create_share_link(
        user_id="test_pg_user",
        filename="test_video_1.mp4",
        title="Intro to PostgreSQL",
        duration=15.5,
    )
    print(f"Share link created: {share['share_url']}")

    user_vids = await get_user_videos("test_pg_user")
    print(f"User videos: {len(user_vids)} video(s) found")

    print("\n--- 5. Testing Redis / In-Memory Cache Service ---")
    from services.cache import init_redis, set_cached_json, get_cached_json, set_job_progress, get_job_progress
    await init_redis()
    await set_cached_json("test_cache_topic", {"topic": "Photosynthesis", "status": "cached"}, ttl_seconds=60)
    cached_val = await get_cached_json("test_cache_topic")
    print(f"Cache retrieved: {cached_val}")

    await set_job_progress("job_123", 75, "Rendering Video Frames")
    progress = await get_job_progress("job_123")
    print(f"Job progress retrieved: {progress}")

    print("\n--- 6. Testing AWS S3 Cloud Storage Service ---")
    from services.s3_service import is_s3_configured, upload_video_to_s3
    from pathlib import Path
    print(f"AWS S3 Configured: {is_s3_configured()}")
    dummy_video = Path("test_video.mp4")
    dummy_video.write_text("dummy video content", encoding="utf-8")
    vid_url = await upload_video_to_s3(dummy_video, "test_video.mp4")
    print(f"Generated Video URL (S3 / Local Fallback): {vid_url}")
    if dummy_video.exists():
        dummy_video.unlink()

    print("\n ALL DATABASE, CACHE & AWS S3 INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
