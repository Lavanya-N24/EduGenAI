"""
EduGenAI - Knowledge Base Service
Enriches short inputs (like brief topics or keywords) by searching Wikipedia
and fallback sources (DuckDuckGo), appending detailed educational context before
it hits the AI filter model, summarizer, and video generator.
"""
import logging
import asyncio
import httpx

logger = logging.getLogger(__name__)

WIKI_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
WIKI_HEADERS = {"User-Agent": "EduGenAI/1.0 (https://github.com/EduGenAI; contact@edugenai.com) httpx/0.28.1"}
DUCKDUCKGO_URL = "https://api.duckduckgo.com/"


async def _wiki_search(query: str) -> str | None:
    """Search Wikipedia and return the top article title."""
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(WIKI_SEARCH_URL, params=params, headers=WIKI_HEADERS)
            if resp.status_code != 200:
                logger.warning(f"Wikipedia search returned status {resp.status_code}")
                return None
            data = resp.json()
            results = data.get("query", {}).get("search", [])
            return results[0]["title"] if results else None
    except Exception as e:
        logger.warning(f"Wikipedia search error: {e}")
        return None


async def _wiki_extract(title: str, sentences: int = 15) -> str | None:
    """Fetch the plain-text extract of a Wikipedia article."""
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "exsentences": sentences,
        "titles": title,
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(WIKI_SEARCH_URL, params=params, headers=WIKI_HEADERS)
            if resp.status_code != 200:
                logger.warning(f"Wikipedia extract returned status {resp.status_code}")
                return None
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            page = next(iter(pages.values()))
            return page.get("extract", "").strip() or None
    except Exception as e:
        logger.warning(f"Wikipedia extract error: {e}")
        return None


async def _duckduckgo_search(query: str) -> str | None:
    """Fallback knowledge source using DuckDuckGo Instant Answer API."""
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1"
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(DUCKDUCKGO_URL, params=params, headers=WIKI_HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "").strip()
                if abstract:
                    return abstract
    except Exception as e:
        logger.warning(f"DuckDuckGo fallback search error: {e}")
    return None


async def enrich_with_knowledge_base(text: str, max_trigger_length: int = 400) -> dict:
    """
    Searches Wikipedia using Wikimedia REST APIs to retrieve rich educational
    context before sending it to the ML filter model, summarizer, and video pipeline.
    """
    clean_text = text.strip()

    if len(clean_text) > max_trigger_length:
        logger.info(f"Text is {len(clean_text)} chars (over {max_trigger_length}). Skipping Knowledge Base.")
        return {"enriched_text": text, "was_enriched": False, "source": None, "sources": []}

    logger.info(f"Text is short ({len(clean_text)} chars). Searching Knowledge Base for: '{clean_text}'")

    # 1. Primary Source: Wikipedia REST API
    try:
        from services.wikipedia import research_topic
        wiki_res = await research_topic(clean_text)
        if wiki_res.get("was_found") and wiki_res.get("extract"):
            enriched_text = f"Topic: {clean_text}\n\nFactual Context from Wikipedia ({wiki_res['title']}):\n{wiki_res['extract']}"
            logger.info(f"Knowledge Base enrichment successful via Wikipedia: {wiki_res['title']}")
            return {
                "enriched_text": enriched_text,
                "was_enriched": True,
                "source": f"Wikipedia: {wiki_res['title']}",
                "sources": wiki_res.get("sources", []),
                "wikipedia_data": wiki_res,
            }
    except Exception as e:
        logger.error(f"Wikipedia enrichment failed: {e}")

    # 2. Secondary Source: DuckDuckGo Instant Answer
    try:
        ddg_summary = await _duckduckgo_search(clean_text)
        if ddg_summary:
            enriched_text = f"Topic: {clean_text}\n\nFactual Context:\n{ddg_summary}"
            logger.info(f"Knowledge Base enrichment successful via DuckDuckGo ({len(ddg_summary)} chars).")
            return {
                "enriched_text": enriched_text,
                "was_enriched": True,
                "source": "DuckDuckGo Knowledge Base",
                "sources": [{"title": "DuckDuckGo Knowledge Base", "url": f"https://duckduckgo.com/?q={clean_text}"}],
                "wikipedia_data": None,
            }
    except Exception as e:
        logger.error(f"Secondary knowledge source failed: {e}")

    return {"enriched_text": text, "was_enriched": False, "source": None, "sources": [], "wikipedia_data": None}

