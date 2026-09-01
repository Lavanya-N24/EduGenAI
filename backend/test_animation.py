"""
EduGenAI - Educational Visual Animation Engine

This is the first visual layer for the new pipeline.

Purpose:
- Turn a real/illustrated background image into an animated educational scene.
- Add meaningful motion such as:
    * sunlight rays
    * floating particles
    * water moving upward
    * CO2 moving toward a leaf
    * gentle plant/leaf sway
    * camera zoom/pan
    * concept labels/highlights
- Does NOT generate AI video.
- Designed to work with Pexels/Pixabay/local images later.
- Manim remains responsible for equations and precise diagrams.

The renderer intentionally keeps the background image visible instead
of replacing it with circles/arrows.
"""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


WIDTH = 1280
HEIGHT = 720
FPS = 24


# ------------------------------------------------------------
# Image preparation
# ------------------------------------------------------------

def _fit_background(
    image: np.ndarray,
    width: int = WIDTH,
    height: int = HEIGHT,
    zoom: float = 1.0,
) -> np.ndarray:
    """Cover the complete video frame while preserving aspect ratio."""

    if image is None:
        return np.zeros(
            (height, width, 3),
            dtype=np.uint8,
        )

    h, w = image.shape[:2]

    scale = max(
        width / max(w, 1),
        height / max(h, 1),
    ) * zoom

    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))

    resized = cv2.resize(
        image,
        (nw, nh),
        interpolation=cv2.INTER_AREA
        if scale < 1
        else cv2.INTER_LINEAR,
    )

    x = max(0, (nw - width) // 2)
    y = max(0, (nh - height) // 2)

    frame = resized[
        y:y + height,
        x:x + width,
    ]

    if frame.shape[0] != height or frame.shape[1] != width:
        frame = cv2.resize(
            frame,
            (width, height),
        )

    return frame.copy()


def _smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def _draw_glow(
    frame: np.ndarray,
    center: tuple[int, int],
    radius: int,
    strength: float = 0.35,
) -> None:
    """Add a soft white/yellow-style glow without requiring an asset."""

    overlay = np.zeros_like(frame)

    cv2.circle(
        overlay,
        center,
        radius,
        (245, 230, 150),
        -1,
    )

    overlay = cv2.GaussianBlur(
        overlay,
        (0, 0),
        radius / 2,
    )

    cv2.addWeighted(
        frame,
        1.0,
        overlay,
        strength,
        0,
        dst=frame,
    )


# ------------------------------------------------------------
# Educational motion
# ------------------------------------------------------------

def _animate_sunlight(
    frame: np.ndarray,
    t: float,
) -> None:
    """Animate sunlight rays toward the lower-middle area."""

    sun_x = 1080
    sun_y = 110

    _draw_glow(
        frame,
        (sun_x, sun_y),
        85,
        0.18,
    )

    # Sun disk
    cv2.circle(
        frame,
        (sun_x, sun_y),
        42,
        (60, 210, 245),
        -1,
    )

    pulse = 1.0 + 0.08 * math.sin(t * 3.0)

    for i in range(8):
        angle = (
            2 * math.pi * i / 8
            + 0.05 * math.sin(t)
        )

        inner = 52
        outer = int(78 * pulse)

        x1 = int(
            sun_x + math.cos(angle) * inner
        )
        y1 = int(
            sun_y + math.sin(angle) * inner
        )

        x2 = int(
            sun_x + math.cos(angle) * outer
        )
        y2 = int(
            sun_y + math.sin(angle) * outer
        )

        cv2.line(
            frame,
            (x1, y1),
            (x2, y2),
            (80, 220, 255),
            5,
            cv2.LINE_AA,
        )

    # Moving rays
    for i in range(4):
        progress = (
            (t * 0.18 + i * 0.25)
            % 1.0
        )

        x = int(
            sun_x
            + (progress - 0.5) * 520
        )

        y = int(
            sun_y
            + progress * 450
        )

        cv2.circle(
            frame,
            (x, y),
            4,
            (120, 230, 255),
            -1,
            cv2.LINE_AA,
        )


def _animate_water(
    frame: np.ndarray,
    t: float,
) -> None:
    """Show water particles moving upward through a plant region."""

    start_x = 300
    bottom_y = 650
    top_y = 270

    for i in range(8):
        progress = (
            t * 0.16
            + i * 0.12
        ) % 1.0

        y = int(
            bottom_y
            - _smoothstep(progress)
            * (bottom_y - top_y)
        )

        x = int(
            start_x
            + math.sin(
                t * 2.0 + i
            ) * 18
        )

        cv2.circle(
            frame,
            (x, y),
            7,
            (230, 190, 70),
            -1,
            cv2.LINE_AA,
        )

        # Short motion trail
        cv2.line(
            frame,
            (x, y + 22),
            (x, y + 7),
            (240, 210, 100),
            3,
            cv2.LINE_AA,
        )


def _animate_co2(
    frame: np.ndarray,
    t: float,
) -> None:
    """Move CO2-like particles toward a leaf area."""

    target = np.array(
        [700.0, 310.0]
    )

    for i in range(7):
        phase = (
            t * 0.12
            + i * 0.15
        ) % 1.0

        start = np.array(
            [
                1050.0,
                250.0 + i * 50,
            ]
        )

        p = _smoothstep(phase)

        point = (
            start * (1.0 - p)
            + target * p
        )

        x = int(point[0])
        y = int(
            point[1]
            + math.sin(
                t * 3 + i
            ) * 8
        )

        # CO2 particle
        cv2.circle(
            frame,
            (x, y),
            9,
            (185, 190, 200),
            -1,
            cv2.LINE_AA,
        )

        # Two small atoms
        cv2.circle(
            frame,
            (x - 9, y),
            4,
            (210, 80, 80),
            -1,
            cv2.LINE_AA,
        )

        cv2.circle(
            frame,
            (x + 9, y),
            4,
            (210, 80, 80),
            -1,
            cv2.LINE_AA,
        )


def _animate_leaf_sway(
    frame: np.ndarray,
    t: float,
    region: Optional[tuple[int, int, int, int]],
) -> None:
    """
    Add a subtle moving highlight around the supplied leaf region.

    region = x, y, width, height
    """

    if not region:
        return

    x, y, w, h = region

    sway = int(
        math.sin(t * 2.0) * 5
    )

    overlay = frame.copy()

    cv2.ellipse(
        overlay,
        (
            x + w // 2 + sway,
            y + h // 2,
        ),
        (
            max(10, w // 2),
            max(10, h // 2),
        ),
        -15,
        0,
        360,
        (100, 255, 140),
        3,
        cv2.LINE_AA,
    )

    cv2.addWeighted(
        overlay,
        0.35,
        frame,
        0.65,
        0,
        dst=frame,
    )


# ------------------------------------------------------------
# Scene renderer
# ------------------------------------------------------------

def render_educational_scene(
    image_path: Optional[str],
    output_path: str,
    duration: float,
    motion: str = "plant_sunlight",
    zoom_start: float = 1.00,
    zoom_end: float = 1.08,
    leaf_region: Optional[tuple[int, int, int, int]] = None,
) -> str:
    """
    Render an animated educational scene from a background image.

    motion options:
        plant_sunlight
        water
        co2
        leaf
        mixed
        gentle_zoom

    If image_path is None, a clean dark background is used.
    """

    duration = max(
        1.0,
        float(duration),
    )

    out = Path(output_path)
    out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if image_path and os.path.exists(
        image_path
    ):
        image = cv2.imread(
            image_path,
            cv2.IMREAD_COLOR,
        )
    else:
        image = None

    writer = cv2.VideoWriter(
        str(out),
        cv2.VideoWriter_fourcc(*"mp4v"),
        FPS,
        (WIDTH, HEIGHT),
    )

    if not writer.isOpened():
        raise RuntimeError(
            "Could not open video writer."
        )

    total_frames = max(
        1,
        int(round(duration * FPS)),
    )

    for frame_index in range(
        total_frames
    ):

        t = frame_index / FPS

        progress = min(
            1.0,
            t / duration,
        )

        # Smooth camera movement.
        zoom = (
            zoom_start
            + (
                zoom_end
                - zoom_start
            )
            * _smoothstep(progress)
        )

        frame = _fit_background(
            image,
            WIDTH,
            HEIGHT,
            zoom,
        )

        # If no image is available, use a clean educational canvas.
        if image is None:
            frame[:] = (
                18,
                24,
                38,
            )

        motion_name = (
            motion or "gentle_zoom"
        ).lower()

        if motion_name in (
            "plant_sunlight",
            "mixed",
        ):
            _animate_sunlight(
                frame,
                t,
            )

        if motion_name in (
            "water",
            "mixed",
        ):
            _animate_water(
                frame,
                t,
            )

        if motion_name in (
            "co2",
            "mixed",
        ):
            _animate_co2(
                frame,
                t,
            )

        if motion_name == "leaf":
            _animate_leaf_sway(
                frame,
                t,
                leaf_region,
            )

        if motion_name == "gentle_zoom":
            pass

        # Always allow a subtle highlight when a leaf region is known.
        if leaf_region and motion_name in (
            "plant_sunlight",
            "mixed",
            "leaf",
        ):
            _animate_leaf_sway(
                frame,
                t,
                leaf_region,
            )

        writer.write(frame)

    writer.release()

    # Re-encode to H.264/yuv420p so browsers can play it reliably.
    normalized = str(
        out.with_suffix(".h264.mp4")
    )

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(out),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "22",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                normalized,
            ],
            check=True,
            timeout=180,
        )

        os.replace(
            normalized,
            str(out),
        )

    finally:
        if os.path.exists(
            normalized
        ):
            try:
                os.remove(
                    normalized
                )
            except OSError:
                pass

    return str(out)


# ------------------------------------------------------------
# Compatibility entry point
# ------------------------------------------------------------

def fetch_scene_animation(
    image_path: Optional[str],
    output_path: str,
    duration: float,
    motion: str = "plant_sunlight",
    leaf_region: Optional[
        tuple[int, int, int, int]
    ] = None,
) -> str:
    """Compatibility wrapper for services.video."""

    return render_educational_scene(
        image_path=image_path,
        output_path=output_path,
        duration=duration,
        motion=motion,
        leaf_region=leaf_region,
    )
