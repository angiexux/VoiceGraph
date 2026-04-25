"""Audio transcription parser using OpenAI Whisper.

Transcribes .mp3, .mp4, .wav, .m4a files into timestamped text chunks.
"""

from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


async def parse_audio(file_path: str) -> list[dict[str, Any]]:
    """Transcribe an audio file and return timestamped chunks.

    Each chunk has:
      - text: transcribed text
      - source_type: "audio"
      - source_file: original filename
      - timestamp_start: segment start time (seconds)
      - timestamp_end: segment end time (seconds)

    Files > 25MB are split into 10-minute segments before processing.
    """
    try:
        import whisper
    except ImportError:
        logger.error(
            "openai-whisper is not installed. Install with: pip install openai-whisper"
        )
        return [{
            "text": f"[Audio transcription unavailable — openai-whisper not installed. File: {os.path.basename(file_path)}]",
            "source_type": "audio",
            "source_file": os.path.basename(file_path),
            "timestamp_start": 0,
            "timestamp_end": 0,
        }]

    logger.info("Loading Whisper model: %s", WHISPER_MODEL)
    model = whisper.load_model(WHISPER_MODEL)

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)

    if file_size_mb > 25:
        # Split into 10-minute segments
        chunks = await _transcribe_large_file(model, file_path)
    else:
        result = model.transcribe(file_path)
        segments = result.get("segments", [])
        chunks = []
        for seg in segments:
            chunks.append({
                "text": seg["text"].strip(),
                "source_type": "audio",
                "source_file": os.path.basename(file_path),
                "timestamp_start": seg["start"],
                "timestamp_end": seg["end"],
            })

    if not chunks:
        full_text = model.transcribe(file_path).get("text", "")
        chunks = [{
            "text": full_text,
            "source_type": "audio",
            "source_file": os.path.basename(file_path),
            "timestamp_start": 0,
            "timestamp_end": 0,
        }]

    logger.info("Transcribed %d segments from %s", len(chunks), file_path)
    return chunks


async def _transcribe_large_file(model: Any, file_path: str) -> list[dict[str, Any]]:
    """Split a large audio file into 10-minute segments and transcribe each."""
    try:
        import subprocess
        duration_result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True
        )
        total_duration = float(duration_result.stdout.strip())
    except Exception:
        logger.warning("Could not determine audio duration, transcribing as single file")
        result = model.transcribe(file_path)
        return [{
            "text": seg["text"].strip(),
            "source_type": "audio",
            "source_file": os.path.basename(file_path),
            "timestamp_start": seg["start"],
            "timestamp_end": seg["end"],
        } for seg in result.get("segments", [])]

    segment_duration = 600  # 10 minutes
    chunks = []
    offset = 0.0

    with tempfile.TemporaryDirectory() as tmpdir:
        segment_idx = 0
        while offset < total_duration:
            segment_path = os.path.join(tmpdir, f"segment_{segment_idx}.wav")
            subprocess.run([
                "ffmpeg", "-i", file_path,
                "-ss", str(offset), "-t", str(segment_duration),
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                segment_path, "-y", "-loglevel", "error"
            ], check=True)

            result = model.transcribe(segment_path)
            for seg in result.get("segments", []):
                chunks.append({
                    "text": seg["text"].strip(),
                    "source_type": "audio",
                    "source_file": os.path.basename(file_path),
                    "timestamp_start": seg["start"] + offset,
                    "timestamp_end": seg["end"] + offset,
                })

            offset += segment_duration
            segment_idx += 1

    return chunks
