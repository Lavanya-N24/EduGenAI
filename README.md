# 🎓 EduGenAI — AI-Powered Multilingual Educational Video Generator

> **Input any educational content → Get a fully narrated, multilingual video lesson with scenes, subtitles, adaptive quizzes, AI tutor, and progress tracking — generated in under 10 seconds.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Flutter](https://img.shields.io/badge/Frontend-Flutter-02569B?style=flat&logo=flutter)](https://flutter.dev)
[![Groq](https://img.shields.io/badge/LLM-Groq%20LLaMA%203.3-F55036?style=flat)](https://groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Table of Contents

- [Features](#-features)
- [Architecture Flow](#-architecture-flow)
- [Quick Start](#-quick-start)
- [Project Structure](#-project-structure)
- [API Reference](#-api-reference)
- [AI/ML Modules](#-aiml-modules)
- [Learning Modes](#-learning-modes)
- [Supported Languages](#-supported-languages-16)
- [Performance](#-performance)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎬 **Video Generation** | AI-composed scenes with avatar narration rendered via OpenCV + FFmpeg |
| 🌐 **16+ Languages** | Full TTS audio + on-screen text in Hindi, Tamil, Kannada, Arabic, etc. |
| 🎯 **3 Learning Modes** | Basic / Beginner / Advanced — LLM adjusts content depth automatically |
| 🧠 **Adaptive Quizzes** | MCQ quizzes generated per topic, difficulty auto-adjusts with score |
| 🤖 **AI Tutor** | Context-aware Groq-powered chat tutor using the generated content as RAG |
| 📊 **Analytics Dashboard** | Topic-level accuracy tracking, performance trend, weak/strong areas |
| 🔗 **Share & Download** | Unique share tokens, direct video download URLs, persistent video history |
| ⚡ **< 10s Generation** | Full pipeline parallelised with asyncio + ThreadPoolExecutor |

---

## 🏛️ Architecture Flow

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the complete **step-by-step data flow diagram**.

```
User Input ──► Summarize ──► LLM Scenes ──► TTS Audio ──► Video Render ──► Share
              (T5 model)    (Groq LLaMA)  (Edge TTS)   (CV2 + FFmpeg)
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.10+ | [python.org](https://python.org) |
| Flutter | 3.16+ | [flutter.dev](https://flutter.dev) |
| FFmpeg | 6.x+ | [ffmpeg.org](https://ffmpeg.org/download.html) |
| Tesseract OCR | 5.x | [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) |

### 1️⃣ Get a Free Groq API Key

1. Go to [https://console.groq.com](https://console.groq.com)
2. Create an account → **API Keys** → **Create Key**
3. Paste it into `backend/.env`

### 2️⃣ Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Add your Groq API key
echo GROQ_API_KEY=your_key_here >> .env

# Start the server
python main.py
```

- API Server → **http://localhost:8000**
- Interactive API Docs → **http://localhost:8000/docs**

### 3️⃣ Flutter App Setup

```bash
cd flutter_app

flutter pub get
flutter run -d chrome        # Web browser
flutter run                  # Android / iOS device
```

> **Android Emulator:** Change `baseUrl` in `lib/services/api_service.dart` to `http://10.0.2.2:8000`  
> **Physical Device:** Use your PC's LAN IP, e.g. `http://192.168.1.x:8000`

---

## 📁 Project Structure

```
EduGenAI/
│
├── ARCHITECTURE.md                   # 📐 Full system flow diagram (START HERE)
│
├── backend/                          # 🐍 Python FastAPI Backend
│   ├── main.py                       # App entry & router registration
│   ├── config.py                     # Env vars, paths, constants
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # 🔑 API keys (DO NOT COMMIT)
│   │
│   ├── routes/                       # HTTP Endpoints
│   │   ├── generate.py               # POST /api/generate/full-pipeline
│   │   ├── quiz.py                   # POST /api/quiz/generate & /submit
│   │   ├── tutor.py                  # POST /api/tutor/chat
│   │   ├── analytics.py             # GET  /api/analytics/{user_id}
│   │   └── sharing.py               # POST /api/share, GET /api/user/{id}/videos
│   │
│   ├── services/                     # Core AI/ML Modules
│   │   ├── ocr.py                    # Image/PDF → Text (Tesseract)
│   │   ├── summarizer_model.py       # Long text → Summary (T5)
│   │   ├── llm.py                    # Scene generation (Groq LLaMA 3.3)
│   │   ├── translation.py           # Multilingual (deep-translator)
│   │   ├── emotion.py               # Emotion detection (Groq)
│   │   ├── tts.py                    # Text-to-Speech (Edge TTS, 16+ langs)
│   │   ├── video.py                  # Video render (OpenCV + FFmpeg)
│   │   ├── subtitle.py              # SRT generator
│   │   ├── quiz_model.py            # Quiz generation (Groq)
│   │   ├── adaptive.py              # Adaptive difficulty engine
│   │   ├── sharing.py               # Share tokens & video history (JSON store)
│   │   ├── knowledge_base.py        # RAG knowledge retrieval
│   │   ├── document_reader.py       # DOCX / PPTX → Text
│   │   └── audio_input.py           # Audio → Text (Whisper)
│   │
│   ├── utils/
│   │   └── file_handler.py          # Upload file parsing
│   │
│   └── outputs/                      # Generated artefacts
│       ├── audio/                    # Per-scene MP3 files
│       ├── video/                    # Final MP4 files
│       └── subtitles/               # SRT files
│
├── flutter_app/                      # 📱 Flutter Frontend
│   ├── pubspec.yaml
│   └── lib/
│       ├── main.dart                 # App entry + theme + routing
│       ├── screens/
│       │   ├── home.dart             # Input, mode selector, language picker
│       │   ├── result.dart           # Video player, download, share
│       │   ├── quiz.dart             # Adaptive MCQ quiz
│       │   ├── tutor.dart            # AI tutor chat interface
│       │   ├── analytics.dart        # Learning dashboard
│       │   └── video_history.dart    # Past video library
│       ├── services/
│       │   └── api_service.dart      # All HTTP calls to backend
│       └── widgets/
│           └── video_player.dart     # Custom web-compatible video player
│
├── training/                         # Model training scripts
├── start.bat                         # One-click Windows launcher
└── README.md
```

---

## 🔌 API Reference

### Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate/full-pipeline` | **Main endpoint** — content → video |
| `POST` | `/api/generate/text-only` | Scene preview (no video render) |
| `POST` | `/api/generate/ocr` | Extract text from image/PDF |
| `GET`  | `/api/generate/languages` | List of supported language codes |

### Quiz & Learning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/quiz/generate` | Generate MCQ quiz from content |
| `POST` | `/api/quiz/submit` | Submit answers, get score + feedback |
| `POST` | `/api/tutor/chat` | Chat with the AI tutor |
| `GET`  | `/api/analytics/{user_id}` | User performance analytics |

### Sharing & History

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/share` | Create a shareable link token |
| `GET`  | `/api/share/{token}` | View shared video metadata |
| `GET`  | `/api/share/{token}/play` | Redirect to video file |
| `GET`  | `/api/user/{user_id}/videos` | User's full video history |

---

## 🧠 AI/ML Modules

| Module | Model / Library | Role |
|--------|----------------|------|
| **OCR** | Tesseract 5 + pdf2image | Image & PDF → raw text |
| **Document Reader** | python-docx, python-pptx | DOCX / PPTX → text |
| **Audio Transcription** | OpenAI Whisper | Audio/video → text |
| **Summarization** | T5 (local fine-tuned) | Long text → compact summary |
| **Scene Generation** | Groq LLaMA 3.3 70B | Structured scene scripts |
| **Emotion Detection** | Groq LLaMA 3.3 70B | Scene emotional tone |
| **Translation** | deep-translator (Google) | Localize scene text |
| **Text-to-Speech** | Microsoft Edge TTS | 16+ language audio narration |
| **Video Rendering** | OpenCV + FFmpeg | Frame composition + muxing |
| **Quiz Generation** | Groq LLaMA 3.3 70B | MCQ with difficulty levels |
| **AI Tutor** | Groq LLaMA 3.3 70B + RAG | Context-aware Q&A |
| **Adaptive Engine** | Custom sliding window | Auto-adjusts quiz difficulty |

---

## 🎯 Learning Modes

| Mode | Icon | Description | Scenes | Vocabulary |
|------|------|-------------|--------|-----------|
| **Basic** | 🌱 | Simplified overview, core ideas only | 3 | Simple |
| **Beginner** | 📘 | Balanced explanation with examples | 5 | Moderate |
| **Advanced** | 🔥 | Full technical depth, edge cases | 8 | Expert |

The selected mode is passed to the LLM system prompt, which adjusts content density, vocabulary complexity, and scene count automatically.

---

## 🌐 Supported Languages (16+)

| Code | Language | TTS | Script |
|------|----------|-----|--------|
| `en` | 🇬🇧 English | ✅ | Latin |
| `hi` | 🇮🇳 Hindi | ✅ | Devanagari |
| `ta` | 🇮🇳 Tamil | ✅ | Tamil |
| `te` | 🇮🇳 Telugu | ✅ | Telugu |
| `kn` | 🇮🇳 Kannada | ✅ | Kannada |
| `ml` | 🇮🇳 Malayalam | ✅ | Malayalam |
| `bn` | 🇮🇳 Bengali | ✅ | Bengali |
| `mr` | 🇮🇳 Marathi | ✅ | Devanagari |
| `fr` | 🇫🇷 French | ✅ | Latin |
| `es` | 🇪🇸 Spanish | ✅ | Latin |
| `de` | 🇩🇪 German | ✅ | Latin |
| `ja` | 🇯🇵 Japanese | ✅ | Hiragana/Kanji |
| `zh-cn` | 🇨🇳 Chinese | ✅ | Simplified Han |
| `ar` | 🇸🇦 Arabic | ✅ | Arabic |
| `ko` | 🇰🇷 Korean | ✅ | Hangul |
| `ru` | 🇷🇺 Russian | ✅ | Cyrillic |

Script-specific NotoSans fonts are automatically selected for correct on-screen rendering.

---

## ⚡ Performance

| Stage | Time (typical) |
|-------|---------------|
| Summarization (T5) | ~0.3s |
| Scene Generation (Groq) | ~1.2s |
| Emotion Detection (parallel) | ~0.8s |
| TTS Audio Generation | ~1.5s per scene |
| Video Rendering (OpenCV) | ~0.4s per scene |
| FFmpeg Muxing | ~0.2s |
| **Total (2-scene content)** | **~4–7s** |

> Parallelism via `asyncio.gather` and `ThreadPoolExecutor` ensures quiz generation and emotion detection run **concurrently** with the main pipeline.

---

## 📄 License

MIT License — free to use, modify and distribute.

---

## 👨‍💻 Author

Built as a **Final Year Major Project**  
*AI-Based Multilingual Animated Audio & Video Generator for Education*

> For architecture deep-dive, see **[ARCHITECTURE.md](ARCHITECTURE.md)**
