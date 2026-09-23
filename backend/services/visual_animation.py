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

import re
import math
import os
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH = 854
HEIGHT = 480
FPS = 6


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


def _draw_stage_badge(pil_draw, text: str, step_num: int, color_bg: tuple, width: int = WIDTH):
    """Draw a clean, sleek educational stage header badge without emoji glyph issues."""
    font_badge = _get_font(13, is_bold=True)
    badge_str = f"STEP {step_num}: {text.upper()}"
    bbox = pil_draw.textbbox((0, 0), badge_str, font=font_badge)
    tw = bbox[2] - bbox[0]
    bx1 = 30
    by1 = 20
    bx2 = bx1 + tw + 28
    by2 = by1 + 26
    pil_draw.rectangle([(bx1, by1), (bx2, by2)], fill=color_bg)
    pil_draw.text((bx1 + 14, by1 + 4), badge_str, font=font_badge, fill=(255, 255, 255))


# ── Stage 1: Solar Energy & Light Absorption ──
def _animate_scene_sunlight(frame: np.ndarray, t: float) -> None:
    """Scene 1: Glowing radiant Sun emitting dynamic photon streams into green leaves."""
    h, w = frame.shape[:2]
    frame[:] = (24, 20, 16) # Deep space/sky background

    # Radiant Sun at Top-Left
    sun_x, sun_y = 150, 140
    _draw_glow(frame, (sun_x, sun_y), 110, 0.35)
    cv2.circle(frame, (sun_x, sun_y), 48, (50, 210, 255), -1, cv2.LINE_AA)

    # Rotating solar corona rays
    for i in range(12):
        angle = 2 * math.pi * i / 12 + t * 0.35
        pulse = 1.0 + 0.12 * math.sin(t * 3.0 + i)
        x1 = int(sun_x + math.cos(angle) * 56)
        y1 = int(sun_y + math.sin(angle) * 56)
        x2 = int(sun_x + math.cos(angle) * int(82 * pulse))
        y2 = int(sun_y + math.sin(angle) * int(82 * pulse))
        cv2.line(frame, (x1, y1), (x2, y2), (70, 225, 255), 3, cv2.LINE_AA)

    # Large Green Leaf absorbing light on the Right
    leaf_cx, leaf_cy = int(w * 0.65), int(h * 0.58)
    cv2.ellipse(frame, (leaf_cx, leaf_cy), (160, 80), -20, 0, 360, (30, 130, 60), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (leaf_cx, leaf_cy), (160, 80), -20, 0, 360, (60, 200, 100), 3, cv2.LINE_AA)
    # Leaf primary vein
    cv2.line(frame, (leaf_cx - 140, leaf_cy + 50), (leaf_cx + 140, leaf_cy - 50), (90, 230, 130), 3, cv2.LINE_AA)

    # Secondary veins
    for vi in range(-3, 4):
        vx = leaf_cx + vi * 35
        vy = leaf_cy - vi * 12
        cv2.line(frame, (vx, vy), (vx - 30, vy - 40), (80, 210, 110), 2, cv2.LINE_AA)
        cv2.line(frame, (vx, vy), (vx + 30, vy + 40), (80, 210, 110), 2, cv2.LINE_AA)

    # Dynamic light photon streams cascading into the leaf
    for i in range(8):
        p = (t * 0.35 + i * 0.125) % 1.0
        px = int(sun_x + (leaf_cx - 40 - sun_x) * p)
        py = int(sun_y + (leaf_cy - 30 - sun_y) * p + math.sin(t * 5.0 + i) * 8)
        cv2.circle(frame, (px, py), 6, (120, 240, 255), -1, cv2.LINE_AA)
        cv2.line(frame, (px - 14, py - 10), (px, py), (160, 245, 255), 2, cv2.LINE_AA)

    # Labels
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Solar Energy & Light Absorption", 1, (217, 119, 6), w)
    
    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(sun_x - 70, sun_y + 65), (sun_x + 70, sun_y + 87)], fill=(180, 83, 9))
    draw.text((sun_x - 62, sun_y + 68), "Sun: Light Energy", font=font_sub, fill=(255, 255, 255))

    draw.rectangle([(leaf_cx - 90, leaf_cy + 95), (leaf_cx + 110, leaf_cy + 117)], fill=(22, 101, 52))
    draw.text((leaf_cx - 82, leaf_cy + 98), "Chlorophyll absorbs Photons", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Stage 2: Water (H2O) Absorption via Roots & Stem Xylem ──
def _animate_scene_roots_water(frame: np.ndarray, t: float) -> None:
    """Scene 2: Underground root system absorbing H2O and transporting it up the Xylem."""
    h, w = frame.shape[:2]
    frame[:int(h * 0.38), :] = (26, 20, 15) # Atmosphere
    frame[int(h * 0.38):, :] = (20, 32, 45) # Soil layer
    cv2.line(frame, (0, int(h * 0.38)), (w, int(h * 0.38)), (50, 90, 120), 2, cv2.LINE_AA)

    stem_x = int(w * 0.5)
    soil_y = int(h * 0.38)

    # Root network spreading through soil
    root_branches = [
        ((stem_x, soil_y), (stem_x - 120, soil_y + 120)),
        ((stem_x - 60, soil_y + 60), (stem_x - 190, soil_y + 150)),
        ((stem_x - 120, soil_y + 120), (stem_x - 160, soil_y + 220)),
        ((stem_x, soil_y), (stem_x + 130, soil_y + 130)),
        ((stem_x + 65, soil_y + 65), (stem_x + 200, soil_y + 160)),
        ((stem_x + 130, soil_y + 130), (stem_x + 170, soil_y + 230)),
        ((stem_x, soil_y), (stem_x, soil_y + 240)),
        ((stem_x, soil_y + 120), (stem_x - 50, soil_y + 230)),
        ((stem_x, soil_y + 120), (stem_x + 50, soil_y + 230)),
    ]
    for p1, p2 in root_branches:
        cv2.line(frame, p1, p2, (80, 130, 180), 4, cv2.LINE_AA)

    # Green stem rising above ground
    cv2.line(frame, (stem_x, soil_y), (stem_x, 60), (45, 160, 75), 14, cv2.LINE_AA)
    cv2.line(frame, (stem_x, soil_y), (stem_x, 60), (80, 220, 120), 4, cv2.LINE_AA) # Xylem core

    # Water H2O molecules permeating from soil into roots and moving UP the stem
    for i in range(14):
        wp = (t * 0.32 + i * 0.07) % 1.0
        # Flowing up from deep root tips into the stem
        wy = int((h - 30) - wp * (h - 90))
        wx = int(stem_x + math.sin(t * 4.0 + i) * 6)
        cv2.circle(frame, (wx, wy), 6, (245, 185, 45), -1, cv2.LINE_AA) # Blue-cyan BGR
        cv2.circle(frame, (wx, wy), 8, (255, 230, 120), 1, cv2.LINE_AA)

    # Water droplets in surrounding soil
    for i in range(8):
        sx = int(stem_x - 180 + i * 45 + math.sin(t * 2 + i) * 8)
        sy = int(soil_y + 50 + (i % 4) * 45)
        cv2.circle(frame, (sx, sy), 5, (230, 160, 30), -1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Water (H2O) Uptake via Roots & Xylem", 2, (37, 99, 235), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(stem_x + 25, 100), (stem_x + 235, 122)], fill=(29, 78, 216))
    draw.text((stem_x + 33, 103), "Xylem: Water Flowing Upward", font=font_sub, fill=(255, 255, 255))

    draw.rectangle([(stem_x - 220, h - 60), (stem_x - 20, h - 38)], fill=(30, 64, 175))
    draw.text((stem_x - 212, h - 57), "Roots Absorb H2O & Minerals", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Stage 3: Carbon Dioxide (CO2) Intake via Stomata ──
def _animate_scene_stomata_co2(frame: np.ndarray, t: float) -> None:
    """Scene 3: Microscopic zoom of leaf underside stoma pore opening & absorbing CO2."""
    h, w = frame.shape[:2]
    frame[:] = (18, 42, 25) # Leaf cell green interior

    center_x, center_y = int(w * 0.55), int(h * 0.52)

    # Epidermal plant cells surrounding stoma
    for row in range(-2, 3):
        for col in range(-3, 4):
            cx = center_x + col * 90
            cy = center_y + row * 80
            if (col, row) not in [(0, 0), (0, -1), (0, 1)]:
                cv2.rectangle(frame, (cx - 40, cy - 35), (cx + 40, cy + 35), (35, 80, 45), -1)
                cv2.rectangle(frame, (cx - 40, cy - 35), (cx + 40, cy + 35), (55, 125, 70), 2, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 12, (45, 100, 60), -1) # Cell nucleus

    # Stoma Guard Cells (Pair of curved bean-shaped cells)
    opening_gap = int(18 + 10 * math.sin(t * 2.5)) # Breathing stoma aperture
    # Left Guard Cell
    cv2.ellipse(frame, (center_x - opening_gap - 25, center_y), (35, 75), 0, 0, 360, (50, 160, 80), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (center_x - opening_gap - 25, center_y), (35, 75), 0, 0, 360, (80, 220, 120), 3, cv2.LINE_AA)
    # Right Guard Cell
    cv2.ellipse(frame, (center_x + opening_gap + 25, center_y), (35, 75), 0, 0, 360, (50, 160, 80), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (center_x + opening_gap + 25, center_y), (35, 75), 0, 0, 360, (80, 220, 120), 3, cv2.LINE_AA)

    # Stoma Pore Interior (Dark opening)
    cv2.ellipse(frame, (center_x, center_y), (opening_gap, 55), 0, 0, 360, (10, 20, 15), -1, cv2.LINE_AA)

    # CO2 Molecule streams entering the pore from left air space
    for i in range(6):
        cp = (t * 0.28 + i * 0.18) % 1.0
        cx = int(80 + cp * (center_x - 80))
        cy = int(center_y - 80 + i * 30 + math.sin(t * 4.0 + i) * 12)
        # Carbon atom (Grey)
        cv2.circle(frame, (cx, cy), 9, (160, 175, 185), -1, cv2.LINE_AA)
        # Two Oxygen atoms (Red)
        cv2.circle(frame, (cx - 9, cy), 5, (80, 90, 230), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx + 9, cy), 5, (80, 90, 230), -1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Carbon Dioxide (CO2) Intake via Stomata", 3, (75, 85, 99), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(40, 110), (220, 132)], fill=(55, 65, 81))
    draw.text((48, 113), "CO2 Molecules from Air", font=font_sub, fill=(255, 255, 255))

    draw.rectangle([(center_x - 90, h - 55), (center_x + 90, h - 33)], fill=(22, 101, 52))
    draw.text((center_x - 82, h - 52), "Guard Cells Open Pore", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Stage 4: Chloroplast & Light Reaction ──
def _animate_scene_chloroplast(frame: np.ndarray, t: float) -> None:
    """Scene 4: Inside the Chloroplast organelle - Thylakoids converting solar energy."""
    h, w = frame.shape[:2]
    frame[:] = (16, 28, 22)

    cx, cy = int(w * 0.5), int(h * 0.52)

    # Chloroplast Outer & Inner Membrane (Large green oval)
    cv2.ellipse(frame, (cx, cy), (260, 150), 0, 0, 360, (25, 75, 40), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (cx, cy), (260, 150), 0, 0, 360, (50, 160, 80), 4, cv2.LINE_AA)
    cv2.ellipse(frame, (cx, cy), (248, 140), 0, 0, 360, (80, 210, 110), 2, cv2.LINE_AA)

    # Thylakoid Stacks (Grana discs)
    grana_x = [cx - 140, cx - 45, cx + 50, cx + 145]
    for gx in grana_x:
        for di in range(5):
            dy = cy - 45 + di * 22
            cv2.ellipse(frame, (gx, dy), (32, 8), 0, 0, 360, (40, 190, 85), -1, cv2.LINE_AA)
            cv2.ellipse(frame, (gx, dy), (32, 8), 0, 0, 360, (90, 240, 140), 1, cv2.LINE_AA)
            
        # Connecting stromal lamellae
        if gx < cx + 140:
            cv2.line(frame, (gx + 30, cy), (gx + 65, cy), (60, 180, 100), 2, cv2.LINE_AA)

    # Energy conversion glow (Light splitting H2O -> H+ + O2 + ATP)
    for i in range(10):
        ap = (t * 0.4 + i * 0.1) % 1.0
        ax = int(cx - 160 + ap * 320)
        ay = int(cy + math.sin(t * 5.0 + i) * 55)
        # Golden ATP energy particles
        cv2.circle(frame, (ax, ay), 4, (60, 225, 255), -1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Chemical Conversion in Chloroplasts", 4, (5, 150, 105), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(cx - 120, h - 55), (cx + 120, h - 33)], fill=(6, 95, 70))
    draw.text((cx - 110, h - 52), "Thylakoid Grana: Light Reaction", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Stage 5: Oxygen (O2) Released & Glucose (C6H12O6) Stored ──
def _animate_scene_oxygen_glucose(frame: np.ndarray, t: float) -> None:
    """Scene 5: Oxygen bubbles escaping into atmosphere and Glucose crystals stored."""
    h, w = frame.shape[:2]
    frame[:] = (22, 28, 20)

    leaf_x, leaf_y = int(w * 0.45), int(h * 0.5)

    # Central healthy leaf
    cv2.ellipse(frame, (leaf_x, leaf_y), (180, 95), 0, 0, 360, (35, 140, 65), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (leaf_x, leaf_y), (180, 95), 0, 0, 360, (75, 215, 115), 3, cv2.LINE_AA)

    # 1. Oxygen (O2) bubbles releasing into upper sky
    for i in range(8):
        op = (t * 0.32 + i * 0.125) % 1.0
        ox = int(leaf_x - 100 + i * 30 + math.sin(t * 3.5 + i) * 15)
        oy = int(leaf_y - 20 - op * 180)
        # Double Oxygen atom
        cv2.circle(frame, (ox - 6, oy), 6, (110, 240, 150), -1, cv2.LINE_AA)
        cv2.circle(frame, (ox + 6, oy), 6, (110, 240, 150), -1, cv2.LINE_AA)
        cv2.circle(frame, (ox, oy), 11, (180, 255, 200), 1, cv2.LINE_AA)

    # 2. Glucose sugar crystals (Hexagonal golden rings) transported down
    for i in range(5):
        gp = (t * 0.25 + i * 0.20) % 1.0
        gx = int(leaf_x - 80 + i * 45)
        gy = int(leaf_y + 20 + gp * 120)
        # Hexagonal sugar unit
        pts = []
        for v in range(6):
            va = 2 * math.pi * v / 6
            pts.append([int(gx + math.cos(va) * 10), int(gy + math.sin(va) * 10)])
        cv2.polylines(frame, [np.array(pts)], True, (50, 210, 255), 2, cv2.LINE_AA)
        cv2.circle(frame, (gx, gy), 4, (80, 225, 255), -1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Oxygen (O2) Release & Glucose Storage", 5, (16, 185, 129), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(50, 100), (240, 122)], fill=(5, 150, 105))
    draw.text((58, 103), "Oxygen (O2) to Atmosphere", font=font_sub, fill=(255, 255, 255))

    draw.rectangle([(leaf_x - 100, h - 55), (leaf_x + 130, h - 33)], fill=(217, 119, 6))
    draw.text((leaf_x - 90, h - 52), "Glucose (Sugar): Plant Energy", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Stage 6 / Summary: Full Master Process & Chemical Reaction ──
def _animate_photosynthesis_full_diagram(
    frame: np.ndarray,
    t: float,
) -> None:
    """
    Master summary diagram showing all 5 components working together in full harmony.
    """
    h, w = frame.shape[:2]
    
    # Atmospheric Sky & Soil Layer
    frame[:int(h * 0.76), :] = (26, 20, 15)
    frame[int(h * 0.76):, :] = (20, 32, 45)
    cv2.line(frame, (0, int(h * 0.76)), (w, int(h * 0.76)), (40, 80, 110), 2, cv2.LINE_AA)

    # 1. Sun
    sun_x, sun_y = 110, 100
    _draw_glow(frame, (sun_x, sun_y), 75, 0.28)
    cv2.circle(frame, (sun_x, sun_y), 34, (60, 210, 255), -1, cv2.LINE_AA)
    for i in range(8):
        angle = 2 * math.pi * i / 8 + t * 0.4
        x1 = int(sun_x + math.cos(angle) * 40)
        y1 = int(sun_y + math.sin(angle) * 40)
        x2 = int(sun_x + math.cos(angle) * 58)
        y2 = int(sun_y + math.sin(angle) * 58)
        cv2.line(frame, (x1, y1), (x2, y2), (80, 225, 255), 3, cv2.LINE_AA)

    # Light Photon streams
    plant_x = 427
    leaf_center = (plant_x, 240)
    for i in range(5):
        p = (t * 0.35 + i * 0.20) % 1.0
        px = int(sun_x + (leaf_center[0] - 60 - sun_x) * p)
        py = int(sun_y + (leaf_center[1] - sun_y) * p)
        cv2.circle(frame, (px, py), 4, (100, 235, 255), -1, cv2.LINE_AA)
        cv2.line(frame, (px - 8, py - 6), (px, py), (140, 240, 255), 2, cv2.LINE_AA)

    # 2. Plant Structure
    ground_y = int(h * 0.76)
    roots = [
        ((plant_x, ground_y), (plant_x - 45, ground_y + 40)),
        ((plant_x, ground_y + 15), (plant_x - 80, ground_y + 65)),
        ((plant_x, ground_y), (plant_x + 50, ground_y + 45)),
        ((plant_x, ground_y + 15), (plant_x + 85, ground_y + 70)),
        ((plant_x, ground_y), (plant_x, ground_y + 75)),
    ]
    for p1, p2 in roots:
        cv2.line(frame, p1, p2, (80, 130, 170), 3, cv2.LINE_AA)

    # Green Stem
    cv2.line(frame, (plant_x, ground_y), (plant_x, 210), (50, 160, 80), 8, cv2.LINE_AA)
    cv2.line(frame, (plant_x, ground_y), (plant_x, 210), (80, 210, 110), 3, cv2.LINE_AA)

    # Left & Right Leaves
    cv2.ellipse(frame, (plant_x - 70, 250), (65, 30), -25, 0, 360, (40, 150, 70), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (plant_x - 70, 250), (65, 30), -25, 0, 360, (70, 220, 110), 2, cv2.LINE_AA)
    cv2.line(frame, (plant_x, 265), (plant_x - 120, 230), (100, 240, 140), 2, cv2.LINE_AA)

    cv2.ellipse(frame, (plant_x + 70, 235), (65, 30), 25, 0, 360, (40, 150, 70), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (plant_x + 70, 235), (65, 30), 25, 0, 360, (70, 220, 110), 2, cv2.LINE_AA)
    cv2.line(frame, (plant_x, 250), (plant_x + 120, 215), (100, 240, 140), 2, cv2.LINE_AA)

    # Top Bud
    cv2.ellipse(frame, (plant_x, 195), (25, 40), 0, 0, 360, (60, 190, 90), -1, cv2.LINE_AA)

    # 3. Water Upward Flow
    for i in range(6):
        wp = (t * 0.28 + i * 0.16) % 1.0
        wy = int(ground_y + 60 - wp * (ground_y + 60 - 240))
        wx = int(plant_x + math.sin(t * 4 + i) * 6)
        cv2.circle(frame, (wx, wy), 5, (245, 180, 50), -1, cv2.LINE_AA)

    # 4. CO2 Inflow
    for i in range(4):
        cp = (t * 0.22 + i * 0.25) % 1.0
        cx = int(80 + cp * (plant_x - 90 - 80))
        cy = int(220 + i * 25 + math.sin(t * 3 + i) * 8)
        cv2.circle(frame, (cx, cy), 7, (180, 190, 200), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx - 7, cy), 3, (100, 110, 240), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx + 7, cy), 3, (100, 110, 240), -1, cv2.LINE_AA)

    # 5. Oxygen Emission
    for i in range(5):
        op = (t * 0.30 + i * 0.20) % 1.0
        ox = int(plant_x + 90 + op * 240)
        oy = int(220 - op * 130 + math.sin(t * 4 + i) * 12)
        cv2.circle(frame, (ox - 5, oy), 5, (100, 240, 140), -1, cv2.LINE_AA)
        cv2.circle(frame, (ox + 5, oy), 5, (100, 240, 140), -1, cv2.LINE_AA)

    # Clean Badges (ASCII-safe text, zero broken glyphs)
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    font_lbl = _get_font(12, is_bold=True)

    draw.rectangle([(50, 150), (200, 172)], fill=(217, 119, 6))
    draw.text((58, 153), "[Sunlight] Light Energy", font=font_lbl, fill=(255, 255, 255))

    draw.rectangle([(60, 310), (220, 332)], fill=(75, 85, 99))
    draw.text((68, 313), "[CO2] Carbon Dioxide", font=font_lbl, fill=(255, 255, 255))

    draw.rectangle([(plant_x - 170, ground_y + 25), (plant_x - 15, ground_y + 47)], fill=(37, 99, 235))
    draw.text((plant_x - 162, ground_y + 28), "[H2O] Water from Roots", font=font_lbl, fill=(255, 255, 255))

    draw.rectangle([(w - 230, 130), (w - 60, 152)], fill=(16, 185, 129))
    draw.text((w - 222, 133), "[O2] Oxygen Released", font=font_lbl, fill=(255, 255, 255))

    draw.rectangle([(plant_x + 130, 260), (plant_x + 310, 282)], fill=(217, 140, 40))
    draw.text((plant_x + 138, 263), "[C6H12O6] Glucose Stored", font=font_lbl, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Blockchain Stage 1: Decentralized Peer-to-Peer Network ──
def _animate_blockchain_network(frame: np.ndarray, t: float) -> None:
    """Animate a glowing distributed P2P blockchain network with verified data packets and chain track."""
    h, w = frame.shape[:2]
    frame[:] = (18, 20, 32)

    # Grid lines
    for gx in range(0, w, 40):
        cv2.line(frame, (gx, 0), (gx, h), (26, 30, 48), 1)
    for gy in range(0, h, 40):
        cv2.line(frame, (0, gy), (w, gy), (26, 30, 48), 1)

    # Distributed peer nodes
    nodes = [
        (int(w * 0.16), int(h * 0.32)),
        (int(w * 0.36), int(h * 0.22)),
        (int(w * 0.64), int(h * 0.24)),
        (int(w * 0.84), int(h * 0.36)),
        (int(w * 0.28), int(h * 0.58)),
        (int(w * 0.72), int(h * 0.60)),
        (int(w * 0.50), int(h * 0.42)),
    ]

    connections = [
        (0, 1), (1, 2), (2, 3), (0, 4), (4, 6), (6, 5), (5, 3), (1, 6), (2, 6), (4, 5), (1, 4), (2, 5)
    ]

    # Draw connection channels
    for i, j in connections:
        p1 = nodes[i]
        p2 = nodes[j]
        cv2.line(frame, p1, p2, (60, 80, 120), 1, cv2.LINE_AA)

        pkt_prog = (t * 0.55 + (i * 3 + j * 7) * 0.1) % 1.0
        pkt_x = int(p1[0] + (p2[0] - p1[0]) * pkt_prog)
        pkt_y = int(p1[1] + (p2[1] - p1[1]) * pkt_prog)
        cv2.circle(frame, (pkt_x, pkt_y), 4, (255, 210, 80), -1, cv2.LINE_AA)

    # Draw glowing nodes
    for idx, (nx, ny) in enumerate(nodes):
        pulse = 1.0 + 0.18 * math.sin(t * 3.5 + idx)
        rad = int(12 * pulse)
        _draw_glow(frame, (nx, ny), int(rad * 2.5), 0.3)
        cv2.circle(frame, (nx, ny), rad, (240, 160, 40), 2, cv2.LINE_AA)
        cv2.circle(frame, (nx, ny), max(3, rad - 4), (255, 200, 70), -1, cv2.LINE_AA)
        cv2.circle(frame, (nx, ny), 3, (255, 255, 255), -1, cv2.LINE_AA)

    # Linked Block sequence along the bottom
    block_w, block_h = 100, 44
    start_bx = int(w * 0.12)
    by = int(h * 0.78)

    for b in range(4):
        bx = start_bx + b * 135
        if b > 0:
            cv2.line(frame, (bx - 32, by + block_h // 2), (bx - 4, by + block_h // 2), (0, 215, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, (bx - 4, by + block_h // 2), 4, (0, 255, 255), -1, cv2.LINE_AA)

        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + block_w, by + block_h), (20, 32, 55), -1)
        cv2.rectangle(overlay, (bx, by), (bx + block_w, by + block_h), (0, 190, 250), 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, dst=frame)

        cv2.putText(frame, f"BLOCK #{b+1}", (bx + 8, by + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "Tx: 14 | Hash OK", (bx + 8, by + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (120, 230, 255), 1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Decentralized Peer-to-Peer Network", 1, (14, 116, 144), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(28, int(h * 0.71)), (220, int(h * 0.71) + 22)], fill=(3, 105, 161))
    draw.text((36, int(h * 0.71) + 3), "Synchronized Shared Ledger", font=font_sub, fill=(255, 255, 255))

    draw.rectangle([(w - 240, int(h * 0.71)), (w - 28, int(h * 0.71) + 22)], fill=(180, 83, 9))
    draw.text((w - 232, int(h * 0.71) + 3), "No Central Bank / Intermediary", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Blockchain Stage 2: Cryptographic Blocks & SHA-256 Chaining ──
def _animate_blockchain_blocks(frame: np.ndarray, t: float) -> None:
    """Animate detailed cryptographic blocks linked by SHA-256 hash pointers."""
    h, w = frame.shape[:2]
    frame[:] = (16, 20, 30)

    for gy in range(0, h, 30):
        cv2.line(frame, (0, gy), (w, gy), (24, 28, 42), 1)

    block_data = [
        {"num": "BLOCK #48", "prev": "0000a12f...", "data": "Alice -> Bob (1.5 BTC)", "nonce": "84920", "hash": "00003b8e..."},
        {"num": "BLOCK #49", "prev": "00003b8e...", "data": "Carol -> Dave (4.0 BTC)", "nonce": "19403", "hash": "00007f1a..."},
        {"num": "BLOCK #50", "prev": "00007f1a...", "data": "Eve -> Frank (0.8 BTC)", "nonce": "62914", "hash": "0000c94d..."},
    ]

    bw, bh = 220, 240
    spacing = 45
    start_x = int((w - (3 * bw + 2 * spacing)) / 2)
    by = int(h * 0.26)

    for idx, b in enumerate(block_data):
        bx = start_x + idx * (bw + spacing)

        # Connecting cryptographic pointer arrow
        if idx > 0:
            arrow_x1 = bx - spacing + 2
            arrow_x2 = bx - 2
            arrow_y = by + int(bh * 0.42)
            cv2.line(frame, (arrow_x1, arrow_y), (arrow_x2, arrow_y), (0, 220, 255), 3, cv2.LINE_AA)
            cv2.line(frame, (arrow_x2 - 10, arrow_y - 6), (arrow_x2, arrow_y), (0, 220, 255), 3, cv2.LINE_AA)
            cv2.line(frame, (arrow_x2 - 10, arrow_y + 6), (arrow_x2, arrow_y), (0, 220, 255), 3, cv2.LINE_AA)
            ap = (t * 0.8 + idx * 0.4) % 1.0
            dot_px = int(arrow_x1 + (arrow_x2 - arrow_x1) * ap)
            cv2.circle(frame, (dot_px, arrow_y), 5, (255, 230, 100), -1, cv2.LINE_AA)

        # Block Card Box
        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (22, 28, 48), -1)
        border_glow = int(180 + 75 * math.sin(t * 3.0 + idx))
        cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (0, border_glow, 255), 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.90, frame, 0.10, 0, dst=frame)

        # Header banner
        cv2.rectangle(frame, (bx, by), (bx + bw, by + 32), (15, 65, 110), -1)
        cv2.putText(frame, b["num"], (bx + 14, by + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        fields = [
            ("Prev Hash:", b["prev"], (100, 200, 255)),
            ("Tx Data:", b["data"], (240, 240, 240)),
            ("Nonce:", b["nonce"], (255, 200, 80)),
            ("SHA-256:", b["hash"], (100, 255, 180)),
        ]
        fy = by + 56
        for lbl, val, val_col in fields:
            cv2.putText(frame, lbl, (bx + 10, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 180, 200), 1, cv2.LINE_AA)
            fy += 16
            cv2.putText(frame, val, (bx + 10, fy), cv2.FONT_HERSHEY_SIMPLEX, 0.42, val_col, 1, cv2.LINE_AA)
            fy += 26

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Cryptographic Hash & Chain Immutability", 2, (180, 83, 9), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(int(w * 0.15), h - 48), (int(w * 0.85), h - 22)], fill=(22, 101, 52))
    draw.text((int(w * 0.18), h - 45), "[Tamper-Proof] Changing 1 byte alters Hash and breaks every linked block", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Blockchain Stage 3: Mining, Proof of Work & Consensus ──
def _animate_blockchain_mining(frame: np.ndarray, t: float) -> None:
    """Animate miners racing to solve SHA-256 proof-of-work mathematical puzzle."""
    h, w = frame.shape[:2]
    frame[:] = (18, 22, 34)

    for gx in range(0, w, 45):
        cv2.line(frame, (gx, 0), (gx, h), (26, 32, 50), 1)

    target_box_w = 460
    target_x = (w - target_box_w) // 2
    cv2.rectangle(frame, (target_x, 65), (target_x + target_box_w, 108), (28, 40, 68), -1)
    cv2.rectangle(frame, (target_x, 65), (target_x + target_box_w, 108), (0, 200, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "DIFFICULTY TARGET:  0000 0000 0000 FFFF...", (target_x + 16, 94), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 240, 255), 1, cv2.LINE_AA)

    miners = [
        {"name": "Miner Node #1 (USA)", "speed": "120 TH/s", "x": int(w * 0.18), "winner": False},
        {"name": "Miner Node #2 (Germany)", "speed": "145 TH/s", "x": int(w * 0.50), "winner": True},
        {"name": "Miner Node #3 (Japan)", "speed": "110 TH/s", "x": int(w * 0.82), "winner": False},
    ]

    card_w = 210
    card_h = 220
    card_y = 135

    for idx, miner in enumerate(miners):
        mx = miner["x"] - card_w // 2

        nonce_val = int((t * 2400 + idx * 8317) % 999999)
        hash_val = f"{(nonce_val * 73819) % 0xFFFFFF:06x}a84..."

        is_winner = miner["winner"] and (int(t * 1.5) % 2 == 1)

        overlay = frame.copy()
        cv2.rectangle(overlay, (mx, card_y), (mx + card_w, card_y + card_h), (24, 32, 54), -1)
        border_col = (50, 220, 100) if is_winner else (60, 90, 140)
        cv2.rectangle(overlay, (mx, card_y), (mx + card_w, card_y + card_h), border_col, 2, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.90, frame, 0.10, 0, dst=frame)

        cv2.putText(frame, miner["name"], (mx + 10, card_y + 26), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Hashrate: {miner['speed']}", (mx + 10, card_y + 48), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (120, 210, 255), 1, cv2.LINE_AA)

        cx, cy = mx + card_w // 2, card_y + 95
        rot_angle = t * 6.0 + idx * 2.0
        cv2.circle(frame, (cx, cy), 22, (40, 70, 110), 2, cv2.LINE_AA)
        for g in range(4):
            ga = rot_angle + g * math.pi / 2
            gx1 = int(cx + math.cos(ga) * 14)
            gy1 = int(cy + math.sin(ga) * 14)
            gx2 = int(cx + math.cos(ga) * 25)
            gy2 = int(cy + math.sin(ga) * 25)
            cv2.line(frame, (gx1, gy1), (gx2, gy2), (0, 200, 255), 2, cv2.LINE_AA)

        cv2.putText(frame, f"Nonce: {nonce_val:06d}", (mx + 12, card_y + 150), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 210, 80), 1, cv2.LINE_AA)

        if is_winner:
            cv2.putText(frame, "STATUS: BLOCK SOLVED!", (mx + 12, card_y + 180), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (80, 255, 120), 1, cv2.LINE_AA)
            cv2.putText(frame, "Reward: 3.125 BTC", (mx + 12, card_y + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 215, 0), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, f"Hash: 00{hash_val}", (mx + 12, card_y + 180), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 180, 200), 1, cv2.LINE_AA)
            cv2.putText(frame, "Searching Nonce...", (mx + 12, card_y + 200), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 140, 170), 1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Proof of Work & Mining Consensus", 3, (22, 101, 52), w)

    font_sub = _get_font(12, is_bold=True)
    draw.rectangle([(int(w * 0.18), h - 45), (int(w * 0.82), h - 22)], fill=(120, 53, 15))
    draw.text((int(w * 0.20), h - 42), "[Consensus] First node to find valid Nonce earns block reward & consensus", font=font_sub, fill=(255, 255, 255))

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


# ── Blockchain Stage 4: Smart Contracts & Programmable Trust ──
def _animate_blockchain_smart_contracts(frame: np.ndarray, t: float) -> None:
    """Animate self-executing smart contracts with automated condition verification."""
    h, w = frame.shape[:2]
    frame[:] = (16, 22, 32)

    ed_x, ed_y = int(w * 0.08), int(h * 0.18)
    ed_w, ed_h = int(w * 0.48), int(h * 0.70)

    overlay = frame.copy()
    cv2.rectangle(overlay, (ed_x, ed_y), (ed_x + ed_w, ed_y + ed_h), (20, 26, 42), -1)
    cv2.rectangle(overlay, (ed_x, ed_y), (ed_x + ed_w, ed_y + ed_h), (0, 160, 220), 2, cv2.LINE_AA)
    cv2.rectangle(overlay, (ed_x, ed_y), (ed_x + ed_w, ed_y + 30), (30, 40, 65), -1)
    cv2.addWeighted(overlay, 0.90, frame, 0.10, 0, dst=frame)

    cv2.circle(frame, (ed_x + 16, ed_y + 15), 5, (80, 80, 240), -1, cv2.LINE_AA)
    cv2.circle(frame, (ed_x + 32, ed_y + 15), 5, (80, 210, 240), -1, cv2.LINE_AA)
    cv2.circle(frame, (ed_x + 48, ed_y + 15), 5, (80, 240, 120), -1, cv2.LINE_AA)
    cv2.putText(frame, "SmartContract.sol (Solidity)", (ed_x + 70, ed_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 220, 245), 1, cv2.LINE_AA)

    code_lines = [
        ("// Decentralized Escrow Agreement", (120, 140, 160)),
        ("contract EscrowAgreement {", (100, 200, 255)),
        ("    address public buyer;", (220, 230, 245)),
        ("    address public seller;", (220, 230, 245)),
        ("    ", (255, 255, 255)),
        ("    function executeTransfer() public {", (100, 200, 255)),
        ("        if (buyer.sentFunds == true) {", (255, 200, 80)),
        ("            transferAsset(buyer);", (120, 255, 160)),
        ("            releasePayment(seller);", (120, 255, 160)),
        ("        }", (255, 200, 80)),
        ("    }", (100, 200, 255)),
        ("}", (100, 200, 255)),
    ]

    ly = ed_y + 55
    for line_text, col in code_lines:
        cv2.putText(frame, line_text, (ed_x + 18, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1, cv2.LINE_AA)
        ly += 18

    flow_x = int(w * 0.62)
    flow_y = int(h * 0.22)
    flow_w = int(w * 0.30)

    steps = [
        ("1. Buyer deposits ETH", True),
        ("2. Condition Verified", True),
        ("3. Digital Asset Delivered", True),
        ("4. Escrow Released", (int(t * 1.5) % 2 == 1)),
    ]

    for s_idx, (s_text, active) in enumerate(steps):
        sy = flow_y + s_idx * 65
        cv2.rectangle(frame, (flow_x, sy), (flow_x + flow_w, sy + 44), (25, 35, 60), -1)
        check_col = (80, 240, 120) if active else (100, 110, 130)
        cv2.rectangle(frame, (flow_x, sy), (flow_x + flow_w, sy + 44), check_col, 2, cv2.LINE_AA)
        cv2.putText(frame, "[OK]" if active else "[..]", (flow_x + 12, sy + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, check_col, 2, cv2.LINE_AA)
        cv2.putText(frame, s_text, (flow_x + 55, sy + 27), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (230, 240, 255), 1, cv2.LINE_AA)

        if s_idx < 3:
            cv2.line(frame, (flow_x + flow_w // 2, sy + 44), (flow_x + flow_w // 2, sy + 65), (0, 180, 230), 2, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Smart Contracts & Automated Trust", 4, (124, 58, 237), w)

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _animate_circuits_energy(
    frame: np.ndarray,
    t: float,
) -> None:
    """Animate glowing electric current and circuit traces across the screen."""
    h, w = frame.shape[:2]
    frame[:] = (16, 20, 32)

    paths = [
        [(int(w*0.1), int(h*0.3)), (int(w*0.35), int(h*0.3)), (int(w*0.45), int(h*0.5)), (int(w*0.85), int(h*0.5))],
        [(int(w*0.15), int(h*0.7)), (int(w*0.5), int(h*0.7)), (int(w*0.6), int(h*0.4)), (int(w*0.9), int(h*0.4))],
        [(int(w*0.4), int(h*0.15)), (int(w*0.4), int(h*0.45)), (int(w*0.7), int(h*0.45)), (int(w*0.7), int(h*0.85))],
    ]

    for path in paths:
        for k in range(len(path) - 1):
            cv2.line(frame, path[k], path[k+1], (60, 80, 130), 2, cv2.LINE_AA)

        for p_idx in range(3):
            prog = (t * 0.4 + p_idx * 0.33) % 1.0
            seg = int(prog * (len(path) - 1))
            sub_p = (prog * (len(path) - 1)) - seg
            p1 = path[seg]
            p2 = path[min(seg + 1, len(path) - 1)]

            ex = int(p1[0] + (p2[0] - p1[0]) * sub_p)
            ey = int(p1[1] + (p2[1] - p1[1]) * sub_p)

            cv2.circle(frame, (ex, ey), 5, (255, 230, 100), -1, cv2.LINE_AA)
            cv2.circle(frame, (ex, ey), 9, (255, 180, 50), 1, cv2.LINE_AA)

    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    _draw_stage_badge(draw, "Computer Science & Digital Circuits", 1, (30, 64, 175), w)
    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)



def _animate_dna_double_helix(
    frame: np.ndarray,
    t: float,
) -> None:
    """Animate a 3D rotating DNA double helix on the right side."""
    h, w = frame.shape[:2]
    center_x = int(w * 0.78)
    
    num_rungs = 14
    spacing = 24
    start_y = int(h * 0.15)
    
    for r in range(num_rungs):
        ry = start_y + r * spacing
        angle = t * 2.5 + r * 0.45
        
        offset = int(math.sin(angle) * 45)
        depth = math.cos(angle) # -1 to 1 for z-index
        
        x1 = center_x + offset
        x2 = center_x - offset
        
        # Rung connecting strand
        rung_color = (180, 140, 60) if depth > 0 else (100, 80, 35)
        cv2.line(frame, (x1, ry), (x2, ry), rung_color, 1, cv2.LINE_AA)
        
        # Strand 1 node
        rad1 = 5 if depth > 0 else 3
        cv2.circle(frame, (x1, ry), rad1, (60, 220, 255) if depth > 0 else (30, 120, 150), -1, cv2.LINE_AA)
        
        # Strand 2 node
        rad2 = 5 if depth <= 0 else 3
        cv2.circle(frame, (x2, ry), rad2, (255, 110, 180) if depth <= 0 else (140, 50, 90), -1, cv2.LINE_AA)


def _animate_space_orbits(
    frame: np.ndarray,
    t: float,
) -> None:
    """Animate orbital paths and revolving celestial bodies with cosmic dust."""
    h, w = frame.shape[:2]
    sun_x, sun_y = int(w * 0.5), int(h * 0.48)
    
    # Glowing central body
    _draw_glow(frame, (sun_x, sun_y), 65, 0.25)
    cv2.circle(frame, (sun_x, sun_y), 24, (80, 200, 255), -1, cv2.LINE_AA)
    
    # 2 Orbiting bodies
    orbits = [(120, 50, 0.8, (230, 180, 80), 8), (220, 90, 0.45, (100, 210, 240), 12)]
    
    for a, b, speed, col, sz in orbits:
        # Draw orbit ellipse
        cv2.ellipse(frame, (sun_x, sun_y), (a, b), -15, 0, 360, (70, 90, 110), 1, cv2.LINE_AA)
        
        # Orbit position
        angle = t * speed
        px = int(sun_x + math.cos(angle) * a)
        py = int(sun_y + math.sin(angle) * b)
        
        cv2.circle(frame, (px, py), sz, col, -1, cv2.LINE_AA)
        cv2.circle(frame, (px, py), sz + 3, (255, 255, 255), 1, cv2.LINE_AA)


def _animate_hud_overlay(
    frame: np.ndarray,
    t: float,
) -> None:
    """Add modern cinematic science documentary HUD corner markers and grid lines."""
    h, w = frame.shape[:2]

    color = (80, 160, 220)
    # Corner brackets
    # Top-Left
    cv2.line(frame, (25, 25), (65, 25), color, 1, cv2.LINE_AA)
    cv2.line(frame, (25, 25), (25, 65), color, 1, cv2.LINE_AA)
    # Top-Right
    cv2.line(frame, (w - 25, 25), (w - 65, 25), color, 1, cv2.LINE_AA)
    cv2.line(frame, (w - 25, 25), (w - 25, 65), color, 1, cv2.LINE_AA)
    # Bottom-Left
    cv2.line(frame, (25, h - 25), (65, h - 25), color, 1, cv2.LINE_AA)
    cv2.line(frame, (25, h - 25), (25, h - 65), color, 1, cv2.LINE_AA)
    # Bottom-Right
    cv2.line(frame, (w - 25, h - 25), (w - 65, h - 25), color, 1, cv2.LINE_AA)
    cv2.line(frame, (w - 25, h - 25), (w - 25, h - 65), color, 1, cv2.LINE_AA)

    # Subtle pulsing recording dot
    if int(t * 2) % 2 == 0:
        cv2.circle(frame, (w - 45, 45), 4, (60, 70, 235), -1, cv2.LINE_AA)

def _get_font(size: int = 14, is_bold: bool = False, text: str = "", lang_code: str = "en"):
    """
    Get a high quality Unicode font supporting English, Urdu, Arabic, Hindi,
    Marathi, Tamil, Telugu, Kannada, Malayalam, Bengali, Gujarati, Japanese, etc.
    """
    text_sample = str(text or "")

    # 1. Arabic / Urdu detection
    is_arabic_urdu = bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", text_sample)) or lang_code.lower() in ("ur", "ar", "fa", "he", "urdu", "arabic")

    # 2. Devanagari (Hindi, Marathi, Sanskrit)
    is_devanagari = bool(re.search(r"[\u0900-\u097F]", text_sample)) or lang_code.lower() in ("hi", "mr", "hindi", "marathi")

    # 3. Kannada
    is_kannada = bool(re.search(r"[\u0C80-\u0CFF]", text_sample)) or lang_code.lower() in ("kn", "kannada")

    # 4. Tamil
    is_tamil = bool(re.search(r"[\u0B80-\u0BFF]", text_sample)) or lang_code.lower() in ("ta", "tamil")

    # 5. Telugu
    is_telugu = bool(re.search(r"[\u0C00-\u0C7F]", text_sample)) or lang_code.lower() in ("te", "telugu")

    # 6. Malayalam
    is_malayalam = bool(re.search(r"[\u0D00-\u0D7F]", text_sample)) or lang_code.lower() in ("ml", "malayalam")

    # 7. Bengali / Assamese
    is_bengali = bool(re.search(r"[\u0980-\u09FF]", text_sample)) or lang_code.lower() in ("bn", "as", "bengali")

    # 8. Gujarati
    is_gujarati = bool(re.search(r"[\u0A80-\u0AFF]", text_sample)) or lang_code.lower() in ("gu", "gujarati")

    # 9. East Asian (Japanese, Chinese, Korean)
    is_east_asian = bool(re.search(r"[\u3000-\u9FFF\uAC00-\uD7AF]", text_sample)) or lang_code.lower() in ("ja", "zh", "ko", "japanese", "chinese")

    assets_dir = Path(__file__).resolve().parent.parent / "assets"

    candidates: list[str] = []
    if is_arabic_urdu:
        candidates += [
            str(assets_dir / "NotoSansArabic-Regular.ttf"),
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
    elif is_devanagari:
        candidates += [
            str(assets_dir / "NotoSansDevanagari-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
            "C:/Windows/Fonts/mangal.ttf",
        ]
    elif is_kannada:
        candidates += [
            str(assets_dir / "NotoSansKannada-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
        ]
    elif is_tamil:
        candidates += [
            str(assets_dir / "NotoSansTamil-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
        ]
    elif is_telugu:
        candidates += [
            str(assets_dir / "NotoSansTelugu-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
        ]
    elif is_malayalam:
        candidates += [
            str(assets_dir / "NotoSansMalayalam-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
        ]
    elif is_bengali:
        candidates += [
            str(assets_dir / "NotoSansBengali-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
        ]
    elif is_gujarati:
        candidates += [
            str(assets_dir / "NotoSansGujarati-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
        ]
    elif is_east_asian:
        candidates += [
            str(assets_dir / "NotoSansJP-Regular.ttf"),
            "C:/Windows/Fonts/meiryo.ttc",
            "C:/Windows/Fonts/msmincho.ttc",
        ]
    else:
        candidates += [
            str(assets_dir / "NotoSans-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttc",
            "C:/Windows/Fonts/arialbd.ttf" if is_bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "arial.ttf",
        ]

    # Global fallbacks
    candidates += [
        str(assets_dir / "NotoSans-Regular.ttf"),
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "arial.ttf",
    ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=0)
            except Exception:
                pass
    return ImageFont.load_default()


def _render_documentary_slide(
    bg_frame: np.ndarray,
    image: Optional[np.ndarray],
    t: float,
    title: str,
    narration: str,
    zoom: float = 1.0,
    lang_code: str = "en",
) -> np.ndarray:
    """
    Renders an elegant educational slide for history/biography/geography:
    - Dark presentation canvas with structured educational text on the left.
    - Authentic framed portrait / map / document image on the right.
    - Zero science formulas or circuit lines.
    - Full multilingual font rendering for Urdu, Arabic, Hindi, Tamil, Kannada, etc.
    """
    h, w = bg_frame.shape[:2]
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (20, 24, 36)

    # Subtle ambient background grid lines
    for y in range(0, h, 24):
        cv2.line(canvas, (0, y), (w, y), (28, 34, 48), 1)

    # ── 1. Embed the Authentic Photo on the Right ──
    img_x1, img_y1 = int(w * 0.52), int(h * 0.10)
    img_w, img_h = int(w * 0.44), int(h * 0.72)
    img_x2, img_y2 = img_x1 + img_w, img_y1 + img_h

    if image is not None:
        try:
            ih, iw = image.shape[:2]
            crop_zoom = min(1.08, max(1.0, zoom))
            scale = max(img_w / iw, img_h / ih) * crop_zoom
            new_w = max(img_w, int(math.ceil(iw * scale)))
            new_h = max(img_h, int(math.ceil(ih * scale)))
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            rh, rw = resized.shape[:2]
            start_y = max(0, (rh - img_h) // 2)
            start_x = max(0, (rw - img_w) // 2)
            cropped = resized[start_y:start_y + img_h, start_x:start_x + img_w]
            # Ensure exact pixel dimension match
            if cropped.shape[0] != img_h or cropped.shape[1] != img_w:
                cropped = cv2.resize(cropped, (img_w, img_h))

            # Place cropped image into the frame
            canvas[img_y1:img_y2, img_x1:img_x2] = cropped
        except Exception as img_err:
            image = None

    # Elegant golden/cyan card border around image
    cv2.rectangle(canvas, (img_x1, img_y1), (img_x2, img_y2), (40, 160, 230), 2, cv2.LINE_AA)

    # If no image: fill with a rich dark gradient panel instead of empty grid
    if image is None:
        panel = canvas[img_y1:img_y2, img_x1:img_x2].copy()
        for py in range(img_h):
            t_grad = py / max(1, img_h - 1)
            r = int(15 + 20 * t_grad)
            g = int(30 + 40 * t_grad)
            b = int(50 + 60 * t_grad)
            panel[py, :] = (b, g, r)  # BGR
        # Decorative diagonal lines
        for d in range(-img_h, img_w, 30):
            cv2.line(panel, (max(0, d), 0), (min(img_w, d + img_h), min(img_h, img_h)), (30, 60, 90), 1)
        # Decorative circle
        cv2.circle(panel, (img_w // 2, img_h // 2), min(img_w, img_h) // 3, (40, 100, 160), 2)
        cv2.circle(panel, (img_w // 2, img_h // 2), min(img_w, img_h) // 5, (50, 130, 200), 2)
        canvas[img_y1:img_y2, img_x1:img_x2] = panel
        cv2.rectangle(canvas, (img_x1, img_y1), (img_x2, img_y2), (40, 160, 230), 2, cv2.LINE_AA)

    # ── 2. Render Text Content on the Left ──
    pil_img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)

    disp_title = (title or "Historical Overview").strip()

    # Dynamic language-appropriate fonts
    font_title = _get_font(20, is_bold=True, text=disp_title, lang_code=lang_code)
    font_body  = _get_font(13, is_bold=False, text=narration, lang_code=lang_code)
    # Badge is always English text — use a clean Latin font to avoid Indic font tofu boxes
    font_badge = _get_font(11, is_bold=True, text="HISTORICAL CONTEXT", lang_code="en")

    # Historical Year / Period Detection
    full_text = f"{title} {narration}"
    year_match = re.search(r"\b(1[0-9]{3}|20[0-2][0-9]|[0-9]{1,2}(?:th|st|nd|rd)\s+century|[0-9]{3,4}\s*(?:BCE|CE|BC|AD))\b", full_text, re.IGNORECASE)
    badge_text = ""
    if year_match:
        badge_text = f"YEAR: {year_match.group(1).upper()}"
    elif any(k in full_text.lower() for k in ("shivaji", "maratha", "mughal", "shahaji")):
        badge_text = "PERIOD: 17TH CENTURY"
    elif "world war" in full_text.lower():
        badge_text = "TIMELINE: 1939 – 1945"
    elif any(k in full_text.lower() for k in ("tipu", "mysore", "hyder")):
        badge_text = "PERIOD: 18TH CENTURY (1782–1799)"
    elif any(k in full_text.lower() for k in ("ashoka", "maurya", "ashok", "اشوک", "अशोक")):
        badge_text = "PERIOD: 3RD CENTURY BCE"
    else:
        badge_text = "HISTORICAL CONTEXT"

    # Year Badge Box
    bbox_badge = draw.textbbox((0, 0), badge_text, font=font_badge)
    badge_w = bbox_badge[2] - bbox_badge[0]
    draw.rectangle([(28, int(h * 0.10)), (28 + badge_w + 18, int(h * 0.10) + 22)], fill=(217, 119, 6))
    draw.text((36, int(h * 0.10) + 3), badge_text, font=font_badge, fill=(255, 255, 255))

    # Scene Title — word-wrap constrained to left panel width so Marathi/Urdu never bleeds into image panel
    max_title_w = int(w * 0.46) - 36
    title_y = int(h * 0.18)
    title_words = disp_title.split()
    title_line = ""
    for tw in title_words:
        test = f"{title_line} {tw}".strip()
        tbbox = draw.textbbox((0, 0), test, font=font_title)
        if (tbbox[2] - tbbox[0]) > max_title_w and title_line:
            draw.text((28, title_y), title_line, font=font_title, fill=(255, 255, 255))
            title_y += 26
            title_line = tw
        else:
            title_line = test
    if title_line:
        draw.text((28, title_y), title_line, font=font_title, fill=(255, 255, 255))

    # Gold Accent Line
    draw.line([(28, int(h * 0.25)), (int(w * 0.48), int(h * 0.25))], fill=(217, 140, 40), width=2)

    # Bullet points from narration (splitting by English '.', Urdu '۔', Hindi '।', newlines, etc.)
    sentences = [s.strip() for s in re.split(r"[.۔।!?\n]+", str(narration or "")) if len(s.strip()) > 6]
    if not sentences and narration:
        sentences = [narration.strip()]

    cur_y = int(h * 0.28)
    max_text_w = int(w * 0.44) - 20

    for s in sentences[:3]:
        # Bullet dot
        draw.ellipse([(28, cur_y + 4), (34, cur_y + 10)], fill=(217, 119, 6))

        # Dynamic word wrapping based on pixel width instead of arbitrary word counts
        words = s.split()
        lines: list[str] = []
        cur_line = ""
        for word in words:
            test_line = f"{cur_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test_line, font=font_body)
            if (bbox[2] - bbox[0]) > max_text_w and cur_line:
                lines.append(cur_line)
                cur_line = word
            else:
                cur_line = test_line
        if cur_line:
            lines.append(cur_line)

        for line_idx, line_str in enumerate(lines[:2]):
            if line_idx == 1 and len(lines) > 2:
                line_str += "..."
            text_fill = (240, 245, 255) if line_idx == 0 else (200, 215, 235)
            draw.text((42, cur_y), line_str, font=font_body, fill=text_fill)
            cur_y += 20
        cur_y += 8

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def _animate_equation_overlay(
    frame: np.ndarray,
    t: float,
    equation: str,
    duration: float,
) -> None:
    """Draw a clean, glowing educational formula overlay banner."""
    if not equation or not str(equation).strip():
        return

    eq_text = str(equation).strip()
    sub_map = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
    eq_text = eq_text.translate(sub_map)
    eq_text = eq_text.replace("->", " → ").replace("-->", " → ")

    h, w = frame.shape[:2]

    # Smooth fade-in over 1 second
    fade_in = min(1.0, max(0.0, t / 0.9))
    if fade_in <= 0.05:
        return

    box_w = min(w - 40, max(360, len(eq_text) * 15 + 48))
    box_h = 58
    box_x = (w - box_w) // 2
    box_y = 48

    # Glassmorphic rounded background
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (box_x, box_y),
        (box_x + box_w, box_y + box_h),
        (15, 20, 32),
        -1,
    )
    # Glowing border
    glow_pulse = 0.5 + 0.5 * math.sin(t * 3.0)
    border_color = (
        int(60 + 60 * glow_pulse),
        int(180 + 50 * glow_pulse),
        int(240 + 15 * glow_pulse),
    )
    cv2.rectangle(
        overlay,
        (box_x, box_y),
        (box_x + box_w, box_y + box_h),
        border_color,
        2,
        cv2.LINE_AA,
    )

    alpha = 0.84 * fade_in
    cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, dst=frame)

    # Render clean typography using PIL
    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_img)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), eq_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    tx = box_x + (box_w - text_w) // 2
    ty = box_y + (box_h - text_h) // 2 - 2

    draw.text((tx, ty), eq_text, font=font, fill=(255, 255, 255))
    frame[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


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
    equation: Optional[str] = None,
    title: Optional[str] = None,
    narration: Optional[str] = None,
    lang_code: str = "en",
) -> str:
    """
    Render an animated educational scene from a background image.

    motion options:
        documentary / narrative / biography / history / geography (clean split-screen presentation)
        plant_sunlight
        water
        co2
        blockchain
        circuits
        dna
        space
        gentle_zoom
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

    motion_name = (
        motion or "documentary"
    ).lower()

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

        # ── 1. Documentary / History / Biography Presentation (Split Educational Slide + Framed Image) ──
        if motion_name in ("documentary", "narrative", "biography", "history", "geography", "map", "culture", "person"):
            frame = _render_documentary_slide(
                frame,
                image,
                t,
                title=str(title or ""),
                narration=str(narration or ""),
                zoom=zoom,
                lang_code=lang_code,
            )

        # ── 2. Specialized Photosynthesis & Biology Stage Modes ──
        elif motion_name in ("plant_sunlight", "photo_sunlight", "sunlight", "light_energy", "photons"):
            _animate_scene_sunlight(frame, t)

        elif motion_name in ("photo_roots", "photo_water", "roots", "water_uptake", "xylem"):
            _animate_scene_roots_water(frame, t)

        elif motion_name in ("photo_stomata", "photo_co2", "stomata", "carbon_dioxide", "guard_cells"):
            _animate_scene_stomata_co2(frame, t)

        elif motion_name in ("photo_chloroplast", "chloroplast", "chlorophyll", "thylakoid", "light_reaction"):
            _animate_scene_chloroplast(frame, t)

        elif motion_name in ("photo_oxygen", "oxygen_glucose", "photo_glucose", "glucose", "energy_storage"):
            _animate_scene_oxygen_glucose(frame, t)

        elif motion_name in ("photo_equation", "photosynthesis", "master_diagram", "botany", "plant"):
            _animate_photosynthesis_full_diagram(frame, t)

        elif motion_name in ("dna", "genetics", "biology", "cells"):
            _animate_dna_double_helix(
                frame,
                t,
            )

        elif motion_name in ("space", "orbits", "astronomy", "gravity"):
            _animate_space_orbits(
                frame,
                t,
            )

        # ── 3. Blockchain & Web3 Technologies ──
        elif motion_name in ("blockchain_network", "blockchain", "crypto", "distributed_ledger", "web3", "p2p"):
            _animate_blockchain_network(frame, t)

        elif motion_name in ("blockchain_blocks", "crypto_blocks", "hashes", "sha256", "immutability"):
            _animate_blockchain_blocks(frame, t)

        elif motion_name in ("blockchain_mining", "mining", "proof_of_work", "pow", "pos", "consensus"):
            _animate_blockchain_mining(frame, t)

        elif motion_name in ("blockchain_smart_contracts", "smart_contracts", "contracts", "dapp", "ethereum"):
            _animate_blockchain_smart_contracts(frame, t)

        # ── 4. Computer Science / Circuits ──
        elif motion_name in ("circuits", "energy", "electricity", "computer_science", "code", "cpu", "chip"):
            _animate_circuits_energy(frame, t)

        # ── 5. Educational Equation & Chemical Reaction Overlay (Only for equation scenes) ──
        active_eq = str(equation or "").strip()
        
        # Show equation overlay when specifically requested or on equation/master diagram scenes
        if motion_name in ("photo_equation", "equation"):
            if not active_eq:
                active_eq = "6CO2 + 6H2O + Sunlight  ->  C6H12O6 + 6O2"
            _animate_equation_overlay(
                frame,
                t,
                active_eq,
                duration,
            )
        elif active_eq and motion_name not in ("documentary", "narrative", "biography", "history", "geography", "map", "culture", "person"):
            _animate_equation_overlay(
                frame,
                t,
                active_eq,
                duration,
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
                "ultrafast",
                "-crf",
                "23",
                "-threads",
                "0",
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
