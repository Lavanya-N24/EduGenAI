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
        "A beautiful educational 3D animation explaining photosynthesis. "
        "Show a healthy green plant growing under bright sunlight. "
        "Warm sunlight rays move naturally toward the leaves. "
        "The leaves gently move in the breeze. "
        "The camera slowly pushes toward the leaf. "
        "Scientific but visually beautiful classroom animation. "
        "Smooth natural motion and cinematic camera movement. "
        "No text, no subtitles, no labels, no watermark."
    ),
    "resolution": "720p",
    "duration": 6
}

print("====================================")
print(" PIXAZO LTX 2.5 TEST")
print("====================================")
print("URL:", URL)
print("API key:", "FOUND")

try:
    response = requests.post(
        URL,
        headers=headers,
        json=payload,
        timeout=120,
    )

    print("\nHTTP:", response.status_code)
    print("Response:")
    print(response.text)

    if response.status_code not in (200, 201, 202):
        raise RuntimeError(
            f"Pixazo request failed: HTTP {response.status_code}"
        )

    print("\n✅ REQUEST ACCEPTED")

except requests.RequestException as e:
    print("\n❌ Network error:")
    print(e)
    raise