"""
EduGenAI - Sharing & Video History Routes
Public endpoints for share links and user video history.
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

from services.sharing import (
    create_share_link,
    get_shared_video,
    get_user_videos,
)
from config import VIDEO_DIR

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Sharing"])


class ShareRequest(BaseModel):
    user_id: str
    filename: str
    title: str
    duration: float = 0


# ── Create share link ────────────────────────────────────────
@router.post("/share")
async def create_share(req: ShareRequest):
    """Create a shareable public link for a video."""
    video_path = VIDEO_DIR / req.filename
    if not video_path.exists():
        raise HTTPException(404, f"Video '{req.filename}' not found on server.")
    result = await create_share_link(
        user_id=req.user_id,
        filename=req.filename,
        title=req.title,
        duration=req.duration,
    )
    return result


# ── View shared video (public) ───────────────────────────────
@router.get("/share/{token}")
async def view_shared_video(token: str):
    """Return metadata for a shared video (anyone can call this)."""
    record = await get_shared_video(token)
    if not record:
        raise HTTPException(404, "Share link not found or expired.")
    return record


# ── Redirect to actual video file ────────────────────────────
@router.get("/share/{token}/play")
async def play_shared_video(token: str):
    """Redirect to the actual mp4 file."""
    record = await get_shared_video(token)
    if not record:
        raise HTTPException(404, "Share link not found.")
    if not record.get("exists"):
        raise HTTPException(410, "Video file no longer available.")
    return RedirectResponse(url=record["video_url"])


# ── User video history ───────────────────────────────────────
@router.get("/user/{user_id}/videos")
async def get_video_history(user_id: str):
    """Return all generated videos for a user."""
    videos = await get_user_videos(user_id)
    return {
        "user_id": user_id,
        "total": len(videos),
        "videos": videos,
    }
