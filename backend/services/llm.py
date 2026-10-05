"""
EduGenAI - Hybrid LLM Service

Groq is the lesson director.

The LLM returns:
- complete lesson
- 5-7 scenes for beginner mode
- 10-16 second narration per scene
- content_type:
    rich     -> real image + animated annotations
    process  -> Manim equations/process diagrams
    narrative -> image-based scene
- actions for Manim
- image_keywords for real visual search
"""

import json
import re
import logging
import asyncio

from groq import Groq
import google.generativeai as genai

from config import GROQ_API_KEY, GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Active, verified Groq models
# NOTE: openai/gpt-oss-120b is a reasoning model that outputs thinking text
# before JSON, causing parse failures. Use the standard model first.
_GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
]

# Active Google Gemini models
_GEMINI_MODELS = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.7-flash",
    "gemini-flash-lite-latest",
]


def _sync_groq_call(messages: list, max_tokens: int, temperature: float, is_json: bool) -> str:
    """Synchronous Groq call executed in a thread pool for Windows stability."""
    client = Groq(api_key=GROQ_API_KEY)
    last_err = None
    kwargs = {
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    for model in _GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            msg = response.choices[0].message
            content = (msg.content or "").strip()

            # Reasoning models (e.g. openai/gpt-oss-120b) may output thinking text
            # before the JSON. For JSON requests, extract only the JSON block.
            if is_json and content:
                first_brace = content.find("{")
                last_brace = content.rfind("}")
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    content = content[first_brace:last_brace + 1]

            if not content and getattr(msg, "reasoning", None):
                content = (msg.reasoning or "").strip()
            if not content:
                raise ValueError(f"Model {model} returned empty content")
            logger.info("Groq model used successfully: %s", model)
            return content
        except Exception as e:
            err_str = str(e)
            logger.warning("Groq model %s failed: %s. Trying next...", model, err_str[:120])
            last_err = e
            continue
    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


async def _call_groq(
    messages: list,
    max_tokens: int = 3000,
    temperature: float = 0.4,
    is_json: bool = True,
) -> str:
    """Run Groq call safely in a thread."""
    return await asyncio.to_thread(_sync_groq_call, messages, max_tokens, temperature, is_json)


async def _call_gemini(system_prompt: str, user_prompt: str, is_json: bool = True) -> str:
    """Call Google Gemini 3.6 Flash with structured JSON or free text output."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured.")

    genai.configure(api_key=GEMINI_API_KEY)
    last_err = None

    gen_config = {"temperature": 0.4}
    if is_json:
        gen_config["response_mime_type"] = "application/json"

    for model_name in _GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt if system_prompt else None,
                generation_config=gen_config,
            )
            res = await asyncio.to_thread(model.generate_content, user_prompt)
            if res and res.text:
                logger.info("✨ Google Gemini model used successfully: %s", model_name)
                return res.text.strip()
        except Exception as e:
            logger.warning("Gemini model %s failed: %s. Trying next...", model_name, str(e)[:120])
            last_err = e
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


async def _call_llm(
    messages: list,
    max_tokens: int = 4000,
    temperature: float = 0.4,
    is_json: bool = True,
) -> str:
    """Try ultra-fast Groq LPU first (<2s), then fallback to Google Gemini."""
    if GROQ_API_KEY:
        try:
            res = await _call_groq(messages, max_tokens=max_tokens, temperature=temperature, is_json=is_json)
            if is_json:
                _parse_json_robust(res)  # Verify parseable before returning
            return res
        except Exception as groq_err:
            logger.warning("Groq failed (%s). Falling back to Gemini...", str(groq_err)[:120])

    if GEMINI_API_KEY:
        try:
            sys_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
            user_msg = "\n\n".join(
                m.get("content", "") for m in messages if m.get("role") in ("user", "assistant")
            )
            return await _call_gemini(sys_msg, user_msg, is_json=is_json)
        except Exception as gem_err:
            logger.warning("Gemini fallback also failed: %s", gem_err)

    raise RuntimeError("All LLM providers failed.")


SCENE_SYSTEM_PROMPT = r"""
You are EduGenAI's master teacher, curriculum director, and expert storyboard planner.

Your mission: Create a COMPLETE, logically flowing, age-appropriate educational video lesson.
The lesson must feel like a real expert teacher walking a student through a topic step by step.

==================================================
LEVEL-BASED NARRATION RULES
==================================================
📗 BASIC Mode (for children / absolute beginners):
  - Simple everyday words, fun real-world analogies.
  - Narration: 16-25 words per scene.
  - Tone: Friendly, wonder-filled, encouraging.

📘 BEGINNER Mode (school students, general learners):
  - Simple-to-moderate vocabulary with key terms defined.
  - Explain mechanisms clearly (how it works, why it happens).
  - Narration: 22-32 words per scene.
  - Tone: Curious, enthusiastic, educational.

📕 ADVANCED Mode (university students, professionals):
  - Precise scientific/technical terminology and mechanisms.
  - Narration: 30-45 words per scene.
  - Tone: Professional, precise, analytical.

==================================================
PEDAGOGICAL SCENE FLOW
==================================================
Adapt the scenes to the requested scene count:
  - Scene 1: Hook & Introduction (why it matters).
  - Middle Scenes: Core Concepts & Mechanisms step-by-step.
  - Final Scene: Summary & real-world takeaway.

==================================================
LANGUAGE RULES
==================================================
- Narration MUST be in the TARGET LANGUAGE.
- image_keywords and visual_description MUST ALWAYS be in ENGLISH.
- Return ONLY valid JSON starting with { and ending with }. Do NOT output reasoning or preamble.
"""


# Level-specific instruction strings injected into the user prompt dynamically
_LEVEL_INSTRUCTIONS = {
    "basic": (
        "BASIC LEVEL — Write like you are teaching a 10-year-old:\n"
        "- Use ONLY simple everyday words. NO scientific jargon.\n"
        "- Use fun real-life analogies (e.g., ‘Roots are like straws’, ‘Blockchain is like a shared notebook’).\n"
        "- Narration: 18-28 words per scene. Very short, punchy, memorable.\n"
        "- Focus on WHAT it is and WHY it is cool. Skip formulas and equations.\n"
        "- Tone: Friendly, fun, wonder-filled. Like a Sesame Street teacher."
    ),
    "beginner": (
        "BEGINNER LEVEL — Write for a curious school/college student:\n"
        "- Use simple-to-moderate vocabulary. Introduce key terms and briefly define them.\n"
        "- Explain mechanisms clearly: how does it work, why does it happen?\n"
        "- Narration: 22-32 words per scene. Clear, natural, flowing sentences.\n"
        "- You may mention 1 simple formula or equation. Do not derive it deeply.\n"
        "- Tone: Enthusiastic, educational, like a good YouTube explainer."
    ),
    "advanced": (
        "ADVANCED LEVEL — Write for university students or professionals:\n"
        "- Use precise scientific/technical language. Assume domain knowledge.\n"
        "- Explain at molecular/atomic/algorithmic/mathematical level. Include cause-and-effect chains.\n"
        "- Narration: 30-45 words per scene. Detailed, analytical, precise.\n"
        "- Include relevant equations, chemical formulas, data structures, or theoretical models.\n"
        "- Explain WHY at a mechanistic level, not just WHAT.\n"
        "- Tone: Professional, precise, like a university lecture or research explainer."
    ),
}

_LEVEL_SCENE_COUNTS = {
    "basic":    {"count": 3,  "min_secs": 25,  "words": "16-25"},
    "beginner": {"count": 4,  "min_secs": 36,  "words": "22-32"},
    "advanced": {"count": 5,  "min_secs": 50,  "words": "30-45"},
}


SCENE_USER_PROMPT = r"""
TOPIC / SOURCE CONTENT:
{content}

{research_context}

TARGET LANGUAGE: {language}
LEARNING MODE: {learning_mode}

=== LEVEL-SPECIFIC NARRATION DEPTH FOR THIS LESSON ===
{level_instructions}

=== REQUIRED SCENE FLOW ===
Follow the universal 7-step pedagogical flow from the system prompt, adapted to this topic.
Scene 1 must be the HOOK (why it matters, real-world relevance).
Scene 2 must define the core concept simply.
Middle scenes must show the MECHANISM step-by-step.
Second-to-last scene must show OUTPUTS/RESULTS.
Last scene must be SUMMARY + real-world impact.

Return ONLY this JSON (no extra text outside JSON):

{{
  "title": "Clear Educational Title",
  "subject": "Subject Area",
  "learning_mode": "{learning_mode}",
  "content_type": "rich",
  "estimated_total_duration": 90,
  "total_scenes": {scene_count},
  "scenes": [
    {{
      "scene_id": 1,
      "title": "Hook — why this topic matters",
      "transition_explanation": "Opening hook introducing the concept.",
      "narration": "Engaging narration in {language} at {learning_mode} level depth.",
      "visual_description": "Detailed visual description in English.",
      "visual_continuity": "Wide establishing shot in English.",
      "scene_visual_type": "image",
      "emotion": "curious",
      "duration_seconds": 13,
      "image_keywords": ["ExactPersonOrTopicName", "descriptive english keyword"],
      "actions": [],
      "equation": ""
    }}
  ],
  "summary": "One-sentence summary of the entire lesson."
}}

Rules:
- Generate {scene_count} scenes so total narration is at least {min_seconds} seconds.
- Narration word count per scene: {narration_words} words.
- For image scenes: actions=[] and equation="".
- For manim scenes: image_keywords=[].
- scene_visual_type must be one of: image, manim, image+manim.
- image_keywords MUST ALWAYS BE IN ENGLISH. Use precise, searchable terms:
  * For people: use their full name as the first keyword (e.g. "Shivaji", "Newton", "Marie Curie")
  * For places: use the official English name (e.g. "Raigad Fort", "Amazon rainforest")
  * For concepts: use standard scientific/educational terms (e.g. "photosynthesis diagram", "DNA double helix")
- visual_description MUST ALWAYS BE IN ENGLISH.
- Include transition_explanation and visual_continuity in every scene.
- Return ONLY valid JSON, nothing else.
"""



def _parse_json_robust(raw: str) -> dict:
    """
    Robust JSON parser that handles:
    - Markdown code fences (```json ... ```)
    - Unescaped newlines/tabs inside strings
    - Truncated JSON responses with unclosed strings, objects, or arrays
    - Trailing commas before closing braces
    """
    text = (raw or "").strip()
    if not text:
        raise RuntimeError("LLM returned an empty response string.")

    # Strip markdown codeblocks
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Find the starting brace of JSON to ignore preamble thoughts
    first_brace = text.find("{")
    if first_brace != -1:
        text = text[first_brace:]

    # First attempt: direct json.loads
    try:
        return json.loads(text)
    except Exception:
        pass

    # Extract outermost JSON object if surrounded by extra text
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            text = candidate

    # Repair unclosed strings and structures
    repaired = text
    # Clean trailing comma inside arrays/objects: ,] -> ] and ,} -> }
    repaired = re.sub(r",\s*([\]\}])", r"\1", repaired)

    # Check if a string was left unclosed (odd number of unescaped quotes)
    # Count unescaped double quotes
    quotes = len(re.findall(r'(?<!\\)"', repaired))
    if quotes % 2 != 0:
        repaired += '"'

    # Close open brackets / braces in reverse order
    stack = []
    in_string = False
    escaped = False
    for char in repaired:
        if escaped:
            escaped = False
            continue
        if char == '\\':
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in ('{', '['):
            stack.append(char)
        elif char == '}':
            if stack and stack[-1] == '{':
                stack.pop()
        elif char == ']':
            if stack and stack[-1] == '[':
                stack.pop()

    # Append matching closing brackets
    closing = ""
    for b in reversed(stack):
        if b == '{':
            closing += "}"
        elif b == '[':
            closing += "]"
    repaired += closing

    try:
        return json.loads(repaired)
    except Exception as e:
        logger.error("JSON repair failed on: %s", (raw or "")[:300])
        raise RuntimeError(f"Failed to parse LLM JSON output: {e}") from e


async def generate_scenes(
    content: str,
    language: str = "English",
    learning_mode: str = "beginner",
    research_context: str = "",
) -> dict:

    mode = (
        learning_mode
        .lower()
        .strip()
    )

    if mode not in (
        "basic",
        "beginner",
        "advanced",
    ):
        mode = "beginner"

    content = str(
        content or ""
    ).strip()

    if not content:
        raise RuntimeError(
            "No educational topic/content was provided."
        )

    # Keep enough source material for a real lesson.
    content = content[:2500]

    # ── Redis Cache Check ────────────────────────────────────
    from services.cache import get_cached_json, set_cached_json, make_cache_key
    cache_key = make_cache_key("scenes", language, mode, content[:120])
    cached_data = await get_cached_json(cache_key)
    if cached_data and cached_data.get("scenes"):
        logger.info("⚡ Returning cached lesson scenes for [%s]", content[:40])
        return cached_data

    formatted_research = (
        f"\n--- BACKGROUND RESEARCH CONTEXT ---\n{research_context.strip()}\n-----------------------------------\n"
        if research_context.strip()
        else ""
    )

    level_cfg = _LEVEL_SCENE_COUNTS.get(mode, _LEVEL_SCENE_COUNTS["beginner"])
    level_instr = _LEVEL_INSTRUCTIONS.get(mode, _LEVEL_INSTRUCTIONS["beginner"])

    raw = await _call_llm(
        messages=[
            {
                "role": "system",
                "content": SCENE_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": SCENE_USER_PROMPT.format(
                    content=content,
                    research_context=formatted_research,
                    language=language,
                    learning_mode=mode,
                    level_instructions=level_instr,
                    scene_count=level_cfg["count"],
                    min_seconds=level_cfg["min_secs"],
                    narration_words=level_cfg["words"],
                ),
            },
        ],
        max_tokens=2200,
        temperature=0.4,
    )

    data = _parse_json_robust(raw)

    data["learning_mode"] = mode

    scenes = data.get(
        "scenes",
        [],
    )

    if not scenes:
        raise RuntimeError(
            "Groq returned no scenes."
        )

    for i, scene in enumerate(
        scenes
    ):

        scene["scene_id"] = i + 1

        scene.setdefault(
            "title",
            f"Scene {i + 1}",
        )

        scene.setdefault(
            "narration",
            "",
        )

        scene.setdefault(
            "visual_description",
            scene["narration"],
        )

        scene.setdefault(
            "emotion",
            "neutral",
        )

        scene.setdefault(
            "duration_seconds",
            12,
        )

        scene.setdefault(
            "key_concepts",
            [],
        )

        scene.setdefault(
            "image_keywords",
            [],
        )

        scene.setdefault(
            "actions",
            [],
        )

        scene.setdefault(
            "equation",
            "",
        )

        scene.setdefault(
            "manim_visual",
            "",
        )

        scene.setdefault(
            "scene_visual_type",
            "image",
        )

        # Keep rendering times realistic.
        try:
            d = float(
                scene["duration_seconds"]
            )
        except Exception:
            d = 12.0

        scene["duration_seconds"] = max(
            8,
            min(
                int(round(d)),
                20,
            ),
        )

    data["total_scenes"] = len(
        scenes
    )

    # ── Fast scene count check ────────────────────────────────────────────────
    MIN_SCENES = 3
    if len(scenes) < MIN_SCENES:
        logger.warning(
            "LLM returned only %d scenes for '%s'. Retrying with strict count prompt...",
            len(scenes), data.get("title", ""),
        )
        try:
            strict_prompt = (
                SCENE_USER_PROMPT.format(
                    content=content,
                    research_context=formatted_research,
                    language=language,
                    learning_mode=mode,
                    level_instructions=level_instr,
                    scene_count=level_cfg["count"],
                    min_seconds=level_cfg["min_secs"],
                    narration_words=level_cfg["words"],
                )
                + f"\n\nCRITICAL: You MUST return EXACTLY {MIN_SCENES} to 8 scenes. "
                  "If topic seems simple, add: intro scene, definition, mechanism, "
                  "real-world example, equation/formula, and summary. "
                  "Every scene narration must be 25-45 words. Do NOT return fewer than "
                  f"{MIN_SCENES} scenes under any circumstance."
            )
            raw2 = await _call_llm(
                messages=[
                    {"role": "system", "content": SCENE_SYSTEM_PROMPT},
                    {"role": "user", "content": strict_prompt},
                ],
                max_tokens=2200,
                temperature=0.3,
            )
            data2 = _parse_json_robust(raw2)
            scenes2 = data2.get("scenes", [])
            if len(scenes2) >= len(scenes):
                scenes = scenes2
                data["scenes"] = scenes
                data["total_scenes"] = len(scenes)
                logger.info("Retry returned %d scenes.", len(scenes))
        except Exception as retry_err:
            logger.warning("Scene retry failed: %s. Padding existing scenes.", retry_err)

    # If still too few, pad by duplicating & expanding existing scenes
    if len(scenes) < MIN_SCENES and scenes:
        import copy
        expansions = [
            "Let's explore this concept in greater detail with a real-world example.",
            "Now let's look at the key mechanism behind this process step by step.",
            "Consider how this knowledge applies to everyday life and modern technology.",
            "Let's summarize the key ideas and reflect on their lasting significance.",
        ]
        base = scenes[:]
        extra_idx = 0
        while len(scenes) < MIN_SCENES and extra_idx < len(expansions):
            src_scene = copy.deepcopy(base[extra_idx % len(base)])
            src_scene["scene_id"] = len(scenes) + 1
            src_scene["narration"] = expansions[extra_idx]
            src_scene["title"] = f"Deep Dive {extra_idx + 1}"
            src_scene["duration_seconds"] = 12
            scenes.append(src_scene)
            extra_idx += 1
        data["scenes"] = scenes
        data["total_scenes"] = len(scenes)
        logger.info("Padded to %d scenes.", len(scenes))
    # ── End scene guarantee ──────────────────────────────────────────────────────

    logger.info(
        "Generated %d scenes [%s / %s] for %s",
        len(scenes),
        mode,
        data.get(
            "content_type",
            "rich",
        ),
        data.get(
            "title",
            "Untitled",
        ),
    )

    if data and data.get("scenes"):
        await set_cached_json(cache_key, data, ttl_seconds=86400)

    return data


# ------------------------------------------------------------
# Quiz
# ------------------------------------------------------------

QUIZ_SYSTEM_PROMPT = r"""
You are an expert educational assessment designer.

Create MCQs from the provided educational content.

Rules:
- exactly 4 options
- exactly one correct answer
- test understanding
- include easy, medium and hard when appropriate
- provide a short explanation
- use the requested language
- return ONLY valid JSON
"""

QUIZ_USER_PROMPT = r"""
CONTENT:
{content}

DIFFICULTY:
{difficulty}

NUMBER OF QUESTIONS:
{num_questions}

LANGUAGE:
{language}

Return:

{{
  "quiz_title": "Quiz title",
  "total_questions": {num_questions},
  "questions": [
    {{
      "id": 1,
      "question": "Question",
      "options": [
        "A) option 1",
        "B) option 2",
        "C) option 3",
        "D) option 4"
      ],
      "correct_answer": "A",
      "difficulty": "easy",
      "explanation": "Explanation",
      "concept_tested": "Concept"
    }}
  ]
}}
"""


async def generate_quiz(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium",
    language: str = "English",
) -> dict:

    raw = await _call_groq(
        messages=[
            {
                "role": "system",
                "content": QUIZ_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": QUIZ_USER_PROMPT.format(
                    content=content,
                    num_questions=num_questions,
                    difficulty=difficulty,
                    language=language,
                ),
            },
        ],
        max_tokens=1024,
        temperature=0.6,
    )

    return json.loads(raw)


# ------------------------------------------------------------
# Tutor
# ------------------------------------------------------------

TUTOR_SYSTEM_PROMPT = r"""
You are EduBot, a friendly educational tutor.

Explain concepts step by step.
Use simple analogies and examples.
Use the Socratic method when useful.
Be encouraging.
Respond in {language}.

Lesson context:
{context}

Difficulty:
{difficulty}

Weak areas:
{weak_areas}
"""


async def tutor_chat(
    message: str,
    context: str = None,
    chat_history: list[dict] = None,
    difficulty: str = "medium",
    weak_areas: str = "none identified yet",
    language: str = "English",
) -> str:
    safe_context = str(context or "General science and educational studies")[:5000]
    
    messages = [
        {
            "role": "system",
            "content": TUTOR_SYSTEM_PROMPT.format(
                context=safe_context,
                difficulty=difficulty,
                weak_areas=weak_areas,
                language=language,
            ),
        }
    ]

    for msg in (
        chat_history or []
    )[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    try:
        return await _call_llm(
            messages=messages,
            max_tokens=1024,
            temperature=0.65,
            is_json=False,
        )
    except Exception as e:
        logger.error(f"Tutor chat LLM call failed: {e}")
        return (
            f"Hello! Regarding **{message}** in the context of **{safe_context[:100]}**:\n\n"
            f"Key concept to remember: Every system operates through inputs, transformations, and outputs. "
            f"In this topic, focus on how the core elements interact and support one another step-by-step. "
            f"Feel free to ask for a specific definition, example, or step-by-step breakdown!"
        )


# ------------------------------------------------------------
# Rich visual layout
# ------------------------------------------------------------

RICH_LAYOUT_SYSTEM_PROMPT = r"""
You are an educational visual designer.

Create a clean annotated visual layout for a science lesson.

Rules:
- topic_title: maximum 3 words, uppercase
- topic_subtitle: one short sentence
- background_search_query: specific real-world image search phrase
- annotations: 4-6 useful labels
- process_steps: 4-6 steps
- inset_panel: useful close-up/detail image
- chapter_tabs: 3-5 short chapters
- labels must describe real concepts from the lesson
- never invent irrelevant objects
- return ONLY JSON
"""

RICH_LAYOUT_USER_PROMPT = r"""
TOPIC:
{topic}

SUBJECT:
{subject}

SCENE NARRATIONS:
{narrations}

Return:

{{
  "topic_title": "TOPIC",
  "topic_subtitle": "One short sentence.",
  "background_search_query": "specific real-world educational photo search",
  "annotations": [
    {{
      "label": "SUNLIGHT",
      "sublabel": "Light provides energy.",
      "position": "top-left",
      "arrow_to": "center-top"
    }}
  ],
  "process_steps": [
    "First step",
    "Second step",
    "Third step",
    "Fourth step"
  ],
  "inset_panel": {{
    "title": "DETAIL VIEW",
    "image_query": "specific close-up search",
    "labels": ["label1", "label2"]
  }},
  "chapter_tabs": [
    "Overview",
    "Inputs",
    "Process",
    "Products"
  ]
}}
"""


async def generate_rich_layout(
    scenes: dict,
) -> dict:

    topic = scenes.get(
        "title",
        "Educational Topic",
    )

    subject = scenes.get(
        "subject",
        "Science",
    )

    narrations = "\n".join(
        f"Scene {s.get('scene_id', i + 1)}: "
        f"{s.get('narration', '')}"
        for i, s in enumerate(
            scenes.get(
                "scenes",
                [],
            )[:7]
        )
    )

    try:

        raw = await _call_groq(
            messages=[
                {
                    "role": "system",
                    "content": RICH_LAYOUT_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": RICH_LAYOUT_USER_PROMPT.format(
                        topic=topic,
                        subject=subject,
                        narrations=narrations,
                    ),
                },
            ],
            max_tokens=1024,
            temperature=0.4,
        )

        return json.loads(raw)

    except Exception as exc:

        logger.warning(
            "Rich layout generation failed: %s",
            exc,
        )

        return {
            "topic_title": str(
                topic
            ).upper()[:20],
            "topic_subtitle": (
                f"Learn about {topic}."
            ),
            "background_search_query": (
                f"{topic} educational science"
            ),
            "annotations": [],
            "process_steps": [],
            "inset_panel": {
                "title": "",
                "image_query": "",
                "labels": [],
            },
            "chapter_tabs": [
                "Overview"
            ],
        }
