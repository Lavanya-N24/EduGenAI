"""
EduGenAI - Educational Image Fetcher

Fetches relevant educational images for each scene.

Priority:
1. Pexels API, if PEXELS_API_KEY is available
2. Pixabay API, if PIXABAY_API_KEY is available
3. Return None so the animation renderer can use its own fallback

This module does NOT generate video.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

try:
    from config import IMAGE_DIR
except Exception:
    IMAGE_DIR = Path("outputs/images")

IMAGE_DIR = Path(IMAGE_DIR)
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "").strip()
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()

PEXELS_URL = "https://api.pexels.com/v1/search"
PIXABAY_URL = "https://pixabay.com/api/"

REQUEST_TIMEOUT = 20


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _clean_query(query: str) -> str:
    """
    Clean and ensure an educational image query is in English for Pexels/Pixabay.
    """
    query = str(query or "").strip()
    if not query:
        return ""

    # If query contains non-ASCII characters (e.g. Kannada, Hindi, etc.), translate to English
    if any(ord(char) > 127 for char in query):
        try:
            from deep_translator import GoogleTranslator
            query = GoogleTranslator(source="auto", target="en").translate(query)
        except Exception:
            pass

    query = re.sub(
        r"[^a-zA-Z0-9\s,\-]",
        " ",
        str(query or ""),
    )

    query = re.sub(
        r"\s+",
        " ",
        query,
    )

    return query[:180].strip()


def _filename_from_query(query: str) -> str:
    safe = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        query.lower(),
    ).strip("_")

    if not safe:
        safe = "scene"

    return (
        f"{safe}_"
        f"{uuid.uuid4().hex[:8]}.jpg"
    )


def _download_image(
    url: str,
    output_path: Path,
) -> str | None:

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "EduGenAI-EducationalApp/2.0 (contact@edugenai.edu; https://github.com/EduGenAI)",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            },
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )

        response.raise_for_status()

        content_type = (
            response.headers
            .get("content-type", "")
            .lower()
        )

        if (
            "image" not in content_type
            and not url.lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")
            )
        ):
            logger.warning(
                "URL does not look like an image: %s",
                content_type,
            )

        with open(
            output_path,
            "wb",
        ) as f:
            for chunk in response.iter_content(
                chunk_size=1024 * 256
            ):
                if chunk:
                    f.write(chunk)

        if output_path.stat().st_size < 1000:
            output_path.unlink(
                missing_ok=True
            )
            return None

        return str(output_path)

    except Exception as exc:
        logger.warning(
            "Image download failed: %s",
            exc,
        )

        try:
            output_path.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        return None


# ---------------------------------------------------------
# Pexels
# ---------------------------------------------------------

def _search_pexels(
    query: str,
) -> str | None:

    if not PEXELS_API_KEY:
        return None

    try:
        response = requests.get(
            PEXELS_URL,
            headers={
                "Authorization": PEXELS_API_KEY,
            },
            params={
                "query": query,
                "per_page": 8,
                "orientation": "landscape",
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        photos = data.get(
            "photos",
            [],
        )

        if not photos:
            return None

        # Prefer landscape educational images.
        for photo in photos:
            sources = photo.get(
                "src",
                {},
            )

            image_url = (
                sources.get("large2x")
                or sources.get("large")
                or sources.get("original")
            )

            if image_url:
                return image_url

        return None

    except Exception as exc:
        logger.warning(
            "Pexels search failed: %s",
            exc,
        )

        return None


# ---------------------------------------------------------
# Pixabay
# ---------------------------------------------------------

def _search_pixabay(
    query: str,
) -> str | None:

    if not PIXABAY_API_KEY:
        return None

    try:
        response = requests.get(
            PIXABAY_URL,
            params={
                "key": PIXABAY_API_KEY,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "safesearch": "true",
                "per_page": 10,
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        hits = data.get(
            "hits",
            [],
        )

        if not hits:
            return None

        for hit in hits:
            image_url = (
                hit.get("largeImageURL")
                or hit.get("webformatURL")
            )

            if image_url:
                return image_url

        return None

    except Exception as exc:
        logger.warning(
            "Pixabay search failed: %s",
            exc,
        )

        return None


def _search_wikipedia_image(query: str) -> str | None:
    """Search Wikimedia Commons for authentic educational images.
    Uses namespace=6 (File:) search which directly matches photo file descriptions,
    giving much higher relevance than Wikipedia article thumbnail lookup.
    Falls back to Wikipedia pageimages with strict title-relevance filtering.
    """
    try:
        clean_q = _clean_query(query)
        if not clean_q:
            return None

        # ── 1. Wikimedia Commons file search (namespace=6) ──────────────────
        # Searches actual image file names/descriptions → very accurate
        commons_url = (
            "https://commons.wikimedia.org/w/api.php"
            "?action=query&generator=search&gsrnamespace=6"
            f"&gsrsearch={quote(clean_q)}&gsrlimit=15"
            "&prop=imageinfo&iiprop=url|size&format=json"
        )
        try:
            resp = requests.get(
                commons_url,
                headers={"User-Agent": "EduGenAI-EducationalApp/2.0 (contact@edugenai.edu)"},
                timeout=6,
            )
            if resp.status_code == 200:
                pages = resp.json().get("query", {}).get("pages", {})
                query_words = set(
                    w.lower() for w in clean_q.split() if len(w) > 3
                )
                # Score each file by how many query words appear in the file title
                candidates = []
                for pid, p in pages.items():
                    title_lower = p.get("title", "").lower()
                    ii_list = p.get("imageinfo", [])
                    if not ii_list:
                        continue
                    img_url = ii_list[0].get("url", "")
                    w = ii_list[0].get("width", 0)
                    h = ii_list[0].get("height", 0)
                    # Only use reasonably sized, landscape/portrait image files
                    if not img_url.lower().endswith((".jpg", ".jpeg", ".png")):
                        continue
                    if w < 300 or h < 200:
                        continue
                    score = sum(1 for qw in query_words if qw in title_lower)
                    candidates.append((score, w * h, img_url))

                # Sort: highest relevance first, then biggest image
                candidates.sort(reverse=True)
                if candidates and candidates[0][0] > 0:
                    logger.info("✅ Wikimedia Commons hit for '%s': score=%d", clean_q, candidates[0][0])
                    return candidates[0][2]
        except Exception as e:
            logger.warning("Wikimedia Commons search error: %s", e)

        # ── 2. Wikipedia pageimages with strict title-relevance filter ───────
        # Searches article pages but only accepts images whose article title
        # contains query keywords (avoids wildlife/unrelated articles).
        try:
            wiki_url = (
                "https://en.wikipedia.org/w/api.php"
                "?action=query&generator=search"
                f"&gsrsearch={quote(clean_q)}&gsrlimit=10"
                "&prop=pageimages&pithumbsize=1200&format=json"
            )
            resp2 = requests.get(
                wiki_url,
                headers={"User-Agent": "EduGenAI-EducationalApp/2.0 (contact@edugenai.edu)"},
                timeout=6,
            )
            if resp2.status_code == 200:
                pages2 = resp2.json().get("query", {}).get("pages", {})
                query_words2 = set(
                    w.lower() for w in clean_q.split() if len(w) > 3
                )
                ranked = []
                for pid, p in pages2.items():
                    title_lower = p.get("title", "").lower()
                    thumb = p.get("thumbnail", {}).get("source", "")
                    if not thumb:
                        continue
                    score = sum(1 for qw in query_words2 if qw in title_lower)
                    ranked.append((score, p.get("title", ""), thumb))
                ranked.sort(reverse=True)
                # Only accept if at least 1 query word appears in the article title
                for score, title, img_url in ranked:
                    if score >= 1:
                        logger.info(
                            "✅ Wikipedia pageimages hit for '%s': article='%s' score=%d",
                            clean_q, title, score,
                        )
                        return img_url
        except Exception as e:
            logger.warning("Wikipedia pageimages search error: %s", e)

    except Exception as e:
        logger.warning("Wikipedia image search error: %s", e)
    return None


# ---------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------

async def fetch_background_image(
    query: str,
    output_dir: str | Path | None = None,
) -> str | None:
    """
    Fetch one relevant background image.
    Prioritizes authentic Wikipedia images for history/biography/geography, then Pexels, then Pixabay.
    """
    query = _clean_query(query)
    if not query:
        return None

    destination = (
        Path(output_dir)
        if output_dir
        else IMAGE_DIR
    )
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = _filename_from_query(query)
    output_path = destination / filename

    logger.info("🖼️ Searching educational visual: %s", query)

    # Smart routing: Pexels/Pixabay for science/nature/astronomy/botany; Wikipedia for history/geography/biography
    is_science = any(k in query.lower() for k in (
        "plant", "leaf", "leaves", "photosynthesis", "sunlight", "chloroplast", "water", "oxygen",
        "cell", "biology", "solar system", "space", "planet", "galaxy", "physics", "chemistry",
        "molecule", "dna", "gravity", "energy", "circuit", "organism", "nature", "forest"
    ))

    loop = asyncio.get_running_loop()
    if is_science:
        image_url = await loop.run_in_executor(
            None,
            lambda: (
                _search_pexels(query)
                or _search_pixabay(query)
                or _search_wikipedia_image(query)
            ),
        )
    else:
        image_url = await loop.run_in_executor(
            None,
            lambda: (
                _search_wikipedia_image(query)
                or _search_pexels(query)
                or _search_pixabay(query)
            ),
        )

    if not image_url:
        logger.warning(
            "No image found for: %s",
            query,
        )
        return None

    image_path = await loop.run_in_executor(
        None,
        lambda: _download_image(
            image_url,
            output_path,
        ),
    )

    if image_path:
        logger.info(
            "✅ Image ready: %s",
            image_path,
        )

    return image_path


# ---------------------------------------------------------
# Scene helper
# ---------------------------------------------------------

async def fetch_scene_image(
    scene: dict,
    output_dir: str | Path | None = None,
) -> str | None:
    """
    Fetch an image based on the scene's image keywords.

    Supports the storyboard format produced by llm.py:

        image_keywords: [...]
        visual_prompt: "..."
        visual_description: "..."
    """

    keywords = scene.get(
        "image_keywords",
        [],
    )

    if isinstance(
        keywords,
        list,
    ):
        keywords = [
            str(k).strip()
            for k in keywords
            if str(k).strip()
        ]
    else:
        keywords = []

    if keywords:
        query = ", ".join(
            keywords[:4]
        )
    else:
        query = (
            scene.get(
                "visual_prompt"
            )
            or scene.get(
                "visual_description"
            )
            or scene.get(
                "title"
            )
            or "educational science"
        )

    image_path = await fetch_background_image(
        query,
        output_dir=output_dir,
    )

    if image_path:
        scene["image_path"] = image_path

    return image_path


# ---------------------------------------------------------
# Multiple scenes
# ---------------------------------------------------------

async def fetch_scene_images(
    scenes: dict,
    output_dir: str | Path | None = None,
) -> dict:
    """
    Fetch images for all scenes.

    Requests run concurrently but are limited to avoid
    hammering the image API.
    """

    scene_list = scenes.get(
        "scenes",
        [],
    )

    semaphore = asyncio.Semaphore(3)

    async def fetch_one(scene):
        async with semaphore:
            try:
                return await fetch_scene_image(
                    scene,
                    output_dir,
                )
            except Exception as exc:
                logger.warning(
                    "Scene image failed: %s",
                    exc,
                )
                return None

    await asyncio.gather(
        *[
            fetch_one(scene)
            for scene in scene_list
        ]
    )

    return scenes