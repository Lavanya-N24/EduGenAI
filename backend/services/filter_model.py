"""
EduGenAI - Content Filter Service (Fast Groq Path)

Strategy:
  1. Check if the trained DistilBERT model is available.
  2. If YES → use it (accurate, but slow CPU inference).
  3. If NO  → use Groq to filter in < 1s (fast path).

For speed, the Groq path is preferred when the model isn't loaded.
"""
import logging
from services.model_loader import get_filter_model

logger = logging.getLogger(__name__)


async def filter_content(text: str, confidence_threshold: float = 0.5) -> dict:
    """
    Filter educational content — remove irrelevant/noisy text.
    Uses Groq LLM when the trained model isn't available for speed.
    """
    tokenizer, model = get_filter_model()

    if model is None or tokenizer is None:
        # Fast path: use Groq to extract only educational content
        return await _groq_filter(text)

    # Slow path: trained DistilBERT model
    return await _model_filter(text, tokenizer, model, confidence_threshold)


async def _groq_filter(text: str) -> dict:
    """Fast Groq-based content filtering — removes noise, keeps educational content."""
    original_length = len(text)

    # For short text, just pass through — no need for Groq
    if len(text) < 500:
        return {
            "filtered_text": text,
            "original_length": original_length,
            "filtered_length": len(text),
            "removed_ratio": 0.0,
            "model_used": "passthrough_short",
        }

    try:
        from groq import AsyncGroq
        from config import GROQ_API_KEY

        client = AsyncGroq(api_key=GROQ_API_KEY)

        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational content filter. "
                        "Extract and return ONLY the educational, informative content from the given text. "
                        "Remove: headers, footers, page numbers, navigation menus, ads, repeated lines, disclaimers. "
                        "Preserve: all educational facts, explanations, definitions, examples. "
                        "Return only the cleaned text, no explanations."
                    ),
                },
                {"role": "user", "content": text[:4000]},
            ],
            temperature=0.1,
        )

        filtered = response.choices[0].message.content.strip()
        filtered_length = len(filtered)
        removed_ratio = round(1 - (filtered_length / max(original_length, 1)), 3)

        logger.info(
            f"Groq filter: {original_length} → {filtered_length} chars ({removed_ratio*100:.1f}% removed)"
        )

        return {
            "filtered_text": filtered,
            "original_length": original_length,
            "filtered_length": filtered_length,
            "removed_ratio": max(0.0, removed_ratio),
            "model_used": "groq_filter",
        }

    except Exception as e:
        logger.warning(f"Groq filter failed ({e}) — passthrough")
        return {
            "filtered_text": text,
            "original_length": original_length,
            "filtered_length": original_length,
            "removed_ratio": 0.0,
            "model_used": "passthrough_error",
        }


async def _model_filter(text: str, tokenizer, model, confidence_threshold: float) -> dict:
    """Trained DistilBERT-based content filtering."""
    try:
        import torch
        import torch.nn.functional as F

        original_length = len(text)
        chunks = _split_into_chunks(text)
        relevant_chunks = []

        for chunk in chunks:
            if not chunk.strip():
                continue
            inputs = tokenizer(
                chunk, truncation=True, padding="max_length", max_length=512, return_tensors="pt"
            )
            with torch.no_grad():
                outputs = model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)
                label = torch.argmax(probs, dim=-1).item()
                confidence = probs[0][label].item()

            if label == 1 and confidence >= confidence_threshold:
                relevant_chunks.append(chunk)

        filtered_text = "\n\n".join(relevant_chunks) if relevant_chunks else text
        filtered_length = len(filtered_text)
        removed_ratio = round(1 - (filtered_length / max(original_length, 1)), 3)

        logger.info(f"DistilBERT filter: {original_length} → {filtered_length} chars")

        return {
            "filtered_text": filtered_text,
            "original_length": original_length,
            "filtered_length": filtered_length,
            "removed_ratio": removed_ratio,
            "model_used": "trained_distilbert",
        }

    except Exception as e:
        logger.error(f"Filter model inference failed: {e} — passthrough")
        return {
            "filtered_text": text,
            "original_length": len(text),
            "filtered_length": len(text),
            "removed_ratio": 0.0,
            "model_used": "passthrough_error",
        }


def _split_into_chunks(text: str, max_chars: int = 400) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    sentences = text.replace(". ", ".\n").split("\n")
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += s + " "
        else:
            if current.strip():
                chunks.append(current.strip())
            current = s + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]
