"""
EduGenAI - Video Generation Service

Pipeline:
    Groq scenes -> gTTS audio -> Pollinations AI video -> FFmpeg -> final MP4

The AI video service is called through:
    services.ai_video.fetch_scene_video()

If Pollinations fails, this file keeps the existing local animated
presentation as a fallback.

Important:
- Pollinations/Wan-style clips may be shorter than narration.
- The AI clip is looped so it covers the narration duration.
- AI scenes are generated sequentially to reduce API/rate-limit problems.
"""

import logging
import uuid
import math
import re
import asyncio
import subprocess
import tempfile
import os
import shutil
import time
from pathlib import Path
from typing import Optional

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from config import VIDEO_DIR, BASE_DIR
from services.visual_animation import render_educational_scene
from services.topic_classifier import classify_topic, get_scene_motion

logger = logging.getLogger(__name__)

WIDTH = 854
HEIGHT = 480
FPS = 6
ASSETS = BASE_DIR / "assets"

PALETTES = {
    "neutral":   {"bg": (18, 24, 45),  "acc": (100, 180, 255), "title": (220, 240, 255)},
    "excited":   {"bg": (30, 10, 50),  "acc": (255, 120, 200), "title": (255, 200, 240)},
    "curious":   {"bg": (10, 35, 40),  "acc": (80, 220, 180), "title": (200, 255, 240)},
    "serious":   {"bg": (20, 20, 20),  "acc": (200, 200, 100), "title": (255, 255, 200)},
    "calm":      {"bg": (15, 30, 50),  "acc": (80, 160, 220), "title": (200, 230, 255)},
    "surprised": {"bg": (40, 20, 10),  "acc": (255, 160, 60),  "title": (255, 230, 200)},
}


def _palette(emotion):
    return PALETTES.get(emotion, PALETTES["neutral"])


_LANG_FONT_MAP: dict[str, str] = {
    # ── Indian Languages ──────────────────────────────────────────
    "kn":      "NotoSansKannada-Regular.ttf",
    "kannada": "NotoSansKannada-Regular.ttf",
    "hi":      "NotoSansDevanagari-Regular.ttf",
    "mr":      "NotoSansDevanagari-Regular.ttf",
    "ta":      "NotoSansTamil-Regular.ttf",
    "te":      "NotoSansTelugu-Regular.ttf",
    "ml":      "NotoSansMalayalam-Regular.ttf",
    "bn":      "NotoSansBengali-Regular.ttf",
    "as":      "NotoSansBengali-Regular.ttf",   # Assamese shares Bengali script
    "gu":      "NotoSansGujarati-Regular.ttf",
    "ur":      "NotoSansArabic-Regular.ttf",    # Urdu uses Arabic script
    # ── Global / Foreign Languages ────────────────────────────────
    "ar":      "NotoSansArabic-Regular.ttf",
    "ja":      "NotoSansJP-Regular.ttf",
    "zh-cn":   "NotoSansJP-Regular.ttf",
    "zh":      "NotoSansJP-Regular.ttf",
    "ko":      "NotoSansJP-Regular.ttf",
    # Latin-script languages fall back to NotoSans
    "en":      "NotoSans-Regular.ttf",
    "es":      "NotoSans-Regular.ttf",
    "fr":      "NotoSans-Regular.ttf",
    "de":      "NotoSans-Regular.ttf",
    "it":      "NotoSans-Regular.ttf",
    "pt":      "NotoSans-Regular.ttf",
    "ru":      "NotoSans-Regular.ttf",
}

_RTL_LANGS = {"ar", "he", "fa", "ur"}

_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}


def _get_pil_font(size: int, lang_code: str = "en") -> ImageFont.FreeTypeFont:
    key = (size, lang_code.lower())

    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    candidates: list[str] = []

    script_font = _LANG_FONT_MAP.get(lang_code.lower(), "")
    if script_font:
        candidates.append(str(ASSETS / script_font))

    candidates += [
        str(ASSETS / "NotoSans-Regular.ttf"),
        "arial.ttf",
        "segoeui.ttf",
        "tahoma.ttf",
    ]

    for candidate in candidates:
        try:
            font = ImageFont.truetype(candidate, size)
            _FONT_CACHE[key] = font
            return font
        except Exception:
            pass

    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _is_rtl(lang_code: str) -> bool:
    return lang_code.lower() in _RTL_LANGS


def _draw_text(draw, xy, text, fill, font, rtl=False, max_width=860):
    if rtl:
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            x = xy[0] + max_width - text_w
            draw.text((x, xy[1]), text, fill=fill, font=font)
        except Exception:
            draw.text(xy, text, fill=fill, font=font)
    else:
        draw.text(xy, text, fill=fill, font=font)


def _wrap_words(text: str, font, max_width: int) -> list[str]:
    words = str(text or "").split()
    lines = []
    cur = ""

    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    for word in words:
        test = f"{cur} {word}".strip()

        try:
            width = dummy.textbbox((0, 0), test, font=font)[2]
        except Exception:
            width = len(test) * 14

        if width > max_width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = test

    if cur:
        lines.append(cur)

    return lines


def overlay_image_alpha(
    img: np.ndarray,
    overlay: np.ndarray,
    x: int,
    y: int,
) -> np.ndarray:

    if overlay is None:
        return img

    y1 = max(0, y)
    y2 = min(img.shape[0], y + overlay.shape[0])
    x1 = max(0, x)
    x2 = min(img.shape[1], x + overlay.shape[1])

    y1o = max(0, -y)
    y2o = min(overlay.shape[0], img.shape[0] - y)
    x1o = max(0, -x)
    x2o = min(overlay.shape[1], img.shape[1] - x)

    if y1 >= y2 or x1 >= x2 or y1o >= y2o or x1o >= x2o:
        return img

    crop = img[y1:y2, x1:x2]
    over = overlay[y1o:y2o, x1o:x2o]

    if over.ndim == 3 and over.shape[2] == 4:
        alpha = over[:, :, 3:4] / 255.0
        img[y1:y2, x1:x2] = (
            over[:, :, :3] * alpha +
            crop * (1 - alpha)
        ).astype(np.uint8)
    else:
        img[y1:y2, x1:x2] = over

    return img


def _load_asset(filename: str) -> Optional[np.ndarray]:
    path = ASSETS / filename

    if path.exists():
        return cv2.imread(str(path), cv2.IMREAD_UNCHANGED)

    return None


def _render_static_frame(
    title: str,
    narration_lines: list[str],
    clean_kws: list[str],
    emotion: str,
    scene_num: int,
    total_scenes: int,
    lang_code: str = "en",
) -> tuple[np.ndarray, list[int]]:

    pal = _palette(emotion)

    bg_rgb = pal["bg"]
    acc_rgb = pal["acc"]
    title_col = pal["title"]

    rtl = _is_rtl(lang_code)

    body_max_w = WIDTH - 420
    sub_max_w = WIDTH - 400

    pil = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        bg_rgb,
    )

    draw = ImageDraw.Draw(
        pil,
        "RGBA",
    )

    for row in range(0, HEIGHT, 3):
        alpha = int(
            15 + 10 * math.sin(row * 0.015)
        )

        draw.rectangle(
            [(0, row), (WIDTH, row + 2)],
            fill=(*bg_rgb, alpha),
        )

    draw.rectangle(
        [(0, 0), (6, HEIGHT)],
        fill=(*acc_rgb, 255),
    )

    badge_font = _get_pil_font(20)

    draw.ellipse(
        [(16, 16), (52, 52)],
        fill=(*acc_rgb, 200),
    )

    draw.text(
        (28, 22),
        str(scene_num),
        fill=(10, 10, 30),
        font=badge_font,
    )

    dot_x = WIDTH - 20 - (total_scenes * 18)

    for s in range(total_scenes):

        col = (
            (*acc_rgb, 255)
            if s == scene_num - 1
            else (60, 60, 60, 255)
        )

        draw.ellipse(
            [
                (dot_x + s * 18, 18),
                (dot_x + s * 18 + 12, 30),
            ],
            fill=col,
        )

    font_title = _get_pil_font(
        52,
        lang_code,
    )

    font_body = _get_pil_font(
        30,
        lang_code,
    )

    font_kw = _get_pil_font(
        28,
        lang_code,
    )

    font_sub = _get_pil_font(
        24,
        lang_code,
    )

    _draw_text(
        draw,
        (68, 28),
        title,
        fill=(*title_col, 255),
        font=font_title,
        rtl=rtl,
        max_width=body_max_w,
    )

    draw.rectangle(
        [(20, 93), (WIDTH - 400, 97)],
        fill=(*acc_rgb, 210),
    )

    y_text = 118

    for line in narration_lines:

        if line.strip():

            _draw_text(
                draw,
                (28, y_text),
                line,
                fill=(210, 225, 245, 255),
                font=font_body,
                rtl=rtl,
                max_width=body_max_w,
            )

        y_text += 42

    kw_box_y = max(
        y_text + 16,
        340,
    )

    kw_y_positions = []

    glow = tuple(
        min(255, int(c * 0.4))
        for c in acc_rgb
    )

    for kw in clean_kws[:6]:

        kw_text = f"  {kw}  "

        bbox = draw.textbbox(
            (28, kw_box_y),
            kw_text,
            font=font_kw,
        )

        draw.rounded_rectangle(
            [
                (bbox[0] - 4, bbox[1] - 3),
                (bbox[2] + 4, bbox[3] + 3),
            ],
            radius=6,
            fill=(*glow, 220),
        )

        _draw_text(
            draw,
            (28, kw_box_y),
            kw_text,
            fill=(*acc_rgb, 255),
            font=font_kw,
            rtl=rtl,
            max_width=body_max_w,
        )

        kw_y_positions.append(
            kw_box_y + 14
        )

        kw_box_y += 50

    narration_flat = " ".join(
        narration_lines
    )

    sub_lines = _wrap_words(
        narration_flat,
        font_sub,
        sub_max_w,
    )

    draw.rectangle(
        [(0, HEIGHT - 90), (WIDTH - 360, HEIGHT)],
        fill=(0, 0, 0, 180),
    )

    for i, sl in enumerate(sub_lines[:2]):

        _draw_text(
            draw,
            (
                20,
                HEIGHT - 82 + i * 36,
            ),
            sl,
            fill=(255, 255, 255, 230),
            font=font_sub,
            rtl=rtl,
            max_width=sub_max_w,
        )

    bgr = cv2.cvtColor(
        np.array(pil),
        cv2.COLOR_RGB2BGR,
    )

    return bgr, kw_y_positions


def _write_scene_video(
    scene_idx: int,
    static_bgr: np.ndarray,
    kw_y_positions: list[int],
    duration: float,
    teacher_img: Optional[np.ndarray],
    mouth_open: Optional[np.ndarray],
    mouth_closed: Optional[np.ndarray],
    pointer_img: Optional[np.ndarray],
    tmp_dir: str,
) -> str:

    avi_path = os.path.join(
        tmp_dir,
        f"scene_{scene_idx:03d}.avi",
    )

    fourcc = cv2.VideoWriter_fourcc(
        *"MJPG"
    )

    writer = cv2.VideoWriter(
        avi_path,
        fourcc,
        FPS,
        (WIDTH, HEIGHT),
    )

    if not writer.isOpened():
        raise RuntimeError(
            f"Could not create video writer: {avi_path}"
        )

    n_frames = max(
        1,
        int(duration * FPS),
    )

    teacher_base = None

    if teacher_img is not None:

        th, tw = teacher_img.shape[:2]

        tx = WIDTH - tw - 10
        ty = HEIGHT - th - 80

        base_with_teacher = static_bgr.copy()

        overlay_image_alpha(
            base_with_teacher,
            teacher_img,
            tx,
            ty,
        )

        teacher_base = base_with_teacher

        teacher_info = (
            tx,
            ty,
            tw,
            th,
        )

    else:

        teacher_base = static_bgr
        teacher_info = None

    for fi in range(n_frames):

        t = fi / FPS

        frame = teacher_base.copy()

        prog_w = int(
            min(
                1.0,
                t / max(duration, 0.01),
            ) * WIDTH
        )

        cv2.rectangle(
            frame,
            (0, HEIGHT - 6),
            (WIDTH, HEIGHT),
            (30, 30, 30),
            -1,
        )

        cv2.rectangle(
            frame,
            (0, HEIGHT - 6),
            (prog_w, HEIGHT),
            (100, 180, 255),
            -1,
        )

        if prog_w > 8:

            cv2.circle(
                frame,
                (prog_w, HEIGHT - 3),
                5,
                (150, 220, 255),
                -1,
            )

        if teacher_info is not None:

            tx, ty, tw, th = teacher_info

            m_img = (
                mouth_open
                if int(t) % 2 == 0
                else mouth_closed
            )

            if m_img is not None:

                mh, mw = m_img.shape[:2]

                overlay_image_alpha(
                    frame,
                    m_img,
                    tx + tw // 2 - mw // 2,
                    ty + th // 2 + 10,
                )

        if pointer_img is not None and kw_y_positions:

            ki = min(
                int(
                    (
                        t /
                        max(duration, 0.01)
                    ) *
                    len(kw_y_positions)
                ),
                len(kw_y_positions) - 1,
            )

            hover_x = int(
                math.sin(t * 4) * 7
            )

            overlay_image_alpha(
                frame,
                pointer_img,
                6 + hover_x,
                kw_y_positions[ki] - 16,
            )

        writer.write(frame)

    writer.release()

    return avi_path


def _mux_scene(
    avi_path: str,
    audio_path: Optional[str],
    out_mp4: str,
) -> str:

    if audio_path and os.path.exists(audio_path):

        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",

            "-i",
            avi_path,

            "-i",
            audio_path,

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-crf",
            "28",

            "-c:a",
            "aac",

            "-b:a",
            "96k",

            "-shortest",

            "-movflags",
            "+faststart",

            out_mp4,
        ]

    else:

        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",

            "-i",
            avi_path,

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-crf",
            "28",

            "-an",

            "-movflags",
            "+faststart",

            out_mp4,
        ]

    subprocess.run(
        cmd,
        check=True,
        timeout=120,
    )

    return out_mp4


def _concat_mp4s(
    mp4_list: list[str],
    output_path: str,
) -> None:

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as flist:

        for p in mp4_list:

            safe_path = (
                os.path.abspath(p)
                .replace("\\", "/")
                .replace("'", "'\\''")
            )

            flist.write(
                f"file '{safe_path}'\n"
            )

        flist_path = flist.name

    try:

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",

                "-f",
                "concat",

                "-safe",
                "0",

                "-i",
                flist_path,

                "-c",
                "copy",

                output_path,
            ],
            check=True,
            timeout=180,
        )

    finally:

        if os.path.exists(flist_path):
            os.unlink(flist_path)


def _mux_ai_video(
    ai_video_path: str,
    audio_path: Optional[str],
    output_path: str,
    duration: float,
) -> str:
    """
    Combine an AI video clip with scene narration.

    The AI clip is looped because video models may return a shorter
    clip than the narration.
    """

    if not os.path.exists(ai_video_path):
        raise FileNotFoundError(
            f"AI video does not exist: {ai_video_path}"
        )

    duration = max(
        0.5,
        float(duration),
    )

    temp_path = output_path + ".mux.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",

        # Loop AI video until narration is complete.
        "-stream_loop",
        "-1",

        "-i",
        ai_video_path,
    ]

    if audio_path and os.path.exists(audio_path):

        cmd += [
            "-i",
            audio_path,

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-c:a",
            "aac",

            "-b:a",
            "128k",
        ]

    else:

        cmd += [
            "-f",
            "lavfi",

            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",

            "-map",
            "0:v:0",

            "-map",
            "1:a:0",

            "-c:a",
            "aac",

            "-b:a",
            "128k",
        ]

    cmd += [
        "-vf",
        (
            f"scale={WIDTH}:{HEIGHT}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2"
        ),

        "-r",
        str(FPS),

        "-c:v",
        "libx264",

        "-preset",
        "veryfast",

        "-crf",
        "23",

        "-pix_fmt",
        "yuv420p",

        "-t",
        str(duration),

        "-shortest",

        "-movflags",
        "+faststart",

        temp_path,
    ]

    subprocess.run(
        cmd,
        check=True,
        timeout=max(
            120,
            int(duration * 10),
        ),
    )

    os.replace(
        temp_path,
        output_path,
    )

    return output_path



def _create_fallback_image(scene: dict, topic: str) -> str:
    """Create a high-quality visual slide when external image fetch is unavailable."""
    from config import IMAGE_DIR
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    fallback_path = IMAGE_DIR / f"fallback_{uuid.uuid4().hex[:8]}.png"

    emotion = scene.get("emotion", "neutral")
    pal = _palette(emotion)
    bg_color = pal["bg"]
    acc_color = pal["acc"]
    title_color = pal["title"]

    img = Image.new("RGB", (WIDTH, HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    for y in range(0, HEIGHT, 40):
        draw.line([(0, y), (WIDTH, y)], fill=(min(255, bg_color[0]+12), min(255, bg_color[1]+12), min(255, bg_color[2]+18)), width=1)
    for x in range(0, WIDTH, 40):
        draw.line([(x, 0), (x, HEIGHT)], fill=(min(255, bg_color[0]+12), min(255, bg_color[1]+12), min(255, bg_color[2]+18)), width=1)

    draw.rectangle([50, 50, WIDTH - 50, HEIGHT - 50], outline=acc_color, width=3)

    title = scene.get("title", topic)
    try:
        font_large = ImageFont.truetype("arial.ttf", 42)
        font_sub = ImageFont.truetype("arial.ttf", 26)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((90, 90), f"Topic: {topic}", fill=acc_color, font=font_sub)
    draw.text((90, 140), title[:60], fill=title_color, font=font_large)

    narration = scene.get("narration", "")
    if narration:
        words = narration.split()
        lines = [" ".join(words[i:i+10]) for i in range(0, min(len(words), 30), 10)]
        curr_y = 240
        for line in lines:
            draw.text((90, curr_y), line, fill=(230, 230, 240), font=font_sub)
            curr_y += 36

    img.save(fallback_path)
    return str(fallback_path)


async def _get_scene_image(scene: dict, topic: str) -> Optional[str]:
    """Fetch an authentic Wikipedia / Wikimedia / Pexels image for the scene."""
    from services.image_fetcher import fetch_background_image

    queries = []

    # 1. Collect English keywords from scene image_keywords (always in English per LLM prompt)
    raw_kws = scene.get("image_keywords", [])
    if isinstance(raw_kws, list):
        for kw in raw_kws:
            kw_s = re.sub(r"[^a-zA-Z0-9\s\-]", " ", str(kw)).strip()
            if len(kw_s) >= 3 and not kw_s.lower().startswith("error"):
                queries.append(kw_s)

    # 2. Extract keywords from visual_description (which is always in English)
    vis_desc = str(scene.get("visual_description") or "").strip()
    vis_clean = re.sub(r"[^a-zA-Z0-9\s\-]", " ", vis_desc).strip()
    if vis_clean and len(vis_clean) >= 3 and not vis_clean.lower().startswith("error"):
        words = [w for w in vis_clean.split() if len(w) > 3 and w.lower() not in ("wide", "shot", "establishing", "scene", "view", "camera")]
        if words:
            queries.append(" ".join(words[:4]))

    # 3. Clean topic
    topic_clean = re.sub(r"[^a-zA-Z0-9\s\-]", " ", str(topic or "")).strip()
    if len(topic_clean) >= 3 and not topic_clean.lower().startswith("error"):
        queries.append(topic_clean)

    # De-duplicate while preserving order
    clean_queries = []
    for q in queries:
        q_norm = " ".join(q.split())
        if q_norm and q_norm not in clean_queries and len(q_norm) >= 3:
            clean_queries.append(q_norm)

    if not clean_queries:
        clean_queries = ["historical fort architecture"]

    try:
        for q in clean_queries[:3]:
            path = await fetch_background_image(q)
            if path and os.path.exists(str(path)):
                logger.info("✅ Scene image resolved: %s -> %s", q, path)
                return str(path)
    except Exception as exc:
        logger.warning("Image fetch skipped (%s): %s", type(exc).__name__, exc)

    return None


def _scene_type(scene: dict) -> str:
    """Choose image/Manim using the LLM's scene_visual_type first."""
    explicit = str(scene.get("scene_visual_type", "")).lower().strip()

    if explicit in {"image", "manim", "image+manim"}:
        return explicit

    if scene.get("equation"):
        return "manim"

    actions = scene.get("actions", [])
    if isinstance(actions, list) and actions:
        return "manim"

    return "image"


def _motion_for_scene(scene: dict, topic: str = "") -> str:
    """Map the storyboard to the strong visual_animation modes using topic context."""
    text = " ".join(
        str(scene.get(k, ""))
        for k in (
            "title",
            "original_title",
            "narration",
            "original_narration",
            "visual_description",
            "visual_prompt",
        )
    ).lower()

    combined = f"{topic.lower()} {text}"

    # Photosynthesis & Botany (Always render full biological animation)
    if any(x in combined for x in (
        "photosynthesis", "chloroplast", "chlorophyll", "leaf", "leaves", "plant", "botany"
    )):
        return "photosynthesis"

    # Astronomy & Space
    if any(x in combined for x in (
        "space", "planet", "orbit", "solar system", "galaxy", "universe", "gravity", "star", "moon", "earth", "asteroid", "telescope"
    )):
        return "space"

    # Biology, DNA & Genetics
    if any(x in combined for x in (
        "dna", "gene", "genetics", "helix", "chromosome", "rna", "mutation", "cell division", "mitosis", "organism"
    )):
        return "dna"

    # History, Biographies, Geography, Maps & Social Studies
    if any(x in combined for x in (
        "history", "king", "ruler", "empire", "maharaj", "shivaji", "biography", "leader",
        "war", "battle", "fort", "treaty", "india", "map", "geography", "state", "culture",
        "heritage", "monument", "century", "dynasty", "swarajya", "reign", "ancient", "medieval",
        "tipu", "sultan", "world war"
    )):
        return "documentary"

    return "photosynthesis" if any(k in topic.lower() for k in ("plant", "food", "eat", "nature")) else "documentary"


async def _render_manim_one(scene: dict, index: int) -> Optional[str]:
    """Fallback handler for process scenes."""
    return None


async def _render_sadtalker_one(
    scene: dict,
    index: int,
    total: int,
    tmp_dir: str,
) -> Optional[str]:
    """
    Use the existing SadTalker service if it exposes a compatible public
    function. The service itself is NOT modified.

    Avatar is generated for the first/last scene by default, or any scene
    with avatar=true. This keeps rendering time practical.
    """
    audio = scene.get("audio_path")
    if not audio or not os.path.exists(str(audio)):
        return None

    explicit = scene.get("avatar")
    if explicit is False:
        return None

    if explicit is not True and index not in {0, total - 1}:
        return None

    teacher = ASSETS / "teacher.png"
    if not teacher.exists():
        logger.warning("assets/teacher.png not found; SadTalker skipped")
        return None

    try:
        import inspect
        import services.sadtalker_service as st
    except Exception as exc:
        logger.warning("SadTalker service unavailable: %s", exc)
        return None

    candidates = (
        "generate_talking_avatar",
        "generate_sadtalker_video",
        "create_talking_avatar",
        "generate_avatar_video",
        "generate_talking_head",
        "generate_video",
        "run_sadtalker",
    )

    output = os.path.join(
        tmp_dir,
        f"sadtalker_{index:03d}.mp4",
    )

    for name in candidates:
        fn = getattr(st, name, None)
        if not callable(fn):
            continue

        try:
            sig = inspect.signature(fn)
            kwargs = {}

            for p in sig.parameters.values():
                n = p.name.lower()

                if n in {
                    "image_path", "source_image", "source_image_path",
                    "face_image", "avatar_image", "driven_image"
                }:
                    kwargs[p.name] = str(teacher)

                elif n in {
                    "audio_path", "driven_audio", "audio",
                    "wav_path", "speech_path"
                }:
                    kwargs[p.name] = str(audio)

                elif n in {
                    "output_path", "output_video", "output_name",
                    "video_path", "save_path", "out_name"
                }:
                    kwargs[p.name] = f"sadtalker_{index:03d}.mp4" if "name" in n else output

            required = [
                p for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty
                and p.kind in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
            ]

            if any(p.name not in kwargs for p in required):
                continue

            result = fn(**kwargs)
            if inspect.isawaitable(result):
                result = await result

            result = str(result) if result else output

            if os.path.exists(result):
                if os.path.abspath(result) != os.path.abspath(output):
                    shutil.copy2(result, output)
                return output

            if os.path.exists(output):
                return output

        except Exception as exc:
            logger.warning(
                "SadTalker callable %s failed: %s",
                name,
                exc,
            )

    logger.warning(
        "No compatible SadTalker function found; continuing without avatar."
    )
    return None


def _mux_scene_audio(
    video_path: str,
    audio_path: Optional[str],
    output_path: str,
    duration: float,
) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", video_path,
    ]

    if audio_path and os.path.exists(str(audio_path)):
        cmd += [
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
        ]
    else:
        cmd += ["-map", "0:v:0", "-an"]

    cmd += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-movflags", "+faststart",
        output_path,
    ]

    subprocess.run(
        cmd,
        check=True,
        timeout=max(180, int(duration * 12)),
    )


def _overlay_sadtalker(
    base: str,
    avatar: str,
    audio: Optional[str],
    output: str,
    duration: float,
) -> None:
    """Put the talking teacher in a small lower-right PiP."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", base,
        "-i", avatar,
    ]

    if audio and os.path.exists(str(audio)):
        cmd += [
            "-i", str(audio),
            "-filter_complex",
            (
                "[1:v]scale=300:-1,format=rgba,"
                "setpts=PTS-STARTPTS[a];"
                "[0:v]setpts=PTS-STARTPTS[b];"
                "[b][a]overlay=W-w-24:H-h-45:shortest=1[v]"
            ),
            "-map", "[v]",
            "-map", "2:a:0",
            "-c:a", "aac",
            "-b:a", "128k",
        ]
    else:
        cmd += [
            "-filter_complex",
            (
                "[1:v]scale=300:-1,format=rgba,"
                "setpts=PTS-STARTPTS[a];"
                "[0:v]setpts=PTS-STARTPTS[b];"
                "[b][a]overlay=W-w-24:H-h-45:shortest=1[v]"
            ),
            "-map", "[v]",
            "-an",
        ]

    cmd += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        "-movflags", "+faststart",
        output,
    ]

    subprocess.run(
        cmd,
        check=True,
        timeout=max(180, int(duration * 15)),
    )


def _write_scene_srt(scenes: list[dict], path: str) -> None:
    """Generate readable subtitles from the exact TTS narration."""
    def stamp(seconds: float) -> str:
        total_ms = int(max(0, seconds) * 1000)
        h, rem = divmod(total_ms, 3600000)
        m, rem = divmod(rem, 60000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    current = 0.0
    entry = 1

    with open(path, "w", encoding="utf-8") as f:
        for scene in scenes:
            text = str(scene.get("narration", "")).strip()
            if not text:
                continue

            duration = float(
                scene.get(
                    "audio_duration",
                    scene.get("duration_seconds", 8),
                )
            )
            # Minimum 10s per scene -> 6 scenes = 60s+ guaranteed
            duration = max(10.0, duration)

            words = text.split()
            chunks = [
                " ".join(words[i:i + 10])
                for i in range(0, len(words), 10)
            ] or [text]

            each = duration / len(chunks)

            for i, chunk in enumerate(chunks):
                start = current + i * each
                end = current + (i + 1) * each

                f.write(
                    f"{entry}\n"
                    f"{stamp(start)} --> {stamp(end)}\n"
                    f"{chunk}\n\n"
                )
                entry += 1

            current += duration


def _burn_final_subtitles(
    video_path: str,
    srt_path: str,
    output_path: str,
) -> None:
    safe = (
        os.path.abspath(srt_path)
        .replace("\\", "/")
        .replace(":", r"\:")
        .replace("'", r"\'")
    )

    vf = (
        f"subtitles='{safe}':force_style="
        "'FontName=Arial,FontSize=20,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H90000000,"
        "BorderStyle=3,Outline=1,Shadow=0,MarginV=46'"
    )

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", video_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-movflags", "+faststart",
            output_path,
        ],
        check=True,
        timeout=900,
    )


def _concat_hybrid_scene_files(
    paths: list[str],
    output: str,
) -> None:
    if not paths:
        raise RuntimeError("No video scenes were generated.")

    if len(paths) == 1:
        shutil.copy2(paths[0], output)
        return

    list_file = output + ".txt"

    try:
        with open(list_file, "w", encoding="utf-8") as f:
            for p in paths:
                safe = (
                    os.path.abspath(p)
                    .replace("\\", "/")
                    .replace("'", "'\\''")
                )
                f.write(f"file '{safe}'\n")

        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                "-movflags", "+faststart",
                output,
            ],
            check=True,
            timeout=900,
        )
    finally:
        try:
            os.remove(list_file)
        except OSError:
            pass


async def generate_video(
    scenes: dict,
    output_filename: str = None,
    lang_code: str = "en",
) -> dict:
    """
    FINAL HYBRID PIPELINE

    Scene routing:
      image         -> Pexels + visual_animation
      manim         -> existing Manim renderer
      image+manim   -> Manim first, image fallback if unavailable

    SadTalker:
      first + final scene by default; scene.avatar=true can enable it
      for any additional scene.

    TTS:
      uses the audio_path already created by the existing TTS service.

    Subtitles:
      generated from the same narration and audio_duration values.
    """

    started = time.time()

    scene_list = scenes.get("scenes", [])
    if not scene_list:
        raise RuntimeError("No scenes were generated.")

    if not output_filename:
        output_filename = (
            f"edugen_{uuid.uuid4().hex[:8]}.mp4"
        )

    VIDEO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = VIDEO_DIR / output_filename
    topic = str(
        scenes.get(
            "original_title",
            scenes.get(
                "title",
                scenes.get("subject", "education"),
            ),
        )
    )

    # ── Classify the topic once, then apply the same strategy to ALL scenes ──
    topic_info = classify_topic(topic)
    topic_category = topic_info["category"]
    topic_motion = topic_info["motion"]
    topic_equation = topic_info.get("equation")
    logger.info(
        "🎓 Topic '%s' classified as %s → %s",
        topic, topic_category, topic_info["animation_style"]
    )

    tmp_dir = tempfile.mkdtemp(
        prefix="edugen_hybrid_"
    )

    scene_paths = []
    image_count = 0
    manim_count = 0
    avatar_count = 0

    try:
        total = len(scene_list)

        async def _render_one_scene(idx: int, scene: dict) -> str:
            duration = float(
                scene.get(
                    "audio_duration",
                    scene.get("duration_seconds", 8),
                )
            )
            # Minimum 10s per scene -> 6 scenes = 60s+ guaranteed
            duration = max(10.0, duration)

            visual_type = _scene_type(scene)

            raw = os.path.join(
                tmp_dir,
                f"raw_{idx:03d}.mp4",
            )
            with_audio = os.path.join(
                tmp_dir,
                f"audio_{idx:03d}.mp4",
            )
            final_scene = os.path.join(
                tmp_dir,
                f"scene_{idx:03d}.mp4",
            )

            logger.info(
                "🎬 Scene %d/%d | %s | %.1fs (Parallel)",
                idx + 1,
                total,
                visual_type,
                duration,
            )

            # 1. Manim when the storyboard explicitly requests it.
            manim_path = None
            if visual_type in {
                "manim",
                "image+manim",
            }:
                manim_path = await _render_manim_one(
                    scene,
                    idx,
                )

            if manim_path:
                shutil.copy2(
                    manim_path,
                    raw,
                )
            else:
                # 2. Render based on topic category
                motion = get_scene_motion(scene, topic_category, topic_motion, scene_idx=idx, total_scenes=total)

                # ANIMATED topics → pure animation, no unrelated background photo
                # DOCUMENTARY topics → authentic photo + documentary slide
                if topic_category == "DOCUMENTARY":
                    image_path = await _get_scene_image(scene, topic)
                else:
                    image_path = None

                eq = scene.get("equation") or (topic_equation if motion in ("photo_equation", "equation") else None)
                lang = str(scenes.get("language", scenes.get("lang_code", scenes.get("lang", "en"))))

                # Render scene in thread pool for multi-core parallel rendering
                await asyncio.to_thread(
                    render_educational_scene,
                    image_path=image_path,
                    output_path=raw,
                    duration=duration,
                    motion=motion,
                    zoom_start=1.0,
                    zoom_end=1.07,
                    equation=eq,
                    title=scene.get("title"),
                    narration=scene.get("narration"),
                    lang_code=lang,
                )

            # 3. TTS audio muxing in parallel
            audio_path = scene.get("audio_path")
            await asyncio.to_thread(
                _mux_scene_audio,
                raw,
                str(audio_path) if audio_path else None,
                with_audio,
                duration,
            )

            # 4. SadTalker teacher for selected teaching moments
            avatar_path = await _render_sadtalker_one(
                scene,
                idx,
                total,
                tmp_dir,
            )

            if avatar_path:
                try:
                    await asyncio.to_thread(
                        _overlay_sadtalker,
                        with_audio,
                        avatar_path,
                        str(audio_path)
                        if audio_path
                        and os.path.exists(str(audio_path))
                        else None,
                        final_scene,
                        duration,
                    )
                except Exception as exc:
                    logger.exception(
                        "SadTalker overlay failed for scene %d: %s",
                        idx + 1,
                        exc,
                    )
                    shutil.copy2(
                        with_audio,
                        final_scene,
                    )
            else:
                shutil.copy2(
                    with_audio,
                    final_scene,
                )

            return final_scene

        # Render all scenes simultaneously in parallel across CPU cores!
        scene_paths = await asyncio.gather(
            *[_render_one_scene(idx, s) for idx, s in enumerate(scene_list)]
        )

        # 5. Join scenes in the exact storyboard order.
        _concat_hybrid_scene_files(
            scene_paths,
            str(output_path),
        )

        # 6. Burn subtitles generated from the same narration/audio timing.
        srt_path = os.path.join(
            tmp_dir,
            "master.srt",
        )

        _write_scene_srt(
            scene_list,
            srt_path,
        )

        subtitled = (
            str(output_path)
            + ".subtitled.mp4"
        )

        subtitles_ok = False

        try:
            _burn_final_subtitles(
                str(output_path),
                srt_path,
                subtitled,
            )

            os.replace(
                subtitled,
                str(output_path),
            )
            subtitles_ok = True

        except Exception as exc:
            logger.exception(
                "Subtitle burn-in failed: %s",
                exc,
            )

        total_duration = sum(
            float(
                s.get(
                    "audio_duration",
                    s.get("duration_seconds", 8),
                )
            )
            for s in scene_list
        )

        elapsed = time.time() - started

        logger.info(
            "🎬 HYBRID VIDEO READY | %.1fs content | "
            "%d scenes | image=%d | manim=%d | "
            "sadtalker=%d | subtitles=%s",
            total_duration,
            total,
            image_count,
            manim_count,
            avatar_count,
            subtitles_ok,
        )

        return {
            "video_path": str(output_path),
            "filename": output_filename,
            "duration": round(total_duration, 1),
            "render_time_s": round(elapsed, 1),
            "resolution": f"{WIDTH}x{HEIGHT}",
            "fps": FPS,
            "total_scenes": total,
            "renderer": "hybrid_visual_manim_sadtalker",
            "image_scenes": image_count,
            "manim_scenes": manim_count,
            "sadtalker_scenes": avatar_count,
            "subtitles": subtitles_ok,
        }

    finally:
        shutil.rmtree(
            tmp_dir,
            ignore_errors=True,
        )


async def create_video(
    scenes: dict,
    output_filename: str = None,
    lang_code: str = "en",
) -> dict:
    return await generate_video(
        scenes,
        output_filename,
        lang_code,
    )
