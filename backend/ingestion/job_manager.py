"""In-memory ingestion job tracker.

Tracks the lifecycle of document ingestion jobs from start to completion,
providing status, progress, and entity/relationship counts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class IngestionJob:
    """Represents a single document ingestion job."""

    id: str
    status: str = "started"
    # Valid statuses:
    #   started, parsing, extracting_phase_a, extracting_phase_b,
    #   extracting_phase_c, storing, complete, error
    source_type: str = "text"
    source_preview: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    entities_found: int = 0
    relationships_found: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return {
            "id": self.id,
            "status": self.status,
            "source_type": self.source_type,
            "source_preview": self.source_preview,
            "progress": self.progress,
            "entities_found": self.entities_found,
            "relationships_found": self.relationships_found,
            "error": self.error,
        }


class JobManager:
    """Simple in-memory job store.

    Not persistent across restarts — suitable for a hackathon demo.
    """

    def __init__(self) -> None:
        self.jobs: dict[str, IngestionJob] = {}

    def create_job(self, source_type: str = "text", source_preview: str = "") -> IngestionJob:
        """Create and register a new ingestion job."""
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            id=job_id,
            source_type=source_type,
            source_preview=source_preview[:200],
        )
        self.jobs[job_id] = job
        return job

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        """Update fields on an existing job."""
        job = self.jobs.get(job_id)
        if job is None:
            return
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

    def get_job(self, job_id: str) -> IngestionJob | None:
        """Retrieve a job by ID, or None if not found."""
        return self.jobs.get(job_id)
