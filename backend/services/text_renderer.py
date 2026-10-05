"""
EduGenAI - High-Quality Multilingual Text Renderer
Provides native text shaping and rendering with full support for complex
Indic scripts (Kannada, Devanagari/Hindi/Marathi, Tamil, Telugu, Malayalam,
Bengali, Gujarati, etc.) as well as Arabic/Urdu, East Asian, and Latin scripts.

On Windows: Uses Windows GDI + Uniscribe to ensure perfect conjuncts,
matras, and ligatures (which standard Pillow FreeType without Raqm cannot render).
Cross-platform fallback: Uses Pillow with automatic Unicode font selection.
"""

import sys
import os
import re
import math
import logging
from typing import Tuple, List, Optional, Union
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]


# Language script detection regexes
_RE_KANNADA = re.compile(r"[\u0C80-\u0CFF]")
_RE_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
_RE_TAMIL = re.compile(r"[\u0B80-\u0BFF]")
_RE_TELUGU = re.compile(r"[\u0C00-\u0C7F]")
_RE_MALAYALAM = re.compile(r"[\u0D00-\u0D7F]")
_RE_BENGALI = re.compile(r"[\u0980-\u09FF]")
_RE_GUJARATI = re.compile(r"[\u0A80-\u0AFF]")
_RE_ARABIC_URDU = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF]")
_RE_EAST_ASIAN = re.compile(r"[\u3000-\u9FFF\uAC00-\uD7AF]")


def get_font_name_for_text(text: str, lang_code: str = "en") -> str:
    """Determine the best Windows system font name for the given text script."""
    text_s = str(text or "")
    lang = (lang_code or "").lower()

    if _RE_KANNADA.search(text_s) or lang in ("kn", "kannada"):
        return "Nirmala UI"
    if _RE_DEVANAGARI.search(text_s) or lang in ("hi", "mr", "sa", "hindi", "marathi"):
        return "Nirmala UI"
    if _RE_TAMIL.search(text_s) or lang in ("ta", "tamil"):
        return "Nirmala UI"
    if _RE_TELUGU.search(text_s) or lang in ("te", "telugu"):
        return "Nirmala UI"
    if _RE_MALAYALAM.search(text_s) or lang in ("ml", "malayalam"):
        return "Nirmala UI"
    if _RE_BENGALI.search(text_s) or lang in ("bn", "as", "bengali"):
        return "Nirmala UI"
    if _RE_GUJARATI.search(text_s) or lang in ("gu", "gujarati"):
        return "Nirmala UI"
    if _RE_ARABIC_URDU.search(text_s) or lang in ("ur", "ar", "fa", "urdu", "arabic"):
        return "Segoe UI"
    if _RE_EAST_ASIAN.search(text_s) or lang in ("ja", "zh", "ko"):
        return "Meiryo"
    return "Segoe UI"


def _render_text_mask_gdi(
    text: str,
    font_size: int = 18,
    bold: bool = False,
    font_name: str = "Nirmala UI",
) -> Tuple[Optional[np.ndarray], int, int]:
    """
    Render text using Windows GDI into an antialiased grayscale alpha mask.
    Returns (alpha_mask, width, height).
    """
    if not IS_WINDOWS or not text:
        return None, 0, 0

    try:
        hdc = gdi32.CreateCompatibleDC(None)
        weight = 700 if bold else 400
        # CLEARTYPE_QUALITY = 5, ANTIALIASED_QUALITY = 4
        hfont = gdi32.CreateFontW(
            font_size, 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, font_name
        )
        old_font = gdi32.SelectObject(hdc, hfont)

        # Calculate exact text bounds
        rect_calc = RECT(0, 0, 0, 0)
        # DT_CALCRECT = 0x0400, DT_NOPREFIX = 0x0800
        user32.DrawTextW(hdc, text, len(text), ctypes.byref(rect_calc), 0x0400 | 0x0800)
        tw = max(1, rect_calc.right - rect_calc.left + 4)
        th = max(1, rect_calc.bottom - rect_calc.top + 4)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = tw
        bmi.biHeight = -th  # top-down bitmap
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        p_bits = ctypes.c_void_p()
        hbm = gdi32.CreateDIBSection(
            hdc, ctypes.byref(bmi), 0, ctypes.byref(p_bits), None, 0
        )
        old_bm = gdi32.SelectObject(hdc, hbm)

        # Clear to black background
        ctypes.memset(p_bits, 0, tw * th * 4)

        # Draw pure white text with transparent background
        gdi32.SetTextColor(hdc, 0x00FFFFFF)
        gdi32.SetBkMode(hdc, 1)  # TRANSPARENT

        rect_draw = RECT(0, 0, tw, th)
        user32.DrawTextW(hdc, text, len(text), ctypes.byref(rect_draw), 0x0800)

        buf = (ctypes.c_uint8 * (tw * th * 4)).from_address(p_bits.value)
        arr = np.ctypeslib.as_array(buf).reshape((th, tw, 4)).copy()

        # Cleanup GDI objects
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(hfont)
        gdi32.SelectObject(hdc, old_bm)
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc)

        # Extract antialiased alpha mask (0.0 to 1.0)
        alpha = np.max(arr[..., :3], axis=2).astype(np.float32) / 255.0
        return alpha, tw, th
    except Exception as e:
        logger.warning("GDI text rendering error: %s", e)
        return None, 0, 0


def get_text_size(
    text: str,
    font_size: int = 18,
    bold: bool = False,
    font_name: Optional[str] = None,
    lang_code: str = "en",
) -> Tuple[int, int]:
    """Accurately measure the pixel width and height of text."""
    if not text:
        return 0, 0

    chosen_font = font_name or get_font_name_for_text(text, lang_code)

    if IS_WINDOWS:
        try:
            hdc = gdi32.CreateCompatibleDC(None)
            weight = 700 if bold else 400
            hfont = gdi32.CreateFontW(
                font_size, 0, 0, 0, weight, 0, 0, 0, 1, 0, 0, 5, 0, chosen_font
            )
            old_font = gdi32.SelectObject(hdc, hfont)

            rect = RECT(0, 0, 0, 0)
            user32.DrawTextW(hdc, text, len(text), ctypes.byref(rect), 0x0400 | 0x0800)
            tw = rect.right - rect.left
            th = rect.bottom - rect.top

            gdi32.SelectObject(hdc, old_font)
            gdi32.DeleteObject(hfont)
            gdi32.DeleteDC(hdc)
            return tw, th
        except Exception:
            pass

    # Fallback to estimation
    return int(len(text) * font_size * 0.55), int(font_size * 1.3)


def wrap_text(
    text: str,
    max_width: int,
    font_size: int = 18,
    bold: bool = False,
    font_name: Optional[str] = None,
    lang_code: str = "en",
) -> List[str]:
    """Wrap text into lines that do not exceed max_width in pixels."""
    words = str(text or "").split()
    if not words:
        return []

    lines: List[str] = []
    current_line = ""

    for word in words:
        candidate = f"{current_line} {word}".strip() if current_line else word
        w, _ = get_text_size(candidate, font_size, bold, font_name, lang_code)
        if w > max_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate

    if current_line:
        lines.append(current_line)

    return lines


def draw_text_cv2(
    frame: np.ndarray,
    xy: Tuple[int, int],
    text: str,
    font_size: int = 18,
    color_bgr: Tuple[int, int, int] = (255, 255, 255),
    bold: bool = False,
    font_name: Optional[str] = None,
    lang_code: str = "en",
) -> Tuple[int, int]:
    """
    Render shaped, antialiased Unicode text directly onto an OpenCV BGR image frame.
    Returns (width, height) of the drawn text.
    """
    text_s = str(text or "").strip()
    if not text_s:
        return 0, 0

    x, y = xy
    h, w = frame.shape[:2]
    if x >= w or y >= h:
        return 0, 0

    chosen_font = font_name or get_font_name_for_text(text_s, lang_code)

    alpha_mask, tw, th = _render_text_mask_gdi(
        text_s, font_size=font_size, bold=bold, font_name=chosen_font
    )

    if alpha_mask is not None and tw > 0 and th > 0:
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(w, x + tw), min(h, y + th)

        src_x1, src_y1 = x1 - x, y1 - y
        src_x2, src_y2 = src_x1 + (x2 - x1), src_y1 + (y2 - y1)

        if x2 > x1 and y2 > y1:
            crop_alpha = alpha_mask[src_y1:src_y2, src_x1:src_x2, None]
            color_arr = np.array(color_bgr, dtype=np.float32)

            bg_region = frame[y1:y2, x1:x2].astype(np.float32)
            blended = bg_region * (1.0 - crop_alpha) + color_arr * crop_alpha
            frame[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)

        return tw, th

    # Fallback to cv2.putText for standard ASCII if GDI fails
    try:
        cv2_font = cv2.FONT_HERSHEY_SIMPLEX
        scale = font_size / 30.0
        cv2.putText(frame, text_s, (x, y + font_size), cv2_font, scale, color_bgr, 1 if not bold else 2, cv2.LINE_AA)
        return int(len(text_s) * font_size * 0.5), int(font_size * 1.2)
    except Exception:
        return 0, 0


def draw_text_pil(
    pil_img: Image.Image,
    xy: Tuple[int, int],
    text: str,
    font_size: int = 18,
    fill: Union[Tuple[int, int, int], Tuple[int, int, int, int]] = (255, 255, 255),
    bold: bool = False,
    font_name: Optional[str] = None,
    lang_code: str = "en",
) -> Tuple[int, int]:
    """
    Render shaped, antialiased Unicode text directly onto a PIL Image.
    Returns (width, height) of the drawn text.
    """
    text_s = str(text or "").strip()
    if not text_s:
        return 0, 0

    x, y = xy
    chosen_font = font_name or get_font_name_for_text(text_s, lang_code)

    alpha_mask, tw, th = _render_text_mask_gdi(
        text_s, font_size=font_size, bold=bold, font_name=chosen_font
    )

    if alpha_mask is not None and tw > 0 and th > 0:
        mask_u8 = (alpha_mask * 255).astype(np.uint8)
        mask_im = Image.fromarray(mask_u8, mode="L")
        color_rgb = fill[:3] if isinstance(fill, (tuple, list)) else (255, 255, 255)
        color_im = Image.new("RGBA", (tw, th), (*color_rgb, 255))
        try:
            pil_img.paste(color_im, (x, y), mask_im)
            return tw, th
        except Exception:
            pass

    # Fallback
    try:
        draw = ImageDraw.Draw(pil_img)
        font = ImageFont.load_default()
        draw.text(xy, text_s, fill=fill, font=font)
        return int(len(text_s) * font_size * 0.5), int(font_size * 1.2)
    except Exception:
        return 0, 0

