"""
EduGenAI - Dynamic Rich Educational Video Renderer

Purpose:
    Render the "rich" path as a real-visual, scene-by-scene educational video.

Each generated scene gets its own real-world image from image_fetcher.py.
The renderer applies a Ken-Burns camera move, highlight rings, animated
arrows/particles, explanation text, topic title, step indicator, and
optional teacher image. TTS audio is muxed into each scene.

Compatible entry point:
    generate_rich_video(scenes, output_filename, lang_code="en")
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import VIDEO_DIR, BASE_DIR
from services.image_fetcher import fetch_background_image, fetch_inset_image

logger = logging.getLogger(__name__)

WIDTH = 1280
HEIGHT = 720
FPS = 12
ASSETS = BASE_DIR / "assets"

ACCENT = (255, 210, 60)
WHITE = (255, 255, 255)
MUTED = (210, 225, 245)
PANEL = (8, 18, 38, 218)
DARK = (5, 12, 25, 225)

FONT_CACHE = {}


def _font(size: int, bold: bool = False):
    key = (size, bold)
    if key in FONT_CACHE:
        return FONT_CACHE[key]

    names = []
    if bold:
        names = [
            ASSETS / "NotoSans-Bold.ttf",
            "arialbd.ttf",
            "segoeui.ttf",
            ASSETS / "NotoSans-Regular.ttf",
            "arial.ttf",
        ]
    else:
        names = [
            ASSETS / "NotoSans-Regular.ttf",
            "arial.ttf",
            "segoeui.ttf",
            "tahoma.ttf",
        ]

    for name in names:
        try:
            f = ImageFont.truetype(str(name), size)
            FONT_CACHE[key] = f
            return f
        except Exception:
            continue

    f = ImageFont.load_default()
    FONT_CACHE[key] = f
    return f


def _wrap(text: str, font, max_width: int, max_lines: int = 3):
    if not text:
        return [""]

    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        candidate = f"{current} {word}".strip()
        try:
            width = dummy.textbbox((0, 0), candidate, font=font)[2]
        except Exception:
            width = len(candidate) * 10

        if width > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate

    if current:
        lines.append(current)

    return lines[:max_lines] or [""]


def _rounded(draw, box, radius=12, fill=None, outline=None, width=1):
    draw.rounded_rectangle(
        box,
        radius=radius,
        fill=fill,
        outline=outline,
        width=width,
    )


def _fit_image(image: Image.Image, width=WIDTH, height=HEIGHT):
    image = image.convert("RGB")
    ratio = max(width / image.width, height / image.height)
    nw = max(width, int(image.width * ratio))
    nh = max(height, int(image.height * ratio))
    image = image.resize((nw, nh), Image.LANCZOS)
    left = (nw - width) // 2
    top = (nh - height) // 2
    return image.crop((left, top, left + width, top + height))


def _ken_burns(image: Image.Image, progress: float, scene_index: int):
    """
    Slow zoom/pan. This makes a still photograph behave like a camera shot.
    """
    image = image.convert("RGB")

    scale = 1.0 + 0.08 * progress

    if scene_index % 2:
        scale = 1.0 + 0.10 * progress

    nw = int(WIDTH * scale)
    nh = int(HEIGHT * scale)

    enlarged = image.resize((nw, nh), Image.LANCZOS)

    max_x = max(0, nw - WIDTH)
    max_y = max(0, nh - HEIGHT)

    if scene_index % 3 == 0:
        x = int(max_x * progress)
        y = int(max_y * 0.35)
    elif scene_index % 3 == 1:
        x = int(max_x * (1.0 - progress))
        y = int(max_y * 0.65)
    else:
        x = int(max_x * 0.5)
        y = int(max_y * progress)

    return enlarged.crop((x, y, x + WIDTH, y + HEIGHT))


def _dark_overlay(base: Image.Image):
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay, "RGBA")

    # Top/bottom readability gradients approximated by bands.
    for i in range(180):
        a = int(100 * (1 - i / 180))
        d.rectangle((0, i, WIDTH, i + 1), fill=(0, 0, 0, a))

    for i in range(150):
        a = int(125 * (1 - i / 150))
        y = HEIGHT - 150 + i
        d.rectangle((0, y, WIDTH, y + 1), fill=(0, 0, 0, a))

    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _scene_text(scene: dict):
    """
    Extract explanation text from several common scene schemas so the
    renderer remains compatible with existing Groq scene generation.
    """
    for key in (
        "narration",
        "narration_text",
        "voiceover",
        "explanation",
        "description",
        "text",
        "script",
    ):
        value = scene.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return ""


def _scene_query(scene: dict, topic: str):
    """
    Prefer an explicit visual query. Otherwise derive a practical search
    phrase from the scene's text. This keeps the system topic-independent.
    """
    for key in (
        "visual_query",
        "image_query",
        "visual_search_query",
        "search_query",
    ):
        value = scene.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    text = _scene_text(scene)
    text = re.sub(r"\s+", " ", text).strip()

    # Keep search requests short enough for image search.
    words = re.findall(r"[A-Za-z0-9₂₃₄₅₆₇₈₉COHNSa-z-]+", text)
    keywords = words[:9]

    if keywords:
        return f"{topic} {' '.join(keywords)} photograph"

    return f"{topic} photograph"


def _draw_arrow(draw, start, end, color=(255, 210, 60), progress=1.0):
    """
    Animated quadratic arrow. Only the first 'progress' portion is drawn.
    """
    x0, y0 = start
    x1, y1 = end

    mx = (x0 + x1) / 2
    my = (y0 + y1) / 2

    dx = x1 - x0
    dy = y1 - y0

    cx = mx - dy * 0.22
    cy = my + dx * 0.22

    points = []
    count = 32
    end_i = max(2, int(count * min(1.0, progress)))

    for i in range(end_i + 1):
        t = i / count
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        points.append((int(x), int(y)))

    if len(points) > 1:
        draw.line(points, fill=(*color, 230), width=4)

        ax, ay = points[-1]
        bx, by = points[-2]
        angle = math.atan2(ay - by, ax - bx)
        size = 13

        for delta in (math.pi / 6, -math.pi / 6):
            ex = ax - size * math.cos(angle + delta)
            ey = ay - size * math.sin(angle + delta)
            draw.line(
                [(ax, ay), (int(ex), int(ey))],
                fill=(*color, 230),
                width=4,
            )


def _draw_topic_bar(draw, layout, scene_index, total_scenes):
    title = str(layout.get("topic_title", "EDUGENAI")).upper()[:34]
    subtitle = str(layout.get("topic_subtitle", ""))[:70]

    _rounded(
        draw,
        (20, 18, 510, 92),
        14,
        fill=(12, 18, 28, 225),
        outline=(*ACCENT, 230),
        width=2,
    )

    draw.text(
        (34, 27),
        "TOPIC",
        fill=(255, 220, 100, 255),
        font=_font(14, True),
    )

    draw.text(
        (34, 46),
        title,
        fill=WHITE,
        font=_font(22, True),
    )

    if subtitle:
        draw.text(
            (300, 29),
            subtitle[:38],
            fill=(210, 225, 240, 230),
            font=_font(12),
        )

    step = f"SCENE {scene_index + 1} / {total_scenes}"
    draw.text(
        (1040, 30),
        step,
        fill=(255, 255, 255, 230),
        font=_font(14, True),
    )


def _draw_explanation_panel(draw, text, scene_index, total_scenes):
    """
    The explanation panel is deliberately scene-specific. It changes with
    every narrated scene instead of showing one static process list.
    """
    if not text:
        return

    box = (35, 510, 790, 675)

    _rounded(
        draw,
        box,
        16,
        fill=(7, 15, 28, 215),
        outline=(90, 130, 180, 140),
        width=1,
    )

    draw.text(
        (58, 528),
        "WHAT IS HAPPENING?",
        fill=(110, 200, 255, 255),
        font=_font(15, True),
    )

    lines = _wrap(
        text,
        _font(18),
        690,
        max_lines=5,
    )

    y = 558
    for line in lines:
        draw.text(
            (58, y),
            line,
            fill=(245, 248, 252, 245),
            font=_font(18),
        )
        y += 27


def _draw_step_indicator(draw, process_steps, active_index):
    if not process_steps:
        return

    x0 = 835
    y0 = 120
    w = 400
    h = min(350, 60 + len(process_steps) * 47)

    _rounded(
        draw,
        (x0, y0, x0 + w, y0 + h),
        14,
        fill=(7, 15, 28, 205),
        outline=(80, 120, 170, 130),
        width=1,
    )

    draw.text(
        (x0 + 18, y0 + 15),
        "THE PROCESS",
        fill=(110, 200, 255, 255),
        font=_font(15, True),
    )

    for i, step in enumerate(process_steps[:6]):
        y = y0 + 50 + i * 47

        active = i == active_index

        col = (255, 210, 60) if active else (100, 150, 200)

        draw.ellipse(
            (x0 + 18, y + 3, x0 + 40, y + 25),
            fill=(*col, 230),
        )

        draw.text(
            (x0 + 25, y + 5),
            str(i + 1),
            fill=(10, 20, 30, 255),
            font=_font(12, True),
        )

        lines = _wrap(
            step,
            _font(12, active),
            335,
            max_lines=2,
        )

        for li, line in enumerate(lines):
            draw.text(
                (x0 + 50, y + li * 15),
                line,
                fill=WHITE if active else (190, 205, 225),
                font=_font(12, active),
            )


def _draw_annotations(draw, annotations, scene_index, progress):
    """
    Labels are staggered across the scene. Their arrows animate toward the
    image rather than appearing as static UI.
    """
    if not annotations:
        return

    positions = [
        (70, 145),
        (70, 300),
        (70, 445),
        (870, 470),
        (930, 285),
        (520, 130),
    ]

    targets = [
        (470, 250),
        (520, 330),
        (430, 430),
        (690, 430),
        (720, 310),
        (600, 250),
    ]

    colors = [
        (255, 210, 60),
        (80, 220, 180),
        (100, 190, 255),
        (255, 120, 80),
        (180, 120, 255),
        (255, 180, 80),
    ]

    for i, ann in enumerate(annotations[:6]):
        if not isinstance(ann, dict):
            continue

        # Reveal annotations progressively.
        reveal = min(1.0, max(0.0, progress * 1.8 - i * 0.16))
        if reveal <= 0:
            continue

        label = str(ann.get("label", "")).strip()
        sub = str(ann.get("sublabel", "")).strip()

        if not label:
            continue

        x, y = positions[i % len(positions)]
        tx, ty = targets[(scene_index + i) % len(targets)]
        color = colors[i % len(colors)]

        _draw_arrow(
            draw,
            (x + 85, y + 22),
            (tx, ty),
            color,
            reveal,
        )

        width = max(135, min(250, len(label) * 13 + 30))
        height = 60 if sub else 36

        _rounded(
            draw,
            (x, y, x + width, y + height),
            9,
            fill=(7, 15, 28, int(220 * reveal)),
            outline=(*color, int(235 * reveal)),
            width=2,
        )

        draw.text(
            (x + 10, y + 7),
            label[:22],
            fill=(*WHITE, int(255 * reveal)),
            font=_font(15, True),
        )

        if sub:
            draw.text(
                (x + 10, y + 30),
                sub[:32],
                fill=(*MUTED, int(220 * reveal)),
                font=_font(10),
            )


def _draw_moving_particles(draw, scene_index, progress):
    """
    Generic motion layer. It gives process scenes visible movement even when
    the source is a photograph. Groq controls the topic and explanation;
    these are visual motion cues, not a claim about exact object geometry.
    """
    colors = [
        (255, 210, 60),
        (100, 210, 255),
        (100, 240, 170),
    ]

    for i in range(5):
        phase = (progress + i * 0.19) % 1.0

        if scene_index % 3 == 0:
            x = int(230 + phase * 480)
            y = int(170 + i * 45 + math.sin(phase * math.pi * 2) * 18)
        elif scene_index % 3 == 1:
            x = int(690 - phase * 430)
            y = int(180 + i * 55)
        else:
            x = int(360 + math.sin(phase * math.pi * 2) * 170)
            y = int(250 + phase * 240)

        r = 5 + (i % 2) * 2
        col = colors[(scene_index + i) % len(colors)]

        draw.ellipse(
            (x - r, y - r, x + r, y + r),
            fill=(*col, 175),
        )


def _draw_focus_ring(draw, scene_index, progress):
    """
    Animated focus ring to direct attention to the current visual concept.
    """
    centers = [
        (540, 310),
        (640, 270),
        (460, 390),
        (690, 350),
        (570, 430),
        (610, 290),
    ]

    cx, cy = centers[scene_index % len(centers)]
    radius = int(42 + 15 * math.sin(progress * math.pi * 2))

    draw.ellipse(
        (
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
        ),
        outline=(255, 210, 60, 190),
        width=3,
    )


def _draw_bottom_bar(draw, chapters, active):
    y = HEIGHT - 42

    draw.rectangle(
        (0, y - 4, WIDTH, HEIGHT),
        fill=(5, 10, 20, 235),
    )

    x = 190

    for i, chapter in enumerate(chapters[:6]):
        text = str(chapter)[:18]
        width = max(95, len(text) * 8 + 26)
        active_now = i == active

        _rounded(
            draw,
            (x, y + 3, x + width, HEIGHT - 5),
            6,
            fill=(0, 130, 230, 220) if active_now else (20, 30, 50, 180),
        )

        draw.text(
            (x + 9, y + 12),
            text,
            fill=WHITE if active_now else (160, 180, 205),
            font=_font(11, active_now),
        )

        x += width + 8

    draw.text(
        (18, y + 10),
        "▶",
        fill=WHITE,
        font=_font(15, True),
    )


def _build_frame(
    bg_image,
    layout,
    scene,
    scene_index,
    total_scenes,
    progress,
    teacher_img=None,
    inset_img=None,
):
    base = _ken_burns(
        bg_image,
        progress,
        scene_index,
    )

    base = _dark_overlay(base)

    draw_layer = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        draw_layer,
        "RGBA",
    )

    _draw_topic_bar(
        draw,
        layout,
        scene_index,
        total_scenes,
    )

    process_steps = layout.get("process_steps", [])

    # Current scene maps to a process step when available.
    active_step = min(
        scene_index,
        max(0, len(process_steps) - 1),
    )

    _draw_step_indicator(
        draw,
        process_steps,
        active_step,
    )

    annotations = layout.get("annotations", [])
    _draw_annotations(
        draw,
        annotations,
        scene_index,
        progress,
    )

    _draw_moving_particles(
        draw,
        scene_index,
        progress,
    )

    _draw_focus_ring(
        draw,
        scene_index,
        progress,
    )

    explanation = _scene_text(scene)

    _draw_explanation_panel(
        draw,
        explanation,
        scene_index,
        total_scenes,
    )

    # Optional inset/detail visual.
    if inset_img is not None:
        x, y, w, h = 855, 485, 355, 165

        _rounded(
            draw,
            (x - 5, y - 28, x + w + 5, y + h + 7),
            10,
            fill=(5, 12, 25, 225),
            outline=(90, 150, 210, 150),
            width=1,
        )

        inset_title = str(
            layout.get("inset_panel", {}).get(
                "title",
                "DETAIL VIEW",
            )
        )[:38]

        draw.text(
            (x, y - 22),
            inset_title,
            fill=(110, 200, 255, 240),
            font=_font(11, True),
        )

        resized = inset_img.resize(
            (w, h),
            Image.LANCZOS,
        )

        base = Image.alpha_composite(
            base.convert("RGBA"),
            draw_layer,
        )

        base.paste(
            resized.convert("RGB"),
            (x, y),
        )

        # Redraw the lower title area because paste happens after overlays.
        draw2 = ImageDraw.Draw(base, "RGBA")
        draw2.text(
            (x, y - 22),
            inset_title,
            fill=(110, 200, 255, 240),
            font=_font(11, True),
        )
    else:
        base = Image.alpha_composite(
            base.convert("RGBA"),
            draw_layer,
        )

    # Teacher image is optional.
    if teacher_img is not None:
        frame = cv2.cvtColor(
            np.array(base.convert("RGB")),
            cv2.COLOR_RGB2BGR,
        )

        from services.video import overlay_image_alpha

        th, tw = teacher_img.shape[:2]

        max_h = 155
        if th > max_h:
            scale = max_h / th
            teacher = cv2.resize(
                teacher_img,
                (
                    max(1, int(tw * scale)),
                    max_h,
                ),
            )
        else:
            teacher = teacher_img

        th, tw = teacher.shape[:2]

        x = WIDTH - tw - 15
        y = HEIGHT - th - 50

        overlay_image_alpha(
            frame,
            teacher,
            x,
            y,
        )

        return frame

    return cv2.cvtColor(
        np.array(base.convert("RGB")),
        cv2.COLOR_RGB2BGR,
    )


def _write_scene(
    scene_index,
    scene,
    bg_image,
    layout,
    inset_img,
    teacher_img,
    duration,
    total_scenes,
    tmp_dir,
):
    avi_path = os.path.join(
        tmp_dir,
        f"rich_{scene_index:03d}.avi",
    )

    writer = cv2.VideoWriter(
        avi_path,
        cv2.VideoWriter_fourcc(*"MJPG"),
        FPS,
        (WIDTH, HEIGHT),
    )

    if not writer.isOpened():
        raise RuntimeError(
            f"Could not open video writer: {avi_path}"
        )

    frames = max(
        1,
        int(duration * FPS),
    )

    for fi in range(frames):
        progress = fi / max(1, frames - 1)

        frame = _build_frame(
            bg_image,
            layout,
            scene,
            scene_index,
            total_scenes,
            progress,
            teacher_img,
            inset_img,
        )

        # Scene progress bar.
        bar_y = HEIGHT - 5
        width = int(WIDTH * progress)

        cv2.rectangle(
            frame,
            (0, bar_y),
            (WIDTH, HEIGHT),
            (20, 30, 50),
            -1,
        )

        cv2.rectangle(
            frame,
            (0, bar_y),
            (width, HEIGHT),
            (255, 210, 60),
            -1,
        )

        writer.write(frame)

    writer.release()

    return avi_path


def _mux(avi_path, audio_path, output_path):
    has_audio = bool(
        audio_path
        and os.path.exists(audio_path)
    )

    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        avi_path,
    ]

    if has_audio:
        command += [
            "-i",
            audio_path,
        ]

    command += [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "24",
    ]

    if has_audio:
        command += [
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
        ]
    else:
        command += [
            "-an",
        ]

    command.append(output_path)

    subprocess.run(
        command,
        check=True,
        timeout=180,
    )

    return output_path


def _concat(mp4s, output):
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
    ) as f:
        for path in mp4s:
            safe = str(path).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        list_file = f.name

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
                list_file,
                "-c",
                "copy",
                output,
            ],
            check=True,
            timeout=300,
        )
    finally:
        try:
            os.unlink(list_file)
        except OSError:
            pass


async def _fetch_scene_images(scene_list, topic):
    """
    Fetch a different real visual for every scene.

    This is the key change from the previous renderer:
    the same background is NOT reused for all scenes.
    """
    async def fetch_one(index, scene):
        query = _scene_query(
            scene,
            topic,
        )

        try:
            image = await fetch_background_image(
                query,
                subject="biology",
                force_refresh=False,
            )

            return index, image, query

        except Exception as error:
            logger.warning(
                "Scene %s image failed: %s",
                index,
                error,
            )

            # Last-resort visual: use topic image.
            try:
                image = await fetch_background_image(
                    topic,
                    subject="default",
                    force_refresh=False,
                )
                return index, image, topic
            except Exception:
                return index, None, query

    results = await asyncio.gather(
        *[
            fetch_one(i, scene)
            for i, scene in enumerate(scene_list)
        ]
    )

    results.sort(key=lambda item: item[0])

    return results


async def generate_rich_video(
    scenes: dict,
    output_filename: str,
    lang_code: str = "en",
) -> dict:
    """
    Main entry point used by services.video.

    Keeps the existing function signature so video.py does not need to
    change.
    """
    start = time.time()

    layout = scenes.get(
        "rich_layout",
        {},
    )

    scene_list = scenes.get(
        "scenes",
        [],
    )

    topic = (
        scenes.get("title")
        or layout.get("topic_title")
        or "education"
    )

    if not scene_list:
        raise RuntimeError(
            "No scenes to render (rich path)"
        )

    VIDEO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = VIDEO_DIR / output_filename

    # ---------------------------------------------------------
    # REAL VISUALS: one image per scene
    # ---------------------------------------------------------
    fetched = await _fetch_scene_images(
        scene_list,
        topic,
    )

    scene_images = [
        item[1]
        for item in fetched
    ]

    logger.info(
        "Fetched %d scene visuals for %s",
        len(scene_images),
        topic,
    )

    # ---------------------------------------------------------
    # Optional inset image
    # ---------------------------------------------------------
    inset_data = layout.get(
        "inset_panel",
        {},
    )

    inset_query = inset_data.get(
        "image_query",
        "",
    )

    inset_img = None

    if inset_query:
        try:
            inset_img = await fetch_inset_image(
                inset_query,
                360,
                200,
            )
        except Exception as error:
            logger.warning(
                "Inset image failed: %s",
                error,
            )

    # ---------------------------------------------------------
    # Teacher image
    # ---------------------------------------------------------
    teacher_img = None

    teacher_path = ASSETS / "teacher.png"

    if teacher_path.exists():
        raw = cv2.imread(
            str(teacher_path),
            cv2.IMREAD_UNCHANGED,
        )

        if raw is not None:
            teacher_img = raw

    # ---------------------------------------------------------
    # Render each scene
    # ---------------------------------------------------------
    tmp_dir = tempfile.mkdtemp(
        prefix="edurich_"
    )

    mp4_paths = []

    try:
        total_scenes = len(scene_list)

        for index, scene in enumerate(scene_list):

            image = scene_images[index]

            if image is None:
                logger.warning(
                    "No image for scene %d; skipping scene image",
                    index,
                )
                continue

            duration = float(
                scene.get(
                    "audio_duration",
                    scene.get(
                        "duration_seconds",
                        8,
                    ),
                )
            )

            duration = max(
                1.5,
                duration,
            )

            audio_path = scene.get(
                "audio_path",
                "",
            )

            avi = _write_scene(
                index,
                scene,
                image,
                layout,
                inset_img,
                teacher_img,
                duration,
                total_scenes,
                tmp_dir,
            )

            mp4 = os.path.join(
                tmp_dir,
                f"rich_{index:03d}.mp4",
            )

            _mux(
                avi,
                audio_path
                if audio_path
                and os.path.exists(audio_path)
                else None,
                mp4,
            )

            mp4_paths.append(mp4)

            try:
                os.unlink(avi)
            except OSError:
                pass

        if not mp4_paths:
            raise RuntimeError(
                "No rich scenes were successfully rendered."
            )

        # -----------------------------------------------------
        # Concatenate scenes
        # -----------------------------------------------------
        if len(mp4_paths) == 1:
            shutil.copy2(
                mp4_paths[0],
                output_path,
            )
        else:
            _concat(
                mp4_paths,
                str(output_path),
            )

    finally:
        shutil.rmtree(
            tmp_dir,
            ignore_errors=True,
        )

    total_duration = sum(
        float(
            scene.get(
                "audio_duration",
                scene.get(
                    "duration_seconds",
                    8,
                ),
            )
        )
        for scene in scene_list
    )

    elapsed = time.time() - start

    logger.info(
        "Dynamic rich video finished in %.1fs: %s",
        elapsed,
        output_filename,
    )

    return {
        "video_path": str(output_path),
        "filename": output_filename,
        "duration": round(total_duration, 1),
        "render_time_s": round(elapsed, 1),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "total_scenes": len(scene_list),
        "renderer": "rich_dynamic",
        "lang_code": lang_code,
    }
