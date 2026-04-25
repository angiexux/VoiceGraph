"""YouTube transcript extraction using youtube_transcript_api."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


def _extract_video_id(url: str) -> str:
    """Extract the video ID from various YouTube URL formats.

    Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID

    Args:
        url: A YouTube URL.

    Returns:
        The 11-character video ID.

    Raises:
        ValueError: If the video ID cannot be extracted.
    """
    patterns = [
        r"(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Maybe it's already just a video ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
        return url

    raise ValueError(f"Could not extract YouTube video ID from: {url}")


async def parse_youtube(url: str) -> str:
    """Extract the transcript from a YouTube video.

    Args:
        url: YouTube video URL or video ID.

    Returns:
        Concatenated transcript text.

    Raises:
        RuntimeError: If transcript extraction fails.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise RuntimeError(
            "youtube_transcript_api is required for YouTube parsing. "
            "Install with: pip install youtube-transcript-api"
        )

    video_id = _extract_video_id(url)
    logger.info("Fetching transcript for YouTube video: %s", video_id)

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Concatenate all transcript segments
        segments = [entry["text"] for entry in transcript_list]
        text = " ".join(segments)

        # Clean up artifacts common in auto-generated transcripts
        text = re.sub(r"\[.*?\]", "", text)  # Remove [Music], [Applause], etc.
        text = re.sub(r"\s+", " ", text).strip()

        logger.info(
            "Extracted %d characters from YouTube video %s",
            len(text),
            video_id,
        )
        return text

    except Exception as exc:
        raise RuntimeError(
            f"Failed to get transcript for video '{video_id}': {exc}"
        ) from exc
