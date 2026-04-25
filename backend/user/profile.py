"""User profile management — stores role and domain for personalized extraction.

Profile is persisted to backend/data/user_profile.json and loaded on startup.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])

PROFILE_PATH = Path(__file__).parent.parent / "data" / "user_profile.json"

# In-memory profile (loaded on startup)
_profile: dict[str, Any] = {}


def _load_profile() -> dict[str, Any]:
    """Load profile from disk."""
    global _profile
    if PROFILE_PATH.exists():
        try:
            _profile = json.loads(PROFILE_PATH.read_text())
            logger.info("Loaded user profile: role=%s, domain=%s",
                        _profile.get("role"), _profile.get("domain"))
        except Exception as exc:
            logger.warning("Failed to load profile: %s", exc)
            _profile = {}
    return _profile


def _save_profile(profile: dict[str, Any]) -> None:
    """Persist profile to disk."""
    global _profile
    _profile = profile
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2))
    logger.info("Saved user profile: role=%s, domain=%s",
                profile.get("role"), profile.get("domain"))


def get_profile() -> dict[str, Any]:
    """Get the current user profile (in-memory)."""
    if not _profile:
        _load_profile()
    return _profile


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@router.get("/profile")
async def get_user_profile():
    """Return the current user profile."""
    profile = get_profile()
    if not profile:
        return {"exists": False, "profile": None}
    return {"exists": True, "profile": profile}


@router.post("/profile")
async def set_user_profile(body: dict[str, Any]):
    """Create or update the user profile."""
    profile = {
        "role": body.get("role", ""),
        "domain": body.get("domain", ""),
        "onboarded_at": body.get("onboarded_at", datetime.now(timezone.utc).isoformat()),
    }
    _save_profile(profile)
    return {"success": True, "profile": profile}


# Load on import
_load_profile()
