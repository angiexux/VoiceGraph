"""FastAPI routes for Slack Events API webhook."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/slack", tags=["slack"])
logger = logging.getLogger(__name__)

# Will be set during app startup
_slack_handler: Any = None


def set_slack_handler(handler: Any) -> None:
    """Register the Slack Bolt handler (called from main.py startup)."""
    global _slack_handler
    _slack_handler = handler


@router.post("/events")
async def slack_events(request: Request) -> Response:
    """Slack Events API endpoint — receives @mention and other events."""
    if _slack_handler is None:
        return Response(content='{"error": "Slack bot not configured"}', status_code=503)

    try:
        from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

        handler = AsyncSlackRequestHandler(_slack_handler)
        return await handler.handle(request)
    except ImportError:
        return Response(content='{"error": "slack-bolt not installed"}', status_code=503)
    except Exception as exc:
        logger.error("Slack events handler failed: %s", exc)
        return Response(status_code=200)  # Always 200 to avoid Slack retries
