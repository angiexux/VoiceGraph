"""API routes for Google Drive integration."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/drive", tags=["drive"])
logger = logging.getLogger(__name__)


class ConnectRequest(BaseModel):
    folder_id: str
    folder_name: str = ""


@router.get("/auth")
async def drive_auth(request: Request) -> dict[str, Any]:
    """Start the Google Drive OAuth2 flow. Returns the authorization URL."""
    from integrations.google_drive import get_auth_url

    redirect_uri = str(request.base_url) + "api/drive/callback"
    url = get_auth_url(redirect_uri)
    if not url:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET not configured.",
        )
    return {"auth_url": url}


@router.get("/callback")
async def drive_callback(code: str, request: Request) -> dict[str, Any]:
    """Handle the OAuth2 redirect and exchange the code for tokens."""
    from integrations.google_drive import exchange_code

    redirect_uri = str(request.base_url) + "api/drive/callback"
    success = exchange_code(code, redirect_uri)
    if not success:
        raise HTTPException(status_code=400, detail="OAuth2 code exchange failed.")
    return {"status": "authenticated", "message": "Google Drive connected successfully."}


@router.post("/connect")
async def connect_folder(body: ConnectRequest) -> dict[str, Any]:
    """Register a Drive folder for sync and trigger an immediate import."""
    from integrations.google_drive import _load_folders, _save_folders
    from agents import context as ctx

    folders = _load_folders()
    # Upsert by folder_id
    existing = next((f for f in folders if f["folder_id"] == body.folder_id), None)
    if not existing:
        folders.append({"folder_id": body.folder_id, "folder_name": body.folder_name})
        _save_folders(folders)

    # Trigger immediate sync in background
    import asyncio
    from integrations.google_drive import sync_folder

    async def _noop_broadcast(event: dict) -> None:
        pass

    asyncio.create_task(
        sync_folder(body.folder_id, ctx.neo4j_client, _noop_broadcast)
    )

    return {
        "status": "syncing",
        "folder_id": body.folder_id,
        "message": "Folder registered. Initial sync started in background.",
    }


@router.get("/status")
async def drive_status() -> dict[str, Any]:
    """Return auth status and list of connected folders."""
    from integrations.google_drive import _load_tokens, _load_folders

    return {
        "authenticated": _load_tokens() is not None,
        "folders": _load_folders(),
    }
