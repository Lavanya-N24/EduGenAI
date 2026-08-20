# 📐 EduGenAI — System Architecture & Data Flow

> This document explains the complete end-to-end flow of the EduGenAI platform, from user input to final video delivery, step by step.

---

## 🗺️ High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Flutter App)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  Type    │  │  Upload  │  │  Select  │  │  Select Language   │  │
│  │  Text    │  │  File    │  │  Mode    │  │  (16+ supported)   │  │
│  │          │  │  PDF/IMG │  │ Basic /  │  │  en, hi, ta, kn..  │  │
│  │          │  │  DOCX    │  │ Beginner │  │                    │  │
│  │          │  │  PPTX    │  │ Advanced │  │                    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬───────────┘  │
│       └─────────────┴─────────────┴─────────────────┘              │
│                                │                                    │
│                     [ Generate Video Button ]                       │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    HTTP POST /api/generate/full-pipeline
                    (multipart/form-data)
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend (port 8000)                    │
│                         routes/generate.py                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
```

---

## 🔄 Step-by-Step Pipeline

### STEP 0 — Input Ingestion

```
┌────────────────────────────────────────────────────────┐
│  STEP 0: INPUT INGESTION                               │
│  utils/file_handler.py                                 │
│                                                        │
│  ┌──────────┐    ┌───────────────┐    ┌────────────┐  │
│  │ Raw Text │    │  File Upload  │    │  Output    │  │
│  │ (string) │    │               │    │            │  │
│  │          │    │  .pdf  ──► OCR│    │  Plain     │  │
│  │          │    │  .png  ──► OCR│    │  Text      │  │
│  │          │    │  .jpg  ──► OCR│    │  String    │  │
│  │          │    │  .docx ──► DR │    │            │  │
│  │          │    │  .pptx ──► DR │    │            │  │
│  │          │    │  .txt  ──► raw│    │            │  │
│  │          │    │  .mp3  ──► 🎤 │    │            │  │
│  └────┬─────┘    └───────┬───────┘    └─────┬──────┘  │
│       └──────────────────┘                  │         │
│                                             ▼         │
│              services/ocr.py (Tesseract + pdf2image)  │
│              services/document_reader.py (docx/pptx)  │
│              services/audio_input.py (Whisper)        │
└────────────────────────────────────────────────────────┘
                            │
                            ▼ raw_text
```

---

### STEP 1 — Content Filtering & Summarization

```
┌────────────────────────────────────────────────────────┐
│  STEP 1: FILTER + SUMMARIZE                            │
│                                                        │
│  raw_text                                              │
│      │                                                 │
│      ▼                                                 │
│  services/filter_model.py                              │
│  ┌─────────────────────────────┐                       │
│  │ Content Safety Filter       │                       │
│  │ Removes inappropriate text  │                       │
│  └─────────────────────────────┘                       │
│      │ filtered_text                                   │
│      ▼                                                 │
│  services/summarizer_model.py (T5 model)               │
│  ┌─────────────────────────────────────────┐           │
│  │  Long text → Compact educational summary│           │
│  │  Max tokens respected for LLM input     │           │
│  └─────────────────────────────────────────┘           │
│      │ summarized_text                                 │
└────────────────────────────────────────────────────────┘
                            │
                            ▼
```

---

### STEP 2 — Scene Generation (LLM)

```
┌────────────────────────────────────────────────────────────────┐
│  STEP 2: SCENE GENERATION                                      │
│  services/llm.py  ──  Groq API (LLaMA 3.3 70B)                │
│                                                                │
│  Input:  summarized_text + language_name + learning_mode       │
│                                                                │
│  System Prompt adapts by mode:                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 🌱 BASIC    → 3 scenes, simple vocab, core ideas only   │   │
│  │ 📘 BEGINNER → 5 scenes, moderate depth, with examples   │   │
│  │ 🔥 ADVANCED → 8 scenes, technical depth, edge cases     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                │
│  Output JSON structure:                                        │
│  {                                                             │
│    "title": "Photosynthesis",                                  │
│    "summary": "...",                                           │
│    "total_scenes": 5,                                          │
│    "scenes": [                                                 │
│      {                                                         │
│        "scene_id": 1,                                          │
│        "title": "What is Photosynthesis?",                     │
│        "narration": "...",                                     │
│        "key_concepts": ["chlorophyll", "sunlight"],            │
│        "emotion": "curious",                                   │
│        "duration": 8                                           │
│      }, ...                                                    │
│    ]                                                           │
│  }                                                             │
└────────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │         asyncio.gather    │
              ▼                           ▼
```

---

### STEP 2.1 & 3 — Quiz Generation + Emotion Detection (Parallel)

```
┌──────────────────────────────┐   ┌──────────────────────────────┐
│  STEP 2.1: QUIZ GENERATION   │   │  STEP 3: EMOTION DETECTION   │
│  services/quiz_model.py      │   │  services/emotion.py         │
│  (Groq LLaMA 3.3)            │   │  (Groq LLaMA 3.3)            │
│                              │   │                              │
│  Generates MCQ quiz from     │   │  Tags each scene with one    │
│  scene content:              │   │  emotional tone:             │
│  • 5-10 questions            │   │  neutral / curious /         │
│  • 4 options each            │   │  excited / serious /         │
│  • correct_answer field      │   │  calm / surprised / joy      │
│  • explanation field         │   │                              │
│  • difficulty: easy/med/hard │   │  Used to vary avatar          │
│                              │   │  expression in video         │
└──────────────┬───────────────┘   └──────────────┬───────────────┘
               │                                  │
               └──────────────┬───────────────────┘
                              │ (both complete)
                              ▼
```

---

### STEP 4 — Translation

```
┌────────────────────────────────────────────────────────┐
│  STEP 4: TRANSLATION                                   │
│  services/translation.py  (deep-translator / Google)   │
│                                                        │
│  If target_language != 'en':                           │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Each scene's narration text is translated       │  │
│  │  into the selected language                      │  │
│  │                                                  │  │
│  │  en → hi (Hindi / Devanagari)                    │  │
│  │  en → kn (Kannada script)                        │  │
│  │  en → ar (Arabic / RTL)                          │  │
│  │  en → zh-cn (Simplified Chinese)                 │  │
│  │  ... 16 languages total                          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  Output: scenes with translated narration text         │
└────────────────────────────────────────────────────────┘
                            │
                            ▼
```

---

### STEP 5 — Text-to-Speech Audio

```
┌────────────────────────────────────────────────────────┐
│  STEP 5: TEXT-TO-SPEECH                                │
│  services/tts.py  ──  Microsoft Edge TTS               │
│                                                        │
│  For each scene:                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  narration_text  ──►  Edge TTS voice lookup      │  │
│  │                                                  │  │
│  │  Language → Voice mapping examples:              │  │
│  │  'en'    → en-IN-NeerjaNeural                    │  │
│  │  'hi'    → hi-IN-SwaraNeural                     │  │
│  │  'ta'    → ta-IN-PallaviNeural                   │  │
│  │  'kn'    → kn-IN-SapnaNeural                     │  │
│  │  'ar'    → ar-SA-ZariyahNeural                   │  │
│  │  'ja'    → ja-JP-NanamiNeural                    │  │
│  │  ...                                             │  │
│  │                                                  │  │
│  │  Output: outputs/audio/scene_1.mp3               │  │
│  │          outputs/audio/scene_2.mp3  ...          │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                            │
                            ▼
```

---

### STEP 6 — Subtitle Generation

```
┌────────────────────────────────────────────────────────┐
│  STEP 6: SUBTITLE GENERATION                           │
│  services/subtitle.py                                  │
│                                                        │
│  Reads audio duration of each scene MP3                │
│  Generates timed SRT entries:                          │
│                                                        │
│  1                                                     │
│  00:00:00,000 --> 00:00:08,000                         │
│  What is Photosynthesis?                               │
│                                                        │
│  2                                                     │
│  00:00:08,000 --> 00:00:16,500                         │
│  Plants use sunlight to make food...                   │
│                                                        │
│  Output: outputs/subtitles/video_abc123.srt            │
└────────────────────────────────────────────────────────┘
                            │
                            ▼
```

---

### STEP 7 — Video Rendering

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 7: VIDEO RENDERING                                           │
│  services/video.py  ──  OpenCV + FFmpeg                            │
│                                                                    │
│  For each scene (parallel via ThreadPoolExecutor):                 │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                                                              │  │
│  │  1. Build slide frame (cv2.VideoWriter):                     │  │
│  │     • Gradient background (color varies by emotion)          │  │
│  │     • Scene title text (NotoSans font, script-aware)         │  │
│  │     • Narration text (wrapped, language-correct font)        │  │
│  │     • Avatar / talking head overlay                          │  │
│  │     • Animated mouth (clock-based open/close toggle)         │  │
│  │     • Key concept pills at bottom                            │  │
│  │                                                              │  │
│  │  2. Write frames at 24 FPS × audio_duration seconds          │  │
│  │     Output: scene_1_raw.mp4 (no audio)                       │  │
│  │                                                              │  │
│  │  3. Mux audio into video with FFmpeg:                        │  │
│  │     ffmpeg -i scene_1_raw.mp4 -i scene_1.mp3                 │  │
│  │            -c:v copy -c:a aac scene_1.mp4                    │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Concatenate all scene videos:                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ffmpeg -f concat -safe 0                                    │  │
│  │         -i scene_list.txt                                    │  │
│  │         -c copy                                              │  │
│  │         outputs/video/final_abc123.mp4                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Font selection per language:                                      │
│  kn/ta/te/ml → NotoSans-[Script]                                   │
│  hi/mr/bn    → NotoSans-Devanagari                                 │
│  ar          → NotoSansArabic  (RTL handled)                       │
│  zh/ja/ko    → NotoSansCJK                                         │
│  en/fr/es    → NotoSans (Latin)                                    │
└────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
```

---

### STEP 7.1 — Save to History & Create Share Token

```
┌────────────────────────────────────────────────────────┐
│  STEP 7.1: PERSIST & TOKENIZE                          │
│  services/sharing.py                                   │
│                                                        │
│  save_video_record(user_id, filename, title, ...)      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Generates UUID share token                      │  │
│  │  Appends to models/video_history.json:           │  │
│  │  {                                               │  │
│  │    "id": "uuid",                                 │  │
│  │    "user_id": "default_user",                    │  │
│  │    "filename": "final_abc123.mp4",               │  │
│  │    "title": "Photosynthesis",                    │  │
│  │    "share_token": "tok_xyz...",                  │  │
│  │    "duration": 42.5,                             │  │
│  │    "scenes": 5,                                  │  │
│  │    "language": "kn",                             │  │
│  │    "learning_mode": "beginner",                  │  │
│  │    "render_time": 4.2,                           │  │
│  │    "created_at": "2026-05-07T..."                │  │
│  │  }                                               │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
                            │
                            ▼
```

---

### STEP 8 — Response to Flutter

```
┌────────────────────────────────────────────────────────────────────┐
│  STEP 8: API RESPONSE                                              │
│                                                                    │
│  HTTP 200 JSON:                                                    │
│  {                                                                 │
│    "job_id": "uuid",                                               │
│    "status": "success",                                            │
│    "scenes": { ...LLM output... },                                 │
│    "quiz":   { ...MCQ questions... },                              │
│    "video": {                                                      │
│      "filename": "final_abc123.mp4",                               │
│      "url": "/outputs/video/final_abc123.mp4",                     │
│      "duration": 42.5,                                             │
│      "total_scenes": 5,                                            │
│      "render_time_s": 4.2,                                         │
│      "share_token": "tok_xyz...",                                  │
│      "video_record_id": "uuid"                                     │
│    },                                                              │
│    "subtitle": {                                                   │
│      "filename": "video_abc123.srt",                               │
│      "total_entries": 5                                            │
│    }                                                               │
│  }                                                                 │
└────────────────────────────────────────────────────────────────────┘
                            │
                 HTTP response to Flutter app
                            │
                            ▼
```

---

### STEP 9 — Flutter Result Screen

```
┌─────────────────────────────────────────────────────────────────────┐
│  STEP 9: RESULT SCREEN (Flutter)                                    │
│  screens/result.dart                                                │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  🎬 VIDEO PLAYER                              │  │
│  │         http://localhost:8000/outputs/video/final.mp4         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  📊 Stats: 5 scenes • 42.5s • 5 subtitles • 🔥 Advanced Mode        │
│                                                                     │
│  ┌────────────────┐  ┌────────────────┐                            │
│  │  📥 Download   │  │   🔗 Share     │                            │
│  │  Copy URL      │  │  Token → Link  │                            │
│  └────────────────┘  └────────────────┘                            │
│                                                                     │
│  🔥 Advanced Mode Complete! Ready to test your knowledge?           │
│                                                                     │
│  📋 Summary + Scene-by-scene breakdown                              │
│                                                                     │
│  ┌────────────────┐  ┌────────────────┐                            │
│  │  📝 Take Quiz  │  │  🤖 Ask Tutor  │                            │
│  └────────────────┘  └────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔁 Quiz & Adaptive Learning Flow

```
User takes Quiz
      │
      ▼
POST /api/quiz/submit  ──►  services/adaptive.py
      │
      ▼
┌─────────────────────────────────────────┐
│  Calculate score (correct / total × 100)│
│                                         │
│  score ≥ 80% → difficulty UP            │
│  score 50–79% → difficulty SAME         │
│  score < 50% → difficulty DOWN          │
└──────────────┬──────────────────────────┘
               │
               ▼
   Update models/user_progress.json
   (topic → attempts, avg_score, difficulty)
               │
               ▼
   Return:  score, feedback, recommendation,
            new_difficulty, weak_areas
```

---

## 🔗 Sharing Flow

```
Video Generated
      │
      ▼
POST /api/share
  { user_id, filename, title, duration }
      │
      ▼
services/sharing.py → generates UUID token
      │
      ▼
Public URL: GET /api/share/{token}
  → Returns video metadata (anyone can access)

Public Play: GET /api/share/{token}/play
  → HTTP 302 Redirect to actual MP4 file

User History: GET /api/user/{user_id}/videos
  → All past videos with share tokens, dates, modes
```

---

## 🧩 Component Dependency Map

```
                    ┌─────────────┐
                    │  main.py    │  ← FastAPI app, router registration
                    └──────┬──────┘
                           │ includes
         ┌─────────────────┼──────────────────┐
         ▼                 ▼                  ▼
   routes/generate    routes/quiz       routes/sharing
         │                 │                  │
         │ calls           │ calls            │ calls
         ▼                 ▼                  ▼
   services/llm      services/quiz_m    services/sharing
   services/tts      services/adaptive  (JSON store)
   services/video         │
   services/ocr      models/user_progress.json
   services/summarizer
   services/emotion
   services/translation
   services/subtitle
   services/knowledge_base
         │
         ▼
   config.py  ──  .env (GROQ_API_KEY, paths)
```

---

## 🗂️ Output File Structure

```
backend/outputs/
├── audio/
│   ├── scene_1_abc123.mp3        ← Per-scene TTS audio
│   ├── scene_2_abc123.mp3
│   └── ...
├── video/
│   ├── scene_1_abc123.mp4        ← Per-scene video (silent)
│   ├── scene_1_abc123_audio.mp4  ← Per-scene video + audio
│   ├── scene_list_abc123.txt     ← FFmpeg concat list
│   └── final_abc123.mp4          ← ✅ FINAL OUTPUT
└── subtitles/
    └── video_abc123.srt          ← Timed subtitle file

backend/models/
├── video_history.json            ← All user video records + share tokens
└── user_progress.json            ← Quiz performance per user
```

---

## ⚡ Performance Architecture

```
routes/generate.py:

  Step 1: summarize(text)                     ~0.3s  [sequential]
     │
  Step 2: generate_scenes(summary, lang, mode) ~1.2s  [sequential]
     │
  Step 2.1 + Step 3:
  asyncio.gather(
    generate_quiz(scenes),                    ~0.8s  ─┐ PARALLEL
    detect_emotions(scenes),                  ~0.8s  ─┘
  )                                          (net ~0.8s)
     │
  Step 4: translate_scenes(scenes, lang)      ~0.5s  [if non-English]
     │
  Step 5: generate_audio(scenes)              ~1.5s per scene
     │                                       [sequential per scene]
  Step 6: generate_subtitles(scenes)          ~0.1s
     │
  Step 7: generate_video(scenes)              ~0.4s per scene
     │                                       [ThreadPoolExecutor parallel]
     │    FFmpeg concat                       ~0.2s
     │
  Step 7.1: save_video_record(...)            ~0.01s
     │
  ✅ Response                      TOTAL: ~4–8s (2-3 scene content)
```

---

*Generated by EduGenAI documentation system.*  
*See [README.md](README.md) for setup and installation instructions.*
