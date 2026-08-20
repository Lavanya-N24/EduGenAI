"""
EduGenAI - Video Generation Service (ULTRA-FAST)
Target: full video ready in < 10 seconds.

Strategy:
  - cv2.VideoWriter instead of MoviePy callbacks — 10-50x faster frame writing
  - librosa REMOVED — replaced with clock-based mouth toggle (no MP3 decode needed)
  - Scene frames rendered in parallel via ThreadPoolExecutor
  - Each scene muxed with ffmpeg directly (fastest possible, no Python overhead)
  - Final video: concatenated scenes with ffmpeg concat demuxer
  - FPS: 8 — imperceptible vs 12 for static slide content, saves 33% encode time
"""
import logging
import uuid
import math
import subprocess
import tempfile
import os
import concurrent.futures
import time
from pathlib import Path
from typing import Optional

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from config import VIDEO_DIR, BASE_DIR

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────
WIDTH  = 1280
HEIGHT = 720
FPS    = 8           # 8fps: perfect for slides, fastest encode
ASSETS = BASE_DIR / "assets"

# ── Emotion → Color palette ───────────────────────────────────
PALETTES = {
    "neutral":   {"bg": (18, 24, 45),  "acc": (100, 180, 255), "title": (220, 240, 255)},
    "excited":   {"bg": (30, 10, 50),  "acc": (255, 120, 200), "title": (255, 200, 240)},
    "curious":   {"bg": (10, 35, 40),  "acc": ( 80, 220, 180), "title": (200, 255, 240)},
    "serious":   {"bg": (20, 20, 20),  "acc": (200, 200, 100), "title": (255, 255, 200)},
    "calm":      {"bg": (15, 30, 50),  "acc": ( 80, 160, 220), "title": (200, 230, 255)},
    "surprised": {"bg": (40, 20, 10),  "acc": (255, 160,  60), "title": (255, 230, 200)},
}

def _palette(emotion): return PALETTES.get(emotion, PALETTES["neutral"])

# ── Per-language font map ─────────────────────────────────────
_LANG_FONT_MAP: dict[str, str] = {
    "kn": "NotoSansKannada-Regular.ttf",
    "kannada": "NotoSansKannada-Regular.ttf",
    "hi": "NotoSansDevanagari-Regular.ttf",
    "mr": "NotoSansDevanagari-Regular.ttf",
    "ta": "NotoSansTamil-Regular.ttf",
    "te": "NotoSansTelugu-Regular.ttf",
    "ml": "NotoSansMalayalam-Regular.ttf",
    "bn": "NotoSansBengali-Regular.ttf",
    "gu": "NotoSansGujarati-Regular.ttf",
    "ar": "NotoSansArabic-Regular.ttf",
    "ja": "NotoSansJP-Regular.ttf",
    "zh-cn": "NotoSansJP-Regular.ttf",
    "ko": "NotoSansJP-Regular.ttf",
}

_RTL_LANGS = {"ar", "he", "fa", "ur"}

# ── Font cache — load each font ONCE, reuse across all scenes ──
_FONT_CACHE: dict[tuple, ImageFont.FreeTypeFont] = {}

def _get_pil_font(size: int, lang_code: str = "en") -> ImageFont.FreeTypeFont:
    key = (size, lang_code.lower())
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates: list[str] = []
    script_font = _LANG_FONT_MAP.get(lang_code.lower(), "")
    if script_font:
        candidates.append(str(ASSETS / script_font))
    candidates += [str(ASSETS / "NotoSans-Regular.ttf"), "arial.ttf", "segoeui.ttf", "tahoma.ttf"]
    for c in candidates:
        try:
            fnt = ImageFont.truetype(c, size)
            _FONT_CACHE[key] = fnt
            return fnt
        except Exception:
            pass
    fnt = ImageFont.load_default()
    _FONT_CACHE[key] = fnt
    return fnt

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
    words = text.split()
    lines, cur = [], ""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for word in words:
        test = f"{cur} {word}".strip()
        try:
            w = dummy.textbbox((0, 0), test, font=font)[2]
        except Exception:
            w = len(test) * 14
        if w > max_width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines

def overlay_image_alpha(img: np.ndarray, overlay: np.ndarray, x: int, y: int) -> np.ndarray:
    if overlay is None:
        return img
    y1, y2 = max(0, y), min(img.shape[0], y + overlay.shape[0])
    x1, x2 = max(0, x), min(img.shape[1], x + overlay.shape[1])
    y1o = max(0, -y); y2o = min(overlay.shape[0], img.shape[0] - y)
    x1o = max(0, -x); x2o = min(overlay.shape[1], img.shape[1] - x)
    if y1 >= y2 or x1 >= x2 or y1o >= y2o or x1o >= x2o:
        return img
    crop = img[y1:y2, x1:x2]
    over = overlay[y1o:y2o, x1o:x2o]
    if over.shape[2] == 4:
        alpha = over[:, :, 3:4] / 255.0
        img[y1:y2, x1:x2] = (over[:, :, :3] * alpha + crop * (1 - alpha)).astype(np.uint8)
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
    """
    Render background + text ONCE per scene. Returns BGR numpy array.
    Called in a thread (not blocking the event loop).
    """
    pal       = _palette(emotion)
    bg_rgb    = pal["bg"]
    acc_rgb   = pal["acc"]
    title_col = pal["title"]
    rtl       = _is_rtl(lang_code)
    body_max_w = WIDTH - 420
    sub_max_w  = WIDTH - 400

    pil  = Image.new("RGB", (WIDTH, HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(pil, "RGBA")

    # Gradient overlay — fast: 240 rectangles not 720
    for row in range(0, HEIGHT, 3):
        alpha = int(15 + 10 * math.sin(row * 0.015))
        draw.rectangle([(0, row), (WIDTH, row + 2)], fill=(*bg_rgb, alpha))

    draw.rectangle([(0, 0), (6, HEIGHT)], fill=(*acc_rgb, 255))  # left bar

    # Scene badge
    badge_font = _get_pil_font(20)
    draw.ellipse([(16, 16), (52, 52)], fill=(*acc_rgb, 200))
    draw.text((28, 22), str(scene_num), fill=(10, 10, 30), font=badge_font)

    # Scene dots
    dot_x = WIDTH - 20 - (total_scenes * 18)
    for s in range(total_scenes):
        col = (*acc_rgb, 255) if s == scene_num - 1 else (60, 60, 60, 255)
        draw.ellipse([(dot_x + s * 18, 18), (dot_x + s * 18 + 12, 30)], fill=col)

    font_title = _get_pil_font(52, lang_code)
    font_body  = _get_pil_font(30, lang_code)
    font_kw    = _get_pil_font(28, lang_code)
    font_sub   = _get_pil_font(24, lang_code)

    # Title
    _draw_text(draw, (68, 28), title, fill=(*title_col, 255), font=font_title, rtl=rtl, max_width=body_max_w)
    draw.rectangle([(20, 93), (WIDTH - 400, 97)], fill=(*acc_rgb, 210))

    # Narration body
    y_text = 118
    for line in narration_lines:
        if line.strip():
            _draw_text(draw, (28, y_text), line, fill=(210, 225, 245, 255), font=font_body, rtl=rtl, max_width=body_max_w)
        y_text += 42

    # Keywords
    kw_box_y = max(y_text + 16, 340)
    kw_y_positions = []
    glow = tuple(min(255, int(c * 0.4)) for c in acc_rgb)
    for kw in clean_kws[:6]:
        kw_text = f"  {kw}  "
        bbox = draw.textbbox((28, kw_box_y), kw_text, font=font_kw)
        draw.rounded_rectangle([(bbox[0]-4, bbox[1]-3), (bbox[2]+4, bbox[3]+3)], radius=6, fill=(*glow, 220))
        _draw_text(draw, (28, kw_box_y), kw_text, fill=(*acc_rgb, 255), font=font_kw, rtl=rtl, max_width=body_max_w)
        kw_y_positions.append(kw_box_y + 14)
        kw_box_y += 50

    # Subtitle bar
    narration_flat = " ".join(narration_lines)
    sub_lines = _wrap_words(narration_flat, font_sub, sub_max_w)
    draw.rectangle([(0, HEIGHT - 90), (WIDTH - 360, HEIGHT)], fill=(0, 0, 0, 180))
    for i, sl in enumerate(sub_lines[:2]):
        _draw_text(draw, (20, HEIGHT - 82 + i * 36), sl, fill=(255, 255, 255, 230), font=font_sub, rtl=rtl, max_width=sub_max_w)

    bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
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
    """
    Write raw frames for one scene to a temp .avi file using cv2.VideoWriter.
    Returns path to the .avi.  Called in a thread.
    """
    avi_path = os.path.join(tmp_dir, f"scene_{scene_idx:03d}.avi")
    fourcc   = cv2.VideoWriter_fourcc(*"MJPG")
    writer   = cv2.VideoWriter(avi_path, fourcc, FPS, (WIDTH, HEIGHT))

    n_frames = max(1, int(duration * FPS))

    # Pre-compute teacher region once (it's static)
    teacher_base = None
    if teacher_img is not None:
        th, tw = teacher_img.shape[:2]
        tx, ty = WIDTH - tw - 10, HEIGHT - th - 80
        # Composite teacher onto a blank copy of static — saves per-frame alpha blend
        base_with_teacher = static_bgr.copy()
        overlay_image_alpha(base_with_teacher, teacher_img, tx, ty)
        teacher_base = base_with_teacher
        teacher_info = (tx, ty, tw, th)
    else:
        teacher_base = static_bgr
        teacher_info = None

    for fi in range(n_frames):
        t = fi / FPS
        frame = teacher_base.copy()

        # Progress bar — just 2 rectangles
        prog_w = int(min(1.0, t / max(duration, 0.01)) * WIDTH)
        cv2.rectangle(frame, (0, HEIGHT - 6), (WIDTH, HEIGHT), (30, 30, 30), -1)
        cv2.rectangle(frame, (0, HEIGHT - 6), (prog_w, HEIGHT), (100, 180, 255), -1)
        if prog_w > 8:
            cv2.circle(frame, (prog_w, HEIGHT - 3), 5, (150, 220, 255), -1)

        # Mouth toggle: open every even second, closed every odd
        if teacher_info is not None:
            tx, ty, tw, th = teacher_info
            m_img = mouth_open if int(t) % 2 == 0 else mouth_closed
            if m_img is not None:
                mh, mw = m_img.shape[:2]
                overlay_image_alpha(frame, m_img, tx + tw // 2 - mw // 2, ty + th // 2 + 10)

        # Pointer hover on keyword
        if pointer_img is not None and kw_y_positions:
            ki      = min(int((t / max(duration, 0.01)) * len(kw_y_positions)), len(kw_y_positions) - 1)
            hover_x = int(math.sin(t * 4) * 7)
            overlay_image_alpha(frame, pointer_img, 6 + hover_x, kw_y_positions[ki] - 16)

        writer.write(frame)

    writer.release()
    return avi_path


def _mux_scene(avi_path: str, audio_path: Optional[str], out_mp4: str) -> str:
    """Combine avi + audio into mp4 using ffmpeg. No Python overhead."""
    if audio_path and os.path.exists(audio_path):
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", avi_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "96k",
            "-shortest",
            out_mp4,
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", avi_path,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-an",
            out_mp4,
        ]
    subprocess.run(cmd, check=True, timeout=60)
    return out_mp4


def _concat_mp4s(mp4_list: list[str], output_path: str) -> None:
    """Concatenate multiple mp4 clips using ffmpeg concat demuxer (no re-encode)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as flist:
        for p in mp4_list:
            flist.write(f"file '{p}'\n")
        flist_path = flist.name
    try:
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", flist_path,
            "-c", "copy",
            output_path,
        ], check=True, timeout=120)
    finally:
        os.unlink(flist_path)


async def generate_video(
    scenes: dict,
    output_filename: str = None,
    lang_code: str = "en",
) -> dict:
    """
    Ultra-fast video generation.
    Uses cv2.VideoWriter + ffmpeg directly.  No MoviePy.
    Scenes are rendered in parallel threads.
    """
    import asyncio

    if not output_filename:
        output_filename = f"edugen_{uuid.uuid4().hex[:8]}.mp4"

    output_path  = VIDEO_DIR / output_filename
    scene_list   = scenes.get("scenes", [])
    total_scenes = len(scene_list)

    if not total_scenes:
        raise RuntimeError("No scenes to render")

    t0 = time.time()

    # ── Load shared assets ONCE ──────────────────────────────
    teacher_img  = _load_asset("teacher.png")
    mouth_open   = _load_asset("mouth_open.png")
    mouth_closed = _load_asset("mouth_closed.png")
    _hand = _load_asset("hand.png")
    pointer_img  = _hand if _hand is not None else _load_asset("pointer.png")

    if pointer_img is not None and pointer_img.shape[0] > 80:
        pointer_img = cv2.resize(pointer_img, (55, 55))
    if teacher_img is not None and teacher_img.shape[0] > 320:
        scale = 280 / teacher_img.shape[0]
        teacher_img = cv2.resize(teacher_img, (int(teacher_img.shape[1] * scale), 280))

    font_body  = _get_pil_font(30, lang_code)
    max_text_w = WIDTH - 420

    # ── Prepare scene data ───────────────────────────────────
    scene_data = []
    for idx, scene in enumerate(scene_list):
        duration     = float(scene.get("audio_duration", scene.get("duration_seconds", 10)))
        audio_path   = scene.get("audio_path", "")
        narration    = scene.get("narration", "")
        title        = scene.get("title", f"Scene {idx + 1}")
        key_concepts = scene.get("key_concepts", [])
        emotion      = scene.get("detected_emotion", scene.get("emotion", "neutral"))
        scene_num    = scene.get("scene_id", idx + 1)
        clean_kws    = [kw.lstrip("-*•➤> \t") for kw in key_concepts if kw.strip()]
        narr_lines   = _wrap_words(narration, font_body, max_text_w)
        scene_data.append((idx, scene, duration, audio_path, title, clean_kws, emotion, scene_num, narr_lines))

    # ── Render static frames in parallel threads ─────────────
    loop = asyncio.get_event_loop()
    tmp_dir = tempfile.mkdtemp(prefix="edugen_")

    def _render_one(args):
        idx, scene, duration, audio_path, title, clean_kws, emotion, scene_num, narr_lines = args
        static_bgr, kw_y = _render_static_frame(
            title, narr_lines, clean_kws, emotion, scene_num, total_scenes, lang_code
        )
        avi_path = _write_scene_video(
            idx, static_bgr, kw_y, duration,
            teacher_img, mouth_open, mouth_closed, pointer_img, tmp_dir
        )
        mp4_path = os.path.join(tmp_dir, f"scene_{idx:03d}.mp4")
        _mux_scene(avi_path, audio_path if os.path.exists(audio_path or "") else None, mp4_path)
        try:
            os.unlink(avi_path)  # free disk immediately
        except Exception:
            pass
        return mp4_path

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(total_scenes, 4)) as pool:
        futures = [loop.run_in_executor(pool, _render_one, args) for args in scene_data]
        mp4_paths = await asyncio.gather(*futures)

    # Sort in scene order (parallel may return out of order)
    mp4_paths = sorted(mp4_paths)

    # ── Concatenate or move ───────────────────────────────────
    if len(mp4_paths) == 1:
        import shutil
        shutil.move(mp4_paths[0], str(output_path))
    else:
        _concat_mp4s(list(mp4_paths), str(output_path))

    # Cleanup tmp files
    for p in mp4_paths:
        try:
            os.unlink(p)
        except Exception:
            pass
    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass

    elapsed = time.time() - t0
    total_dur = sum(
        s.get("actual_duration", s.get("audio_duration", s.get("duration_seconds", 10)))
        for s in scene_list
    )

    logger.info(f"🎬 Video done in {elapsed:.1f}s: {output_filename} ({total_dur:.1f}s content, {total_scenes} scenes)")

    return {
        "video_path":    str(output_path),
        "filename":      output_filename,
        "duration":      round(total_dur, 1),
        "render_time_s": round(elapsed, 1),
        "resolution":    f"{WIDTH}x{HEIGHT}",
        "fps":           FPS,
        "total_scenes":  total_scenes,
    }
