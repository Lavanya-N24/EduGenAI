"""
EduGenAI - SadTalker Animation Service
Wraps the SadTalker deep learning model to generate lip-synced talking head videos.
"""
import logging
import os
import subprocess
from pathlib import Path
from config import BASE_DIR, VIDEO_DIR

logger = logging.getLogger(__name__)

SADTALKER_DIR = BASE_DIR / "sadtalker"
INFERENCE_SCRIPT = SADTALKER_DIR / "inference.py"
AVATAR_IMG = BASE_DIR / "assets" / "avatar.png"

async def generate_talking_head(audio_path: str, output_name: str) -> str:
    """
    Runs SadTalker inference on the CPU to generate a talking head video.
    
    Args:
        audio_path: Path to the generated TTS audio (.wav or .mp3)
        output_name: Desired name for the output mp4 file (e.g. 'scene_1_avatar.mp4')
        
    Returns:
        Path to the generated video.
    """
    output_dir = VIDEO_DIR / "avatars"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    final_output_path = output_dir / output_name

    # If the file already exists (e.g., from a previous run or cache), just return it
    if final_output_path.exists():
        return str(final_output_path)

    if not INFERENCE_SCRIPT.exists():
        logger.error("SadTalker repository not found in backend/sadtalker/")
        raise FileNotFoundError("SadTalker inference script missing.")

    if not AVATAR_IMG.exists():
        logger.error(f"Default avatar image missing at {AVATAR_IMG}")
        raise FileNotFoundError("Avatar image missing.")

    logger.info(f"Starting SadTalker generation for {audio_path}...")
    logger.warning("Running SadTalker on CPU. This will take a VERY long time.")

    # Build the SadTalker inference command
    # --still: less head movement, better for static presentations
    # --preprocess crop: crops the face automatically
    # --enhancer gfpgan: improves face resolution (might be too slow on CPU, we can disable if needed)
    cmd = [
        "python", str(INFERENCE_SCRIPT),
        "--driven_audio", str(audio_path),
        "--source_image", str(AVATAR_IMG),
        "--result_dir", str(output_dir),
        "--still",
        "--preprocess", "crop",
        "--device", "cpu"
    ]

    try:
        # Run as a blocking subprocess for now. In a massive production system, 
        # this would go into a Celery/Redis queue because of the long CPU execution time.
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(SADTALKER_DIR) # Run from the sadtalker directory so paths resolve correctly
        )
        
        if process.returncode != 0:
            logger.error(f"SadTalker failed: {process.stderr}")
            raise RuntimeError(f"SadTalker inference failed: {process.stderr}")
            
        logger.info("SadTalker generation complete!")
        
        # SadTalker outputs to a timestamped subfolder inside result_dir by default.
        # We need to find the newest .mp4 in output_dir and rename it to final_output_path.
        # Let's search the output_dir for the newly created mp4.
        # The output format is usually: {result_dir}/{timestamp}/{avatar_name}##{audio_name}.mp4
        
        # For simplicity, let's just find the most recently created mp4 in the output_dir tree
        all_mp4s = list(output_dir.rglob("*.mp4"))
        if not all_mp4s:
            raise FileNotFoundError("SadTalker completed but no MP4 output was found.")
            
        # Sort by creation time to get the latest
        latest_mp4 = max(all_mp4s, key=os.path.getctime)
        
        # Rename/Move it to our desired final path
        os.replace(latest_mp4, final_output_path)
        
        return str(final_output_path)
        
    except Exception as e:
        logger.error(f"Exception during SadTalker generation: {e}")
        # Fallback: if it fails, we just won't have a talking head.
        return None
