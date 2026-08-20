"""
EduGenAI - Sharing & Video History Service
Manages share links, user video history, and progress tracking.
Storage: local JSON (acts as lightweight cloud within the backend).
"""
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import MODELS_DIR, VIDEO_DIR

logger = logging.getLogger(__name__)

SHARING_FILE = MODELS_DIR / "sharing_data.json"
BASE_URL = "http://localhost:8000"


def _load() -> dict:
    try:
        if SHARING_FILE.exists():
            return json.loads(SHARING_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"share_links": {}, "user_videos": {}}


def _save(data: dict):
    SHARING_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


# ── Video History ────────────────────────────────────────────

def save_video_record(
    user_id: str,
    filename: str,
    title: str,
    duration: float,
    scenes: int,
    language: str,
    learning_mode: str,
    render_time: float = 0,
) -> dict:
    """Save a generated video to user history."""
    data = _load()
    if user_id not in data["user_videos"]:
        data["user_videos"][user_id] = []

    record = {
        "id": uuid.uuid4().hex[:10],
        "filename": filename,
        "title": title,
        "duration": duration,
        "scenes": scenes,
        "language": language,
        "learning_mode": learning_mode,
        "render_time": render_time,
        "created_at": datetime.now().isoformat(),
        "video_url": f"/outputs/video/{filename}",
        "share_token": None,
    }
    data["user_videos"][user_id].insert(0, record)
    data["user_videos"][user_id] = data["user_videos"][user_id][:50]  # keep last 50
    _save(data)
    logger.info(f"Saved video record for user {user_id}: {filename}")
    return record


def get_user_videos(user_id: str) -> list[dict]:
    """Return all videos for a user, newest first."""
    data = _load()
    videos = data["user_videos"].get(user_id, [])
    # Enrich with live share URL
    for v in videos:
        if v.get("share_token"):
            v["share_url"] = f"{BASE_URL}/api/share/{v['share_token']}"
        # Check file still exists
        v["exists"] = (VIDEO_DIR / v["filename"]).exists()
    return videos


# ── Share Links ──────────────────────────────────────────────

def create_share_link(
    user_id: str,
    filename: str,
    title: str,
    duration: float,
) -> dict:
    """Create a public shareable link for a video."""
    data = _load()
    token = uuid.uuid4().hex[:16]

    share_record = {
        "token": token,
        "user_id": user_id,
        "filename": filename,
        "title": title,
        "duration": duration,
        "created_at": datetime.now().isoformat(),
        "views": 0,
    }
    data["share_links"][token] = share_record

    # Also update user_videos record if found
    for vid in data["user_videos"].get(user_id, []):
        if vid["filename"] == filename:
            vid["share_token"] = token
            break

    _save(data)
    share_url = f"{BASE_URL}/api/share/{token}"
    logger.info(f"Share link created: {share_url}")
    return {"token": token, "share_url": share_url, **share_record}


def get_shared_video(token: str) -> Optional[dict]:
    """Retrieve share link metadata. Returns None if not found."""
    data = _load()
    record = data["share_links"].get(token)
    if not record:
        return None
    # Increment view count
    record["views"] = record.get("views", 0) + 1
    _save(data)
    return {
        **record,
        "video_url": f"/outputs/video/{record['filename']}",
        "exists": (VIDEO_DIR / record["filename"]).exists(),
    }
