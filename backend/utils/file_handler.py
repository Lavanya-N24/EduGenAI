import logging
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

async def handle_uploaded_file(file: UploadFile) -> tuple[bytes, str]:
    """
    Reads an uploaded file and determines its type for processing.
    """
    file_bytes = await file.read()
    filename = file.filename.lower()

    if filename.endswith((".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp")):
        input_type = "image_ocr"
    elif filename.endswith(".pdf"):
        input_type = "pdf"
    elif filename.endswith(".pptx"):
        input_type = "pptx"
    elif filename.endswith(".docx"):
        input_type = "docx"
    elif filename.endswith((".mp3", ".wav", ".m4a", ".ogg")):
        input_type = "audio"
    else:
        # Try reading as plain text file
        try:
            file_bytes.decode("utf-8")
            input_type = "text_file"
        except UnicodeDecodeError:
            raise HTTPException(400, f"Unsupported file format: {filename}. Use text, image, PDF, DOCX, PPTX, or audio.")

    return file_bytes, input_type
