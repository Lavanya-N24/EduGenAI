"""
EduGenAI - OCR Service
Extracts text from images (book pages, handwritten notes) and PDFs.

ML Algorithm: Tesseract 5 uses LSTM (Long Short-Term Memory) neural networks.
Pipeline: Image → Preprocessing → Character Segmentation → LSTM Recognition → Output Text
"""
import io
import logging
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
import pytesseract
import fitz  # PyMuPDF

from config import TESSERACT_PATH

logger = logging.getLogger(__name__)

import shutil

# Set Tesseract path if specified and exists/in PATH
if TESSERACT_PATH and (Path(TESSERACT_PATH).exists() or shutil.which(TESSERACT_PATH)):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Enhances image quality for better OCR accuracy.
    Steps: Grayscale → Contrast boost → Sharpen → Binarize
    """
    # Convert to grayscale
    img = image.convert("L")

    # Boost contrast (helps with faded text)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Sharpen (helps with blurry photos)
    img = img.filter(ImageFilter.SHARPEN)

    # Binarize using threshold (black text on white background)
    img = img.point(lambda x: 0 if x < 140 else 255, "1")

    return img


async def extract_text_from_image(image_bytes: bytes, language: str = "eng") -> dict:
    """
    Extract text from an image using Tesseract OCR.

    Args:
        image_bytes: Raw image bytes (from upload)
        language: Tesseract language code (eng, hin, tam, etc.)

    Returns:
        dict with extracted text and confidence score
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        processed = preprocess_image(image)

        # Extract text with confidence data
        data = pytesseract.image_to_data(
            processed, lang=language, output_type=pytesseract.Output.DICT
        )

        # Build text from high-confidence words
        words = []
        confidences = []
        for i, word in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf > 30 and word.strip():  # Filter low-confidence noise
                words.append(word)
                confidences.append(conf)

        text = " ".join(words)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        logger.info(f"OCR extracted {len(words)} words, avg confidence: {avg_confidence:.1f}%")

        return {
            "text": text,
            "word_count": len(words),
            "confidence": round(avg_confidence, 2),
            "language": language,
        }
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise RuntimeError(f"OCR extraction failed: {str(e)}")


async def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Extract text from a PDF document.
    Uses PyMuPDF for digital PDFs, falls back to OCR for scanned PDFs.

    Returns:
        dict with extracted text, page count, and method used
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_text = []
        method = "digital"

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()

            if text:
                # Digital PDF — text is embedded
                all_text.append(f"--- Page {page_num + 1} ---\n{text}")
            else:
                # Scanned PDF — fall back to OCR
                method = "ocr"
                pix = page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                result = await extract_text_from_image(img_bytes)
                all_text.append(f"--- Page {page_num + 1} ---\n{result['text']}")

        page_count = len(doc)
        doc.close()
        combined = "\n\n".join(all_text)

        logger.info(f"PDF extracted {page_count} pages using {method} method")

        return {
            "text": combined,
            "page_count": page_count,
            "method": method,
            "word_count": len(combined.split()),
        }
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError(f"PDF extraction failed: {str(e)}")
