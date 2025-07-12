# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

longan (formerly Gen Movie) is a PDF-to-video converter that transforms PDF slides into narrated Japanese videos using VOICEVOX text-to-speech with dialogue between 四国めたん (Shikoku Metan) and ずんだもん (Zundamon) characters.

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

# Rebuild without cache (important when making significant changes)
docker-compose build --no-cache
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
- Multiple LLM provider support (OpenAI, Claude, Gemini, AWS Bedrock)
- Web-based LLM provider configuration and API key management
- Conversation style selection (ラジオ風、ビジネスライク、友達風、etc.)
- Auto-copy .env.example on first launch

## LLM Provider Configuration

### Supported Providers
- **OpenAI** - GPT-4o, GPT-4, GPT-3.5-turbo
- **Claude (Anthropic)** - Claude-3-opus, Claude-3-sonnet, Claude-3-haiku
- **Google Gemini** - Gemini Pro, Gemini Pro Vision
- **AWS Bedrock** - Claude models, Llama3, and more

### Environment Variables (`.env`)
```bash
# 使用するLLMプロバイダー: openai, claude, gemini, bedrock
USE_MODEL=openai

# OpenAI
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4o

# Claude (Anthropic)
ANTHROPIC_API_KEY=your-api-key
CLAUDE_MODEL=claude-3-opus-20240229

# Google Gemini
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=gemini-pro

# AWS Bedrock
AWS_BEDROCK_CREDENTIALS=ACCESS_KEY|SECRET_KEY  # 統合形式
# または個別設定
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=ap-northeast-1  # 東京リージョン
BEDROCK_MODEL=anthropic.claude-3-opus-20240229-v1:0
```

### Settings Management
- Web UI at `/settings` for provider configuration
- Settings stored in project `.env` file
- Radio button selection for active provider
- Automatic API key validation
- Shows warning popup when no API keys configured

### LLM Provider API
```python
from api.core.llm_provider import LLMFactory, LLMConfig, LLMProvider

# Create LLM instance
config = LLMConfig(
    provider=LLMProvider.OPENAI,
    api_key="your-key",
    model_id="gpt-4o"
)
llm = LLMFactory.create(config)

# Generate text
response = await llm.generate(
    system_prompt="You are a helpful assistant",
    user_prompt="Hello!",
    temperature=0.7
)
```

### API Endpoints
- `GET /api/settings/providers` - List available providers
- `POST /api/settings/provider` - Save provider configuration
- `DELETE /api/settings/provider/{provider}` - Remove provider
- `POST /api/settings/test-key` - Test API key validity
- `PUT /api/settings` - Update general settings