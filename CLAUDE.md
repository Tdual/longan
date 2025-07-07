# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Gen Movie is a PDF-to-video converter that transforms PDF slides into narrated Japanese videos using VOICEVOX text-to-speech with dialogue between 四国めたん (Shikoku Metan) and ずんだもん (Zundamon) characters.

## Key Commands

### Backend Development
```bash
# Run FastAPI backend (from project root)
uvicorn api.main:app --reload

# Install Python dependencies
pip install -r api/requirements.txt
```

### Frontend Development
```bash
# Run SvelteKit frontend (from frontend/ directory)
cd frontend
npm run dev

# Build frontend for production
npm run build

# Type checking
npm run check
```

### Docker Development
```bash
# Start all services (VOICEVOX, API, Frontend)
docker-compose up

# Rebuild containers
docker-compose build
```

### Testing and Video Generation
```bash
# Generate audio files
python scripts/generate_audio.py

# Create video from slides and audio
python scripts/create_video.py

# Test VOICEVOX connection
python scripts/test_voicevox.py
```

## Architecture Overview

### Core Flow
1. **PDF Upload** → FastAPI receives PDF with target duration (default: 10 minutes)
2. **Processing** → PDF converted to slide images, text extracted
3. **Dialogue Generation** → OpenAI API creates contextual dialogue based on slide content
4. **Audio Synthesis** → VOICEVOX generates Japanese speech for each dialogue line
5. **Video Assembly** → MoviePy combines slides and audio into final video

### Key Components

**Backend (`/api/`)**
- `main.py` - FastAPI server with async job processing
- `core/dialogue_generator.py` - AI dialogue generation with instruction history
- `core/audio_generator.py` - VOICEVOX integration (speakers: Metan=2, Zundamon=3)
- `core/video_creator.py` - Video assembly with slide transitions
- `core/katakana_converter.py` - English→Katakana conversion for proper pronunciation

**Frontend (`/frontend/`)**
- SvelteKit 5 with TypeScript
- Real-time job status polling
- Dialogue editor with regeneration support
- CSV import/export functionality

### Important Configuration

**Environment Variables (`.env`)**
- `OPENAI_API_KEY` - Required for dialogue generation
- `VOICEVOX_URL` - Default: http://localhost:50021 (Docker: http://voicevox:50021)

**VOICEVOX Speaker IDs**
- 2: 四国めたん (ノーマル)
- 3: ずんだもん (ノーマル)

### Data Directories
- `uploads/` - Uploaded PDF files
- `slides/` - Extracted slide images
- `audio/` - Generated audio files
- `output/` - Final video files
- `data/` - Dialogue JSON files

### Recent Features
- Target duration specification for video length control
- Slide-specific dialogue regeneration with context awareness
- Instruction history tracking to prevent repetitive regenerations
- English word to Katakana conversion for proper Japanese pronunciation