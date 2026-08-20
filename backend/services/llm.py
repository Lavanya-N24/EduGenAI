"""
EduGenAI - LLM Service (Scene Generation + Quiz + Tutor)
Uses Groq API for high-speed inference.
"""
import json
import logging
from groq import AsyncGroq

from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

# ── Configure Groq ──────────────────────────────────────────
client = AsyncGroq(api_key=GROQ_API_KEY)
MODEL_NAME = "openai/gpt-oss-120b"

# ── Scene Generation ───────────────────────────────────────
SCENE_SYSTEM_PROMPT = """You are an expert educational content designer. Your task is to transform
educational text into a structured scene-based video script.

LEARNING MODE INSTRUCTIONS:
- BASIC: Use very simple language (grade 5-6 level). Short sentences. Focus on 1-2 core concepts per scene. Use lots of analogies and everyday examples. Max 3 scenes.
- BEGINNER: Use clear, friendly language (grade 8-9 level). Moderate detail. 3-5 concepts per scene. Balanced explanations. 4-6 scenes.
- ADVANCED: Use precise, technical language. Include depth, nuances, and cross-topic connections. Challenge the learner with complex ideas. 5-8 scenes.

RULES:
1. Match the number of scenes and complexity to the learning mode above
2. Each scene must have a clear visual description for animation
3. Narration should match the mode's language complexity
4. Detect the emotional tone of each scene
5. Identify key concepts for each scene
6. Suggest background colors that match the mood
7. Return ONLY valid JSON. No markdown, no code blocks, no extra text."""

SCENE_USER_PROMPT = """INPUT TEXT:
{content}

TARGET LANGUAGE: {language}
LEARNING MODE: {learning_mode}

OUTPUT FORMAT (strict JSON):
{{
  "title": "Video title",
  "subject": "Subject area",
  "learning_mode": "{learning_mode}",
  "total_scenes": <number>,
  "scenes": [
    {{
      "scene_id": 1,
      "title": "Scene title",
      "narration": "What the narrator says (in {language})",
      "visual_description": "Describe the visual scene for animation",
      "emotion": "one of: neutral, curious, excited, serious, calm, surprised",
      "duration_seconds": 15,
      "key_concepts": ["concept1", "concept2"],
      "background_color": "#hexcolor",
      "animation_type": "one of: text_reveal, diagram, illustration, bullet_points, comparison, timeline"
    }}
  ],
  "summary": "2-3 sentence summary of the entire content"
}}"""


async def generate_scenes(content: str, language: str = "English", learning_mode: str = "beginner") -> dict:
    """
    Generate scene-based video script from educational content using Groq.
    learning_mode: 'basic' | 'beginner' | 'advanced'
    """
    # Normalize mode
    mode = learning_mode.lower().strip()
    if mode not in ("basic", "beginner", "advanced"):
        mode = "beginner"

    # Truncate content to avoid Groq 413 Request Too Large errors
    MAX_CONTENT_CHARS = 2000
    if len(content) > MAX_CONTENT_CHARS:
        logger.warning(f"Content too long ({len(content)} chars), truncating to {MAX_CONTENT_CHARS}")
        content = content[:MAX_CONTENT_CHARS]

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SCENE_SYSTEM_PROMPT},
                {"role": "user", "content": SCENE_USER_PROMPT.format(
                    content=content, language=language, learning_mode=mode
                )},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        scenes = json.loads(text)
        scenes["learning_mode"] = mode   # ensure it's in the response
        logger.info(f"Generated {scenes.get('total_scenes', 0)} scenes [{mode}] for: {scenes.get('title', 'Untitled')}")
        return scenes

    except Exception as e:
        logger.error(f"Scene generation failed: {e}")
        raise RuntimeError(f"Scene generation failed: {str(e)}")


# ── Quiz Generation ────────────────────────────────────────
QUIZ_SYSTEM_PROMPT = """You are an expert educational assessment designer. Generate a quiz based on the
following educational content.

RULES:
1. Generate multiple-choice questions (MCQs)
2. Each question should test understanding, not just memorization
3. Include questions at different difficulty levels (easy, medium, hard)
4. Each question must have exactly 4 options with one correct answer
5. Provide a brief explanation for the correct answer
6. Questions should be in the requested language
7. Return ONLY valid JSON."""

QUIZ_USER_PROMPT = """CONTENT:
{content}

DIFFICULTY LEVEL: {difficulty}
NUMBER OF QUESTIONS: {num_questions}
LANGUAGE: {language}

OUTPUT FORMAT (strict JSON):
{{
  "quiz_title": "Quiz title",
  "total_questions": {num_questions},
  "questions": [
    {{
      "id": 1,
      "question": "The question text",
      "options": ["A) option1", "B) option2", "C) option3", "D) option4"],
      "correct_answer": "A",
      "difficulty": "easy|medium|hard",
      "explanation": "Why this is the correct answer",
      "concept_tested": "The key concept being tested"
    }}
  ]
}}"""


async def generate_quiz(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    language: str = "English",
) -> dict:
    """
    Generate MCQ quiz from educational content using Groq.
    """
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                {"role": "user", "content": QUIZ_USER_PROMPT.format(
                    content=content,
                    num_questions=num_questions,
                    difficulty=difficulty,
                    language=language,
                )},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        quiz = json.loads(text)
        logger.info(f"Generated quiz: {quiz.get('quiz_title', 'Untitled')} with {num_questions} questions")
        return quiz

    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise RuntimeError(f"Quiz generation failed: {str(e)}")


# ── AI Tutor (Chat) ────────────────────────────────────────
TUTOR_SYSTEM_PROMPT = """You are EduBot, a friendly and patient AI tutor. You help students understand
educational concepts through conversation.

TEACHING STYLE:
- Use the Socratic method: guide students to answers with questions
- Break complex topics into simple steps
- Use analogies and real-world examples
- Be encouraging and supportive
- If the student is struggling, simplify further
- Respond in {language}

CONTEXT (the lesson content the student is learning):
{context}

STUDENT'S LEARNING HISTORY:
- Current difficulty level: {difficulty}
- Weak areas: {weak_areas}"""


async def tutor_chat(
    message: str,
    context: str,
    chat_history: list[dict] = None,
    difficulty: str = "medium",
    weak_areas: str = "none identified yet",
    language: str = "English",
) -> str:
    """
    AI Tutor chat response using Groq.
    """
    try:
        system_content = TUTOR_SYSTEM_PROMPT.format(
            context=context[:4000],
            difficulty=difficulty,
            weak_areas=weak_areas,
            language=language,
        )

        messages = [{"role": "system", "content": system_content}]
        
        if chat_history:
            for msg in chat_history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Tutor chat failed: {e}")
        return "I'm having trouble right now. Could you rephrase your question?"
