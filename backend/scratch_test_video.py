import asyncio
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.video import generate_video

async def run_test():
    scenes = {
        "scenes": [
            {
                "scene_id": 1,
                "title": "What is Gravity?",
                "narration": "Gravity is the force that pulls objects towards each other.",
                "visual_description": "A big apple falling from a tree.",
                "key_concepts": ["Force", "Mass", "Attraction", "Earth"],
                "audio_duration": 4, # Just 4 seconds
                "audio_path": "" # No audio for this test, fallback to 0 RMS
            }
        ]
    }
    print("Starting video generation test...")
    try:
        res = await generate_video(scenes, "test_gravity.mp4")
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(run_test())
