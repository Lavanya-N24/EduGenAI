"""
EduGenAI - Pixazo AI Video Generation Service

Interacts with Pixazo's LTX-2.5 Pro text-to-video / image-to-video API.
Falls back seamlessly to local educational animation if API credits/balance
are exhausted or network errors occur.
"""

import logging
import os
import tempfile
import httpx
from typing import Optional
from config import PIXAZO_API_KEY

logger = logging.getLogger(__name__)

PIXAZO_TEXT_TO_VIDEO_URL = "https://gateway.pixazo.ai/ltx-2-5-pro/v1/text-to-video"
TIMEOUT = 45.0


async def generate_pixazo_scene_video(
    prompt: str,
    duration_seconds: int = 6,
    output_path: Optional[str] = None,
) -> Optional[str]:
    """
    Generate an AI video clip using Pixazo LTX-2.5 Pro.
    
    Args:
        prompt: English descriptive prompt for the scene.
        duration_seconds: Duration of the generated clip (typically 6s).
        output_path: File path to save the resulting .mp4.
        
    Returns:
        output_path if successful, None if Pixazo fails or balance is insufficient.
    """
    api_key = (PIXAZO_API_KEY or os.getenv("PIXAZO_API_KEY", "")).strip()
    if not api_key:
        logger.info("PIXAZO_API_KEY not configured. Using local educational animation engine.")
        return None

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": api_key,
    }

    clean_prompt = (
        f"{prompt.strip()}. "
        "Educational 3D scientific animation, clear smooth camera movement, high quality, "
        "no text, no watermark, cinematic lighting."
    )

    payload = {
        "prompt": clean_prompt,
        "resolution": "720p",
        "duration": min(10, max(5, int(duration_seconds))),
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            logger.info("🎨 Requesting Pixazo AI video for prompt: '%s'", prompt[:60])
            resp = await client.post(PIXAZO_TEXT_TO_VIDEO_URL, headers=headers, json=payload)
            
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                video_url = data.get("video_url") or data.get("url") or data.get("output_url")
                if video_url:
                    # Download the video
                    v_resp = await client.get(video_url)
                    if v_resp.status_code == 200:
                        out = output_path or tempfile.mktemp(suffix=".mp4")
                        with open(out, "wb") as f:
                            f.write(v_resp.content)
                        logger.info("✅ Pixazo video generated successfully: %s", out)
                        return out
                logger.warning("Pixazo response did not contain video URL: %s", data)
            elif resp.status_code == 402:
                logger.warning("Pixazo Insufficient Balance (HTTP 402). Falling back to local visual engine.")
            else:
                logger.warning("Pixazo API returned HTTP %d: %s", resp.status_code, resp.text[:120])
    except Exception as e:
        logger.warning("Pixazo generation exception: %s. Using local visual fallback.", e)

    return None
