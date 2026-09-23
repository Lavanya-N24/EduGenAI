import asyncio
import time
from services.llm import generate_scenes
from services.translation import translate_scenes
from services.tts import generate_scene_audio
from services.video import generate_video

async def main():
    t_start = time.time()
    print("Step 1: Storyboard...")
    t0 = time.time()
    scenes = await generate_scenes("Newton laws of motion", "Kannada", "beginner")
    print(f"  Done in {time.time()-t0:.2f}s, scenes: {len(scenes.get('scenes', []))}")

    print("Step 2: Translation...")
    t1 = time.time()
    scenes = await translate_scenes(scenes, "kn")
    print(f"  Done in {time.time()-t1:.2f}s")

    print("Step 3: Neural TTS...")
    t2 = time.time()
    scenes = await generate_scene_audio(scenes, "kn")
    print(f"  Done in {time.time()-t2:.2f}s")

    print("Step 4: Video Generation...")
    t3 = time.time()
    video_res = await generate_video(scenes, lang_code="kn")
    print(f"  Done in {time.time()-t3:.2f}s")

    total = time.time() - t_start
    print(f"\n⚡ TOTAL PIPELINE DURATION: {total:.2f} seconds!")
    print(f"Video file: {video_res.get('filename')}, duration: {video_res.get('duration')}s")

if __name__ == "__main__":
    asyncio.run(main())
