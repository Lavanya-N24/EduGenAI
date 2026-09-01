"""
Fast end-to-end visual animation test for EduGenAI.

Run from backend:
    python test_photosynthesis_animation.py

Creates six connected Photosynthesis clips using the same
Pexels image plus content-specific motion.
"""

import asyncio
from pathlib import Path

from services.image_fetcher import fetch_background_image
from services.visual_animation import render_educational_scene


async def main():
    print("\n🌱 PHOTOSYNTHESIS ANIMATION TEST")
    print("=" * 45)

    image_path = await fetch_background_image(
        "green plant leaves sunlight photosynthesis"
    )

    if not image_path:
        raise RuntimeError(
            "Could not fetch image. Check PEXELS_API_KEY."
        )

    print(f"✅ Image: {image_path}")

    out_dir = Path("outputs/videos/photosynthesis_test")
    out_dir.mkdir(parents=True, exist_ok=True)

    scenes = [
        (
            "01_sunlight.mp4",
            "plant_sunlight",
            6,
            "Sunlight reaches the leaves.",
        ),
        (
            "02_water.mp4",
            "water",
            6,
            "Water moves from the roots toward the leaves.",
        ),
        (
            "03_co2.mp4",
            "co2",
            6,
            "Carbon dioxide moves toward the leaf.",
        ),
        (
            "04_chloroplast.mp4",
            "chloroplast",
            6,
            "The camera moves into the chloroplast.",
        ),
        (
            "05_products.mp4",
            "oxygen_glucose",
            6,
            "Glucose is produced and oxygen is released.",
        ),
        (
            "06_full_process.mp4",
            "photosynthesis",
            8,
            "Sunlight, water and carbon dioxide combine in photosynthesis.",
        ),
    ]

    for number, (filename, motion, duration, explanation) in enumerate(
        scenes, start=1
    ):
        print(f"\n🎬 {number}/6  {motion}")
        print(f"   {explanation}")

        output = out_dir / filename

        render_educational_scene(
            image_path=image_path,
            output_path=str(output),
            duration=duration,
            motion=motion,
            zoom_start=1.00,
            zoom_end=1.06,
        )

        print(f"   ✅ {output}")

    print("\n" + "=" * 45)
    print("🎉 VISUAL ANIMATION TEST COMPLETE")
    print(f"📁 {out_dir.resolve()}")
    print("=" * 45)


if __name__ == "__main__":
    asyncio.run(main())
