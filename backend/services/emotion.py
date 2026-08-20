"""
EduGenAI - Emotion Detection Service
Analyzes the emotional tone of text to drive emotion-aware TTS narration.

ML Algorithm: DistilBERT (distilled BERT)
- Architecture: 6-layer Transformer encoder (vs BERT's 12 layers)
- Training: Knowledge distillation from BERT — 40% smaller, 60% faster, 97% accuracy
- Fine-tuned on: Emotion dataset (joy, sadness, anger, fear, surprise, neutral)
- How it works: Text → Tokenize → DistilBERT embeddings → Classification head → Emotion label
"""
import logging

logger = logging.getLogger(__name__)

# Load emotion classification pipeline (downloads model on first run ~250MB)
# Model: bhadresh-savani/distilbert-base-uncased-emotion
# Trained on 6 emotions: joy, sadness, anger, fear, surprise, love
_emotion_classifier = None


def _get_classifier():
    """Lazy-load the emotion classifier to avoid startup delay."""
    global _emotion_classifier
    if _emotion_classifier is None:
        try:
            from transformers import pipeline  # imported lazily; optional dependency
        except Exception as e:
            raise RuntimeError(
                "Emotion model unavailable (missing 'transformers' and/or its dependencies)."
            ) from e

        logger.info("Loading emotion detection model (first time only)...")
        _emotion_classifier = pipeline(
            "text-classification",
            model="bhadresh-savani/distilbert-base-uncased-emotion",
            top_k=None,  # Return all emotion scores
        )
        logger.info("Emotion detection model loaded successfully.")
    return _emotion_classifier


# Map model's emotion labels to our TTS-compatible emotions
EMOTION_MAP = {
    "joy": "joy",
    "sadness": "sadness",
    "anger": "anger",
    "fear": "fear",
    "surprise": "surprise",
    "love": "joy",  # Map love → joy for TTS
}


async def detect_emotion(text: str) -> dict:
    """
    Detect the primary emotion in a piece of text.

    Args:
        text: Input text to analyze

    Returns:
        dict with primary emotion, confidence, and all scores
    """
    try:
        classifier = _get_classifier()

        # Truncate long text (DistilBERT max: 512 tokens)
        truncated = text[:500]

        results = classifier(truncated)[0]

        # Sort by score descending
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

        primary = sorted_results[0]
        emotion_label = EMOTION_MAP.get(primary["label"], "neutral")

        all_emotions = {
            EMOTION_MAP.get(r["label"], r["label"]): round(r["score"], 4)
            for r in sorted_results
        }

        logger.info(f"Detected emotion: {emotion_label} ({primary['score']:.2%})")

        return {
            "primary_emotion": emotion_label,
            "confidence": round(primary["score"], 4),
            "all_emotions": all_emotions,
        }

    except Exception as e:
        logger.error(f"Emotion detection failed: {e}")
        # Fall back to neutral if detection fails
        return {
            "primary_emotion": "neutral",
            "confidence": 1.0,
            "all_emotions": {"neutral": 1.0},
        }


async def detect_scene_emotions(scenes: dict) -> dict:
    """
    Detect emotions for all scenes and update scene data.

    Args:
        scenes: Scene data dict from LLM

    Returns:
        Scene data with AI-detected emotions
    """
    for scene in scenes.get("scenes", []):
        narration = scene.get("narration", "")
        if narration:
            emotion_result = await detect_emotion(narration)
            scene["detected_emotion"] = emotion_result["primary_emotion"]
            scene["emotion_confidence"] = emotion_result["confidence"]
            scene["emotion_scores"] = emotion_result["all_emotions"]

            # Use AI-detected emotion if LLM didn't provide one
            if not scene.get("emotion"):
                scene["emotion"] = emotion_result["primary_emotion"]

    logger.info(f"Detected emotions for {len(scenes.get('scenes', []))} scenes")
    return scenes
