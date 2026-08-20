"""
EduGenAI - Summarization Service (Fast Groq Path)

Strategy:
  1. Check if the trained T5-small model is available.
  2. If YES → use it (accurate, but slow CPU beam-search).
  3. If NO  → use Groq to summarize in < 1s (fast path).
"""
import logging
from services.model_loader import get_summarizer_model

logger = logging.getLogger(__name__)

MAX_INPUT_TOKENS  = 512
MAX_OUTPUT_TOKENS = 128
NUM_BEAMS         = 4


async def summarize_text(text: str) -> dict:
    """
    Summarize long educational text.
    Uses Groq LLM when the trained model isn't available for speed.
    """
    tokenizer, model = get_summarizer_model()

    if model is None or tokenizer is None:
        return await _groq_summarize(text)

    return await _t5_summarize(text, tokenizer, model)


async def _groq_summarize(text: str) -> dict:
    """Fast Groq-based summarization — runs in < 1 second."""
    original_length = len(text)

    # For very short text, no need to summarize
    if len(text) < 300:
        return {
            "summary": text,
            "original_length": original_length,
            "summary_length": len(text),
            "compression_ratio": 0.0,
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
                        "You are an expert educational content summarizer. "
                        "Summarize the given text into clear, concise key points. "
                        "Preserve all important facts, definitions, and concepts. "
                        "Return a well-structured summary of 2-4 paragraphs. "
                        "No bullet points — write in flowing prose."
                    ),
                },
                {"role": "user", "content": text[:4000]},
            ],
            temperature=0.3,
        )

        summary = response.choices[0].message.content.strip()
        summary_length = len(summary)
        compression_ratio = round(1 - (summary_length / max(original_length, 1)), 3)

        logger.info(
            f"Groq summarize: {original_length} → {summary_length} chars "
            f"({compression_ratio*100:.1f}% compression)"
        )

        return {
            "summary": summary,
            "original_length": original_length,
            "summary_length": summary_length,
            "compression_ratio": max(0.0, compression_ratio),
            "model_used": "groq_summarizer",
        }

    except Exception as e:
        logger.warning(f"Groq summarization failed ({e}) — truncation fallback")
        return {
            "summary": text[:800],
            "original_length": original_length,
            "summary_length": min(800, original_length),
            "compression_ratio": 0.0,
            "model_used": "truncation_fallback",
        }


async def _t5_summarize(text: str, tokenizer, model) -> dict:
    """Trained T5-small summarization."""
    try:
        import torch
        import asyncio

        original_length = len(text)
        chunks = _chunk_text_for_t5(text, tokenizer)
        chunk_summaries = []

        loop = asyncio.get_event_loop()

        def _run_t5(chunk):
            input_text = "summarize: " + chunk
            inputs = tokenizer(input_text, return_tensors="pt", truncation=True, max_length=MAX_INPUT_TOKENS)
            with torch.no_grad():
                outputs = model.generate(
                    inputs["input_ids"],
                    max_length=MAX_OUTPUT_TOKENS,
                    num_beams=NUM_BEAMS,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                )
            return tokenizer.decode(outputs[0], skip_special_tokens=True)

        for chunk in chunks:
            summary_chunk = await loop.run_in_executor(None, _run_t5, chunk)
            chunk_summaries.append(summary_chunk)

        if len(chunk_summaries) > 1:
            merged = " ".join(chunk_summaries)
            summary_text = await loop.run_in_executor(None, _run_t5, merged[:1000])
        else:
            summary_text = chunk_summaries[0] if chunk_summaries else text[:500]

        summary_length = len(summary_text)
        compression_ratio = round(1 - (summary_length / max(original_length, 1)), 3)

        logger.info(f"T5 summarize: {original_length} → {summary_length} chars")

        return {
            "summary": summary_text,
            "original_length": original_length,
            "summary_length": summary_length,
            "compression_ratio": compression_ratio,
            "model_used": "trained_t5",
        }

    except Exception as e:
        logger.error(f"T5 summarizer failed: {e}")
        return await _groq_summarize(text)


def _chunk_text_for_t5(text: str, tokenizer, max_tokens: int = 512) -> list[str]:
    sentences = text.replace(". ", ".\n").split("\n")
    chunks, current_tokens, current_text = [], 0, ""
    for sentence in sentences:
        token_count = len(tokenizer.encode(sentence, add_special_tokens=False))
        if current_tokens + token_count > (max_tokens - 10):
            if current_text.strip():
                chunks.append(current_text.strip())
            current_text = sentence + " "
            current_tokens = token_count
        else:
            current_text += sentence + " "
            current_tokens += token_count
    if current_text.strip():
        chunks.append(current_text.strip())
    return chunks if chunks else [text[:1000]]
