# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI-based teacher video processing system that integrates OpenAI Whisper API for speech-to-text and Unscreen API for video background removal. The system is designed to process teacher self-introduction videos with automatic transcription and background removal capabilities.

## Development Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Development server
python -m app.main
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Docker deployment
docker-compose up -d
```

### Testing
```bash
# Health check
curl http://localhost:8000/api/v1/health/

# Upload and process video
curl -X POST "http://localhost:8000/api/v1/video/upload-and-process" \
  -F "file=@teacher_video.mp4" \
  -F "teacher_name=John Smith" \
  -F "language_hint=en"

# Check processing progress
curl http://localhost:8000/api/v1/video/progress/{job_id}
```

## Architecture Overview

### Core Services
- **VideoProcessorService** (`app/services/video_processor.py`): Main orchestration service that coordinates video processing workflow
- **WhisperService** (`app/services/speech_to_text.py`): Handles audio extraction and transcription using OpenAI Whisper API
- **UnscreenService** (`app/services/background_removal.py`): Manages video background removal using Unscreen API

### Processing Flow
1. Video upload validation and storage
2. Audio extraction from video using FFmpeg
3. Speech-to-text transcription with OpenAI Whisper
4. Background removal using Unscreen API
5. Result compilation and progress tracking

### Key Configuration
- Environment variables: `OPENAI_API_KEY`, `UNSCREEN_API_KEY`
- File limits: Max 100MB video size, supported formats: .mp4, .mov, .avi, .mkv
- Concurrent processing: Configurable via `MAX_CONCURRENT_JOBS` (default: 3)
- Audio sample rate: 16kHz (optimized for Whisper)

### API Structure
- **Upload Endpoint**: `/api/v1/video/upload-and-process` - Upload and process videos
- **Progress Endpoint**: `/api/v1/video/progress/{job_id}` - Check processing status
- **Download Endpoint**: `/api/v1/video/download/{job_id}` - Download processed video
- **Health Check**: `/api/v1/health/` - Service health status

### Error Handling
- Comprehensive error handling for API failures
- Automatic retry mechanisms
- Detailed logging with job IDs for debugging
- User-friendly error messages for common issues

### Required Dependencies
- Python >= 3.9
- FFmpeg >= 4.0 (for audio extraction)
- OpenAI API key with sufficient credits
- Unscreen API key with sufficient credits