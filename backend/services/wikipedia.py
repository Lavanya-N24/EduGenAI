"""
EduGenAI - Wikipedia & Wikimedia Research Service

Fetches verified factual background information from Wikipedia using the
Wikimedia REST APIs (search and page summary) to provide research context
for Groq lesson planning.

Endpoints used:
- Search: https://en.wikipedia.org/w/rest.php/v1/search/page?q={query}&limit=5
- Page Summary: https://en.wikipedia.org/api/rest_v1/page/summary/{title}
"""

import logging
import re
import urllib.parse
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

WIKIMEDIA_REST_SEARCH = "https://en.wikipedia.org/w/rest.php/v1/search/page"
WIKIMEDIA_REST_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary"
WIKI_HEADERS = {
    "User-Agent": "EduGenAI-LessonPlanner/2.0 (https://github.com/EduGenAI; contact@edugenai.edu) httpx/0.28.1",
    "Accept": "application/json",
}
TIMEOUT = 7.0


async def search_wikipedia_topic(query: str, limit: int = 5) -> list[dict]:
    """
    Search Wikipedia for the most relevant articles using the Wikimedia REST API.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    # If query is in non-English, translate query to English for Wikipedia search
    if any(ord(c) > 127 for c in clean_query):
        try:
            from deep_translator import GoogleTranslator
            clean_query = GoogleTranslator(source="auto", target="en").translate(clean_query)
        except Exception:
            pass

    # Remove excess punctuation
    search_term = re.sub(r"[^\w\s\-]", " ", clean_query).strip()
    search_term = " ".join(search_term.split()[:8])

    params = {"q": search_term, "limit": limit}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(WIKIMEDIA_REST_SEARCH, params=params, headers=WIKI_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("pages", [])
                results = []
                for p in pages:
                    results.append({
                        "key": p.get("key"),
                        "title": p.get("title"),
                        "description": p.get("description", ""),
                        "thumbnail": p.get("thumbnail", {}).get("url") if p.get("thumbnail") else None,
                    })
                return results
            else:
                logger.warning("Wikimedia REST search returned %d for query '%s'", resp.status_code, search_term)
    except Exception as e:
        logger.warning("Wikimedia REST search exception: %s", e)

    return []


async def get_wikipedia_summary(title: str) -> Optional[dict]:
    """
    Retrieve structured article summary and metadata from Wikimedia REST API.
    """
    if not title:
        return None

    safe_title = urllib.parse.quote(title.replace(" ", "_"), safe=":/@")
    url = f"{WIKIMEDIA_REST_SUMMARY}/{safe_title}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(url, headers=WIKI_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "title": data.get("title", title),
                    "display_title": data.get("displaytitle", title),
                    "description": data.get("description", ""),
                    "extract": data.get("extract", "").strip(),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", f"https://en.wikipedia.org/wiki/{safe_title}"),
                    "thumbnail": data.get("thumbnail", {}).get("source") if data.get("thumbnail") else None,
                    "timestamp": data.get("timestamp"),
                }
            else:
                logger.warning("Wikimedia REST summary returned %d for '%s'", resp.status_code, title)
    except Exception as e:
        logger.warning("Wikimedia REST summary exception: %s", e)

    return None


async def research_topic(topic_or_text: str) -> dict:
    """
    High-level Wikipedia research pipeline:
    1. Search for most relevant Wikipedia article.
    2. Retrieve article summary & extract.
    3. Format clean educational facts for Groq lesson planning.
    4. Provide source metadata for frontend citations.

    Returns:
        dict with keys:
            - was_found: bool
            - title: str
            - description: str
            - extract: str
            - url: str
            - thumbnail: Optional[str]
            - research_context: str (Formatted prompt context for Groq)
    """
    query = topic_or_text.strip()
    if not query:
        return {"was_found": False, "research_context": "", "sources": []}

    # Extract first 15 words if text is a paragraph
    search_query = " ".join(query.split()[:12])

    logger.info("📚 Researching topic on Wikipedia: '%s'", search_query)

    # 1. Search Wikipedia
    candidates = await search_wikipedia_topic(search_query, limit=3)
    if not candidates:
        # Try raw topic directly as page title
        summary_data = await get_wikipedia_summary(search_query)
        if summary_data and summary_data.get("extract"):
            return _build_research_result(summary_data)
        logger.info("No Wikipedia article found for '%s'. Continuing with Groq general knowledge.", search_query)
        return {"was_found": False, "research_context": "", "sources": []}

    # 2. Get top candidate summary
    top_candidate = candidates[0]
    title_to_fetch = top_candidate.get("key") or top_candidate.get("title")
    summary_data = await get_wikipedia_summary(title_to_fetch)

    if not summary_data or not summary_data.get("extract"):
        # Try second candidate if available
        if len(candidates) > 1:
            second_title = candidates[1].get("key") or candidates[1].get("title")
            summary_data = await get_wikipedia_summary(second_title)

    if summary_data and summary_data.get("extract"):
        return _build_research_result(summary_data)

    logger.info("Wikipedia summary was empty. Falling back to Groq knowledge.")
    return {"was_found": False, "research_context": "", "sources": []}


def _build_research_result(data: dict) -> dict:
    title = data.get("title", "")
    desc = data.get("description", "")
    extract = data.get("extract", "")
    url = data.get("url", "")
    thumb = data.get("thumbnail")

    research_context = (
        f"FACTUAL WIKIPEDIA RESEARCH CONTEXT:\n"
        f"Article Title: {title}\n"
        f"Topic Summary: {desc}\n"
        f"Key Educational Facts:\n{extract}\n"
        f"Source URL: {url}\n\n"
        f"INSTRUCTION: Use these factual details to ensure 100% scientific accuracy, "
        f"correct terminology, and step-by-step logic. Do NOT copy word-for-word; "
        f"explain in an engaging, student-friendly teaching style."
    )

    logger.info("✅ Successfully retrieved Wikipedia research context for: '%s' (%d chars)", title, len(extract))

    return {
        "was_found": True,
        "title": title,
        "description": desc,
        "extract": extract,
        "url": url,
        "thumbnail": thumb,
        "research_context": research_context,
        "sources": [
            {
                "title": f"Wikipedia: {title}",
                "description": desc,
                "url": url,
                "thumbnail": thumb,
            }
        ],
    }
