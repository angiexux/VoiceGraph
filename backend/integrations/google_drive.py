"""Google Drive folder sync integration.

OAuth2 flow + folder crawl + daily APScheduler re-sync.
Requires: google-auth-oauthlib, google-api-python-client, apscheduler
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_TOKENS_PATH = Path(__file__).parent.parent / "data" / "drive_tokens.json"
_CONNECTED_FOLDERS_PATH = Path(__file__).parent.parent / "data" / "drive_folders.json"

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def _load_tokens() -> dict | None:
    if _TOKENS_PATH.exists():
        try:
            return json.loads(_TOKENS_PATH.read_text())
        except Exception:
            return None
    return None


def _save_tokens(token_data: dict) -> None:
    _TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKENS_PATH.write_text(json.dumps(token_data, indent=2))


def _load_folders() -> list[dict]:
    if _CONNECTED_FOLDERS_PATH.exists():
        try:
            return json.loads(_CONNECTED_FOLDERS_PATH.read_text())
        except Exception:
            return []
    return []


def _save_folders(folders: list[dict]) -> None:
    _CONNECTED_FOLDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONNECTED_FOLDERS_PATH.write_text(json.dumps(folders, indent=2))


def get_auth_url(redirect_uri: str) -> str | None:
    """Build the Google OAuth2 authorization URL."""
    client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.warning("GOOGLE_DRIVE_CLIENT_ID / GOOGLE_DRIVE_CLIENT_SECRET not set")
        return None

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        return auth_url
    except ImportError:
        logger.error("google-auth-oauthlib not installed. pip install google-auth-oauthlib google-api-python-client")
        return None


def exchange_code(code: str, redirect_uri: str) -> bool:
    """Exchange OAuth2 code for tokens and persist them."""
    client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return False

    try:
        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        _save_tokens({
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or []),
        })
        return True
    except Exception as exc:
        logger.error("OAuth2 code exchange failed: %s", exc)
        return False


def _get_drive_service() -> Any | None:
    """Build an authenticated Drive API service from stored tokens."""
    token_data = _load_tokens()
    if not token_data:
        return None

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", SCOPES),
        )
        return build("drive", "v3", credentials=creds)
    except ImportError:
        logger.error("google-api-python-client not installed")
        return None
    except Exception as exc:
        logger.error("Failed to build Drive service: %s", exc)
        return None


SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
}

GOOGLE_EXPORT_TYPES = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"
    ),
    "application/vnd.google-apps.spreadsheet": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    ),
    "application/vnd.google-apps.presentation": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"
    ),
}


async def sync_folder(
    folder_id: str,
    neo4j_client: Any,
    broadcast_fn: Any,
) -> dict[str, Any]:
    """Download all supported files from a Drive folder and ingest them.

    Args:
        folder_id: Google Drive folder ID.
        neo4j_client: Live Neo4j client for ingestion.
        broadcast_fn: WebSocket broadcast function for progress events.

    Returns:
        Summary dict with files_processed count.
    """
    service = _get_drive_service()
    if service is None:
        return {"error": "Drive not authenticated", "files_processed": 0}

    try:
        # List files in folder (non-recursive for V1)
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, modifiedTime)",
            pageSize=100,
        ).execute()
        files = results.get("files", [])
    except Exception as exc:
        logger.error("Failed to list Drive folder %s: %s", folder_id, exc)
        return {"error": str(exc), "files_processed": 0}

    files_processed = 0
    for file in files:
        mime = file.get("mimeType", "")
        name = file.get("name", "")
        file_id = file.get("id", "")

        export_mime, ext = GOOGLE_EXPORT_TYPES.get(mime, (None, None))
        native_ext = SUPPORTED_MIME_TYPES.get(mime)

        if not export_mime and not native_ext:
            continue  # Unsupported file type

        try:
            with tempfile.NamedTemporaryFile(
                suffix=ext or native_ext, delete=False
            ) as tmp:
                tmp_path = tmp.name

            if export_mime:
                # Export Google Doc/Sheet/Slides as Office format
                content = service.files().export_media(
                    fileId=file_id, mimeType=export_mime
                ).execute()
            else:
                # Download native file
                content = service.files().get_media(fileId=file_id).execute()

            with open(tmp_path, "wb") as f:
                f.write(content)

            # Ingest the downloaded file
            from ingestion.ingest import run_ingestion
            from ingestion.job_manager import JobManager

            job_manager = JobManager()
            job_id = f"drive_{file_id}"
            source_type = (ext or native_ext or ".txt").lstrip(".")

            await run_ingestion(
                job_id=job_id,
                source_type=source_type,
                content=tmp_path,
                job_manager=job_manager,
                neo4j_client=neo4j_client,
                ontology_manager=None,
                broadcast_fn=broadcast_fn,
                metadata={"source_type": source_type, "drive_file_id": file_id, "drive_file_name": name},
            )
            files_processed += 1
            os.unlink(tmp_path)

        except Exception as exc:
            logger.warning("Failed to process Drive file '%s': %s", name, exc)

    return {"files_processed": files_processed, "total_files": len(files)}


def start_scheduler(neo4j_client: Any, broadcast_fn: Any) -> None:
    """Start APScheduler for daily Drive re-sync."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        scheduler = AsyncIOScheduler()

        async def daily_sync() -> None:
            folders = _load_folders()
            for folder in folders:
                fid = folder.get("folder_id", "")
                if fid:
                    await sync_folder(fid, neo4j_client, broadcast_fn)

        scheduler.add_job(daily_sync, "interval", hours=24, id="drive_daily_sync")
        scheduler.start()
        logger.info("Drive daily sync scheduler started.")
    except ImportError:
        logger.warning("apscheduler not installed — Drive daily sync disabled. pip install apscheduler")
    except Exception as exc:
        logger.warning("Failed to start Drive scheduler: %s", exc)
