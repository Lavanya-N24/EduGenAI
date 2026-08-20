"""
EduGenAI - Audio Input Service
Extracts text from audio files using OpenAI Whisper.
"""
import logging
import io
import tempfile
import os
import whisper

logger = logging.getLogger(__name__)

# Load the whisper model once
_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        logger.info("Loading Whisper base model for Audio Input...")
        # Using 'base' model for decent accuracy and fast performance on CPU
        _whisper_model = whisper.load_model("base")
    return _whisper_model

async def extract_text_from_audio(audio_bytes: bytes, file_extension: str) -> dict:
    """
    Extracts text from audio bytes using OpenAI Whisper.
    
    Args:
        audio_bytes: The raw bytes of the uploaded audio file.
        file_extension: e.g. ".mp3", ".wav"
        
    Returns:
        dict with extracted text and metadata.
    """
    model = get_whisper_model()
    
    # Whisper requires a file path, so we write the bytes to a temp file
    temp_fd, temp_path = tempfile.mkstemp(suffix=file_extension)
    try:
        with os.fdopen(temp_fd, 'wb') as f:
            f.write(audio_bytes)
            
        logger.info(f"Extracting text from audio ({len(audio_bytes)} bytes)")
        
        # Transcribe audio
        result = model.transcribe(temp_path)
        
        text = result["text"].strip()
        detected_language = result.get("language", "unknown")
        
        logger.info(f"Audio extraction complete. Detected language: {detected_language}, Extracted {len(text)} chars.")
        
        return {
            "text": text,
            "language": detected_language,
            "method": "whisper_speech_to_text",
            "word_count": len(text.split()),
        }
        
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        raise RuntimeError(f"Audio extraction failed: {str(e)}")
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
