"""WebSocket event schemas for the VoiceGraph protocol.

Client events flow from the frontend to the backend.
Server events flow from the backend to the frontend.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ClientEventType(str, Enum):
    """Types of events the client can send."""

    VOICE_START = "voice_start"
    VOICE_CHUNK = "voice_chunk"
    VOICE_END = "voice_end"
    TEXT_INPUT = "text_input"
    GRAPH_INTERACTION = "graph_interaction"
    EXTRACTION_START = "extraction_start"
    EXTRACTION_CANCEL = "extraction_cancel"


class ServerEventType(str, Enum):
    """Types of events the server can send."""

    TRANSCRIPT_PARTIAL = "transcript_partial"
    TRANSCRIPT_FINAL = "transcript_final"
    AGENT_THINKING = "agent_thinking"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    GRAPH_UPDATE = "graph_update"
    HIGHLIGHT = "highlight"
    EXTRACTION_PROGRESS = "extraction_progress"
    ERROR = "error"
    ECHO = "echo"


# ---------------------------------------------------------------------------
# Client events
# ---------------------------------------------------------------------------


class VoiceStartEvent(BaseModel):
    """Client signals the start of a voice recording."""

    type: ClientEventType = ClientEventType.VOICE_START
    sample_rate: int = 16000
    encoding: str = "pcm_s16le"


class VoiceChunkEvent(BaseModel):
    """A chunk of raw audio data (base64-encoded)."""

    type: ClientEventType = ClientEventType.VOICE_CHUNK
    data: str = Field(..., description="Base64-encoded audio bytes")


class VoiceEndEvent(BaseModel):
    """Client signals the end of a voice recording."""

    type: ClientEventType = ClientEventType.VOICE_END


class TextInputEvent(BaseModel):
    """A plain-text message from the user."""

    type: ClientEventType = ClientEventType.TEXT_INPUT
    text: str


class GraphInteractionEvent(BaseModel):
    """User interacted with a graph element (click, hover, etc.)."""

    type: ClientEventType = ClientEventType.GRAPH_INTERACTION
    action: str = Field(..., description="click | hover | select")
    node_id: str | None = None
    edge_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractionStartEvent(BaseModel):
    """Client requests an extraction pipeline run."""

    type: ClientEventType = ClientEventType.EXTRACTION_START
    source_url: str
    source_type: str = Field("auto", description="youtube | web | text | auto")


class ExtractionCancelEvent(BaseModel):
    """Client requests cancellation of a running extraction."""

    type: ClientEventType = ClientEventType.EXTRACTION_CANCEL
    job_id: str


# ---------------------------------------------------------------------------
# Server events
# ---------------------------------------------------------------------------


class TranscriptPartialEvent(BaseModel):
    """Partial speech-to-text transcript (streaming)."""

    type: ServerEventType = ServerEventType.TRANSCRIPT_PARTIAL
    text: str
    is_final: bool = False


class TranscriptFinalEvent(BaseModel):
    """Final, stable speech-to-text transcript."""

    type: ServerEventType = ServerEventType.TRANSCRIPT_FINAL
    text: str


class AgentThinkingEvent(BaseModel):
    """Indicates the agent is processing."""

    type: ServerEventType = ServerEventType.AGENT_THINKING
    message: str = ""


class AgentResponseEvent(BaseModel):
    """Natural-language response from the agent."""

    type: ServerEventType = ServerEventType.AGENT_RESPONSE
    text: str
    audio_url: str | None = None


class ToolCallEvent(BaseModel):
    """The agent is invoking a tool."""

    type: ServerEventType = ServerEventType.TOOL_CALL
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultEvent(BaseModel):
    """Result returned by a tool invocation."""

    type: ServerEventType = ServerEventType.TOOL_RESULT
    tool_name: str
    result: dict[str, Any] = Field(default_factory=dict)


class GraphUpdateEvent(BaseModel):
    """Incremental update to the graph visualisation."""

    type: ServerEventType = ServerEventType.GRAPH_UPDATE
    added_nodes: list[dict[str, Any]] = Field(default_factory=list)
    added_edges: list[dict[str, Any]] = Field(default_factory=list)
    removed_node_ids: list[str] = Field(default_factory=list)
    removed_edge_ids: list[str] = Field(default_factory=list)


class HighlightEvent(BaseModel):
    """Instruct the frontend to highlight specific nodes/edges."""

    type: ServerEventType = ServerEventType.HIGHLIGHT
    node_ids: list[str] = Field(default_factory=list)
    edge_ids: list[str] = Field(default_factory=list)
    color: str = "yellow"


class ExtractionProgressEvent(BaseModel):
    """Progress update for a running extraction job."""

    type: ServerEventType = ServerEventType.EXTRACTION_PROGRESS
    job_id: str
    phase: str = Field(..., description="a | b | c")
    progress: float = Field(..., ge=0.0, le=1.0)
    message: str = ""


class ErrorEvent(BaseModel):
    """An error occurred server-side."""

    type: ServerEventType = ServerEventType.ERROR
    message: str
    code: str = "INTERNAL_ERROR"
