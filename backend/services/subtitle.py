"""
EduGenAI - Subtitle Generation Service
Generates synchronized SRT subtitle files from scene data.

Approach: Since we generate both narration text and audio, we already know
the content and timing. We split narration into timed chunks and generate
standard SRT format subtitles.
"""
import logging
import uuid
from pathlib import Path

from config import SUBTITLE_DIR

logger = logging.getLogger(__name__)


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _split_narration_to_chunks(
    narration: str, duration: float, max_chars: int = 80
) -> list[dict]:
    """
    Split narration text into subtitle chunks with timing.

    Args:
        narration: Full narration text
        duration: Total duration in seconds
        max_chars: Max characters per subtitle line

    Returns:
        list of dicts with text, start, end times
    """
    words = narration.split()
    if not words:
        return []

    # Calculate words per second
    wps = len(words) / max(duration, 1)

    chunks = []
    current_words = []
    current_length = 0

    for word in words:
        if current_length + len(word) + 1 > max_chars and current_words:
            chunks.append(" ".join(current_words))
            current_words = [word]
            current_length = len(word)
        else:
            current_words.append(word)
            current_length += len(word) + 1

    if current_words:
        chunks.append(" ".join(current_words))

    # Calculate timing for each chunk
    timed_chunks = []
    words_so_far = 0

    for chunk in chunks:
        chunk_words = len(chunk.split())
        start_time = words_so_far / wps if wps > 0 else 0
        end_time = (words_so_far + chunk_words) / wps if wps > 0 else 0
        end_time = min(end_time, duration)

        timed_chunks.append({
            "text": chunk,
            "start": start_time,
            "end": end_time,
        })
        words_so_far += chunk_words

    return timed_chunks


async def generate_subtitles(scenes: dict, output_filename: str = None) -> dict:
    """
    Generate SRT subtitle file from scene data.

    Args:
        scenes: Scene data dict with narration and timing info
        output_filename: Custom filename for the subtitle file

    Returns:
        dict with subtitle file path and subtitle count
    """
    if not output_filename:
        output_filename = f"subtitles_{uuid.uuid4().hex[:8]}.srt"

    output_path = SUBTITLE_DIR / output_filename
    srt_entries = []
    entry_index = 1
    cumulative_time = 0.0

    for scene in scenes.get("scenes", []):
        narration = scene.get("narration", "")
        duration = scene.get("audio_duration", scene.get("duration_seconds", 10))

        if not narration:
            cumulative_time += duration
            continue

        chunks = _split_narration_to_chunks(narration, duration)

        for chunk in chunks:
            start = cumulative_time + chunk["start"]
            end = cumulative_time + chunk["end"]

            srt_entry = (
                f"{entry_index}\n"
                f"{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}\n"
                f"{chunk['text']}\n"
            )
            srt_entries.append(srt_entry)
            entry_index += 1

        cumulative_time += duration

    # Write SRT file
    srt_content = "\n".join(srt_entries)
    output_path.write_text(srt_content, encoding="utf-8")

    logger.info(f"Generated {entry_index - 1} subtitle entries → {output_filename}")

    return {
        "subtitle_path": str(output_path),
        "filename": output_filename,
        "total_entries": entry_index - 1,
        "total_duration": round(cumulative_time, 1),
        "format": "srt",
    }


async def generate_scene_subtitles_data(scenes: dict) -> list[dict]:
    """
    Generate subtitle data (in-memory) for video overlay without writing to file.

    Returns:
        list of subtitle dicts with text, start, end times
    """
    all_subtitles = []
    cumulative_time = 0.0

    for scene in scenes.get("scenes", []):
        narration = scene.get("narration", "")
        duration = scene.get("audio_duration", scene.get("duration_seconds", 10))

        if narration:
            chunks = _split_narration_to_chunks(narration, duration)
            for chunk in chunks:
                all_subtitles.append({
                    "text": chunk["text"],
                    "start": cumulative_time + chunk["start"],
                    "end": cumulative_time + chunk["end"],
                })

        cumulative_time += duration

    return all_subtitles
