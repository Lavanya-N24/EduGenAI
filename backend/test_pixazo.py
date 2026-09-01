import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PIXAZO_API_KEY", "").strip()

if not API_KEY:
    raise RuntimeError("PIXAZO_API_KEY is missing")

URL = "https://gateway.pixazo.ai/ltx-2-5-pro/v1/text-to-video"

headers = {
    "Content-Type": "application/json",
    "Ocp-Apim-Subscription-Key": API_KEY,
}

payload = {
    "prompt": (
        "Educational 3D animation showing photosynthesis. "
        "A healthy green plant stands under bright sunlight. "
        "Sunlight rays gently move toward the green leaves. "
        "The camera slowly moves closer to the leaf. "
        "Natural plant movement, beautiful scientific visualization, "
        "smooth cinematic motion, classroom-friendly, "
        "no text, no subtitles, no watermark."
    ),
    "resolution": "720p",
    "duration": 6,
    "fps": 24,
    "generate_audio": False,
    "aspect_ratio": "16:9",
}

print("Sending request to Pixazo LTX 2.5...")
print("URL:", URL)

response = requests.post(
    URL,
    headers=headers,
    json=payload,
    timeout=60,
)

print("\nHTTP:", response.status_code)
print("Response:")
print(response.text)