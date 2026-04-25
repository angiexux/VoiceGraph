"""VoiceSession — manages a Gemini Live API session for real-time voice.

Handles bidirectional audio streaming, transcript extraction, and
function-call execution against VoiceGraph tools.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any, Callable, Coroutine

from google import genai
from google.genai import types

from voice.tool_declarations import VOICE_TOOLS
from voice.tool_executor import execute_tool

logger = logging.getLogger(__name__)

# Model that supports Live/bidi with audio + tools
LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"

def _build_system_instruction() -> str:
    """Build a dynamic system instruction using the user's profile and graph stats."""
    from user.profile import get_profile
    profile = get_profile()
    role = profile.get("role", "researcher")
    domain = profile.get("domain", "general knowledge")

    return f"""You are VoiceGraph, a voice-first AI knowledge assistant for a {role} focused on {domain}. You help them explore, query, and build their personal knowledge graph. Be warm, clear, and direct.

You are grounded in the user's personal knowledge graph — a collection of concepts, people, papers, organizations, and relationships they have ingested from their own documents, notes, and research.

RULES:
- Call tools IMMEDIATELY. Don't narrate what you plan to do — just do it and then speak about results.
- After EVERY search/explore/path query, ALWAYS call highlight_nodes with ALL relevant entity NAMES.
- For simple commands (add, delete, stats): brief, 1-2 sentences.
- For domain questions: give RICH, DETAILED answers. 4-6 sentences. Explain connections in plain language. Name specific entities and relationships from the graph.
- Interpret all queries through the lens of {domain}. When they ask about a concept, prioritize relationships relevant to their domain.
- When you find a causal chain (A causes B causes C), narrate it step by step.

TOOLS:
- search_concepts: broad topic search → then highlight results
- explore_entity: specific entity lookup → then highlight results
- find_path: how two things connect → then highlight the path
- get_graph_stats: graph size overview
- add_node / add_relationship / remove_node: graph mutations
- highlight_nodes: light up nodes on the graph. Pass entity NAMES. ALWAYS call this after search/explore results.

NEVER SAY things like "I've determined that..." or "My plan is to..." or "Let me search for..." — just DO IT and then speak about what you found."""


SYSTEM_INSTRUCTION = _build_system_instruction()


class VoiceSession:
    """Manages a single Gemini Live session for one WebSocket client."""

    def __init__(
        self,
        send_event: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        self._send_event = send_event
        self._session: Any = None
        self._client: genai.Client | None = None
        self._receive_task: asyncio.Task | None = None
        self._active = False
        self._session_context: Any = None
        self._tool_in_progress = False
        # Conversation memory — survives reconnects
        self._conversation_history: list[str] = []
        # Transcript buffering — accumulate words before sending
        self._user_transcript_buf = ""
        self._agent_transcript_buf = ""
        self._user_flush_task: asyncio.Task | None = None
        self._agent_flush_task: asyncio.Task | None = None

    @property
    def active(self) -> bool:
        return self._active

    async def start(self) -> None:
        """Open a Gemini Live connection and start the receive loop."""
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.error("GOOGLE_API_KEY not set")
            await self._send_event({
                "type": "error",
                "message": "GOOGLE_API_KEY not set. Voice features are unavailable.",
            })
            return

        try:
            self._client = genai.Client(api_key=api_key)

            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                tools=[types.Tool(function_declarations=VOICE_TOOLS)],
                system_instruction=SYSTEM_INSTRUCTION,
                input_audio_transcription=types.AudioTranscriptionConfig(),
                output_audio_transcription=types.AudioTranscriptionConfig(),
            )

            logger.info("Connecting to Gemini Live model: %s", LIVE_MODEL)
            self._session_context = self._client.aio.live.connect(
                model=LIVE_MODEL,
                config=config,
            )
            self._session = await self._session_context.__aenter__()
            self._active = True

            self._receive_task = asyncio.create_task(
                self._receive_loop(),
                name="voice-receive-loop",
            )

            await self._send_event({
                "type": "voice_ready",
                "message": "Voice session started. Listening...",
            })
            logger.info("Gemini Live session started successfully")

        except Exception as exc:
            logger.exception("Failed to start Gemini Live session")
            await self._send_event({
                "type": "error",
                "message": f"Failed to start voice session: {exc}",
            })

    async def send_audio(self, base64_audio: str) -> None:
        """Send a base64-encoded PCM16 audio chunk to Gemini."""
        if not self._active or self._session is None:
            return

        try:
            audio_bytes = base64.b64decode(base64_audio)
            await self._session.send_realtime_input(
                audio=types.Blob(
                    data=audio_bytes,
                    mime_type="audio/pcm;rate=16000",
                )
            )
        except Exception:
            # Connection closed — don't spam logs for every audio chunk
            pass

    async def send_text(self, text: str) -> None:
        """Send a text message to the Gemini Live session."""
        if not self._active or self._session is None:
            return

        self._add_history("user", text)
        try:
            await self._session.send_client_content(
                turns=[types.Content(
                    parts=[types.Part(text=text)],
                    role="user",
                )],
                turn_complete=True,
            )
        except Exception:
            logger.exception("Failed to send text to Gemini")

    async def close(self) -> None:
        """Close the Gemini Live session and clean up."""
        self._active = False

        if self._receive_task is not None:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                logger.exception("Error closing Gemini Live session")
            self._session = None
            self._session_context = None

        self._client = None
        logger.info("Gemini Live session closed")

    # ------------------------------------------------------------------
    # Background receive loop
    # ------------------------------------------------------------------

    async def _receive_loop(self) -> None:
        """Continuously receive responses from Gemini Live and forward them.
        Auto-reconnects up to 3 times if the session drops."""
        max_retries = 3

        for attempt in range(max_retries + 1):
            if self._session is None:
                return

            try:
                async for response in self._session.receive():
                    if not self._active:
                        return
                    try:
                        await self._handle_response(response)
                    except Exception:
                        logger.exception("Error handling Gemini response (continuing)")
                # Stream ended normally (Gemini closed it)
                if not self._active:
                    return

                # If a tool is in progress, wait for it to finish before reconnecting
                if self._tool_in_progress:
                    logger.warning("Stream ended while tool in progress — waiting...")
                    for _ in range(150):  # Wait up to 15 seconds
                        if not self._tool_in_progress:
                            break
                        await asyncio.sleep(0.1)

                logger.warning("Gemini Live stream ended (attempt %d/%d)", attempt + 1, max_retries)

            except asyncio.CancelledError:
                logger.info("Receive loop cancelled")
                return
            except Exception:
                logger.exception("Gemini Live receive error (attempt %d/%d)", attempt + 1, max_retries)

            # Try to reconnect
            if attempt < max_retries and self._active:
                await self._send_event({
                    "type": "voice_ready",
                    "message": "Reconnecting voice...",
                })
                try:
                    await self._reconnect()
                    logger.info("Reconnected to Gemini Live successfully")
                    continue
                except Exception:
                    logger.exception("Reconnect failed")

        # All retries exhausted
        if self._active:
            await self._send_event({
                "type": "error",
                "message": "Voice session disconnected. Click mic to restart.",
            })
            self._active = False

    async def _flush_transcript(self, role: str, delay: float) -> None:
        """Wait for a pause in streaming, then flush the buffered transcript."""
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return  # New text arrived, timer reset

        if role == "user":
            text = self._user_transcript_buf.strip()
            self._user_transcript_buf = ""
        else:
            text = self._agent_transcript_buf.strip()
            self._agent_transcript_buf = ""

        if text:
            self._add_history(role if role == "user" else "assistant", text)
            await self._send_event({
                "type": "transcript",
                "role": role,
                "text": text,
            })

    @staticmethod
    def _trim_tool_result(tool_name: str, result: dict) -> dict:
        """Trim tool results to avoid overflowing Gemini's context.
        Large results (many nodes/edges) cause Gemini 1011 internal errors."""
        import json
        raw = json.dumps(result, default=str)
        if len(raw) < 4000:
            return result

        # Build a compact summary instead
        trimmed: dict = {}
        for key, val in result.items():
            if isinstance(val, list) and len(val) > 5:
                # Keep first 5 items + count
                trimmed[key] = val[:5]
                trimmed[f"{key}_total"] = len(val)
            elif isinstance(val, dict) and len(json.dumps(val, default=str)) > 1000:
                # Summarize large dicts
                trimmed[key] = {k: v for i, (k, v) in enumerate(val.items()) if i < 10}
            else:
                trimmed[key] = val

        trimmed["_note"] = "Results trimmed for brevity. Use highlight_nodes to show them on the graph."
        return trimmed

    def _add_history(self, role: str, text: str) -> None:
        """Add to conversation history (keeps last 20 entries)."""
        self._conversation_history.append(f"{role}: {text}")
        if len(self._conversation_history) > 20:
            self._conversation_history = self._conversation_history[-20:]

    async def _reconnect(self) -> None:
        """Re-establish the Gemini Live session with conversation context."""
        # Close old session
        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass

        # Build system instruction with conversation history
        history_context = ""
        if self._conversation_history:
            history_text = "\n".join(self._conversation_history[-10:])
            history_context = (
                f"\n\nCONVERSATION HISTORY (continue from here, don't repeat):\n"
                f"{history_text}\n\n"
                f"Continue the conversation naturally. The user may refer to "
                f"things discussed above. Do NOT re-introduce yourself."
            )

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            tools=[types.Tool(function_declarations=VOICE_TOOLS)],
            system_instruction=SYSTEM_INSTRUCTION + history_context,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        self._session_context = self._client.aio.live.connect(
            model=LIVE_MODEL,
            config=config,
        )
        self._session = await self._session_context.__aenter__()

    async def _handle_response(self, response: Any) -> None:
        """Process a single response from Gemini Live."""
        # Handle function calls
        if response.tool_call is not None:
            await self._handle_tool_call(response.tool_call)
            return

        # Handle server content (audio + text + transcriptions)
        server_content = response.server_content
        if server_content is None:
            return

        # Input transcription — what the user said (accumulate, flush on pause)
        if server_content.input_transcription and server_content.input_transcription.text:
            self._user_transcript_buf += server_content.input_transcription.text
            # Cancel previous flush timer and set a new one
            if self._user_flush_task and not self._user_flush_task.done():
                self._user_flush_task.cancel()
            self._user_flush_task = asyncio.create_task(
                self._flush_transcript("user", 0.8)
            )

        # Output transcription — what the agent said (accumulate, flush on pause)
        if server_content.output_transcription and server_content.output_transcription.text:
            self._agent_transcript_buf += server_content.output_transcription.text
            if self._agent_flush_task and not self._agent_flush_task.done():
                self._agent_flush_task.cancel()
            self._agent_flush_task = asyncio.create_task(
                self._flush_transcript("agent", 1.0)
            )

        # Check for turn completion
        if server_content.turn_complete:
            await self._send_event({"type": "turn_complete"})
            return

        # Process content parts
        if server_content.model_turn and server_content.model_turn.parts:
            for part in server_content.model_turn.parts:
                # Audio response
                if part.inline_data is not None:
                    audio_b64 = base64.b64encode(
                        part.inline_data.data
                    ).decode("ascii")
                    await self._send_event({
                        "type": "audio_chunk",
                        "data": audio_b64,
                        "mime_type": part.inline_data.mime_type or "audio/pcm;rate=24000",
                    })

                # Text thinking (model's internal text, NOT spoken output)
                if part.text is not None and part.text.strip():
                    await self._send_event({
                        "type": "thinking_step",
                        "step": part.text.strip()[:200],
                        "icon": "💭",
                    })

    async def _handle_tool_call(self, tool_call: Any) -> None:
        """Handle tool calls from Gemini. Must respond before Gemini continues."""
        self._tool_in_progress = True
        responses = []

        for fc in tool_call.function_calls:
            tool_name = fc.name
            tool_args = dict(fc.args) if fc.args else {}
            # Capture the function call ID — required for send_tool_response
            fc_id = getattr(fc, 'id', None)

            logger.info("Gemini requested tool: %s(%s) id=%s", tool_name, tool_args, fc_id)
            self._add_history("tool_call", f"{tool_name}({tool_args})")

            await self._send_event({
                "type": "tool_call_start",
                "tool_name": tool_name,
                "args": tool_args,
            })

            await self._send_event({
                "type": "thinking_start",
                "query": f"Using {tool_name}...",
            })

            await self._send_event({
                "type": "thinking_step",
                "step": f"Calling {tool_name} with {tool_args}",
                "icon": "🔍",
            })

            try:
                result = await asyncio.wait_for(
                    execute_tool(tool_name, tool_args),
                    timeout=15.0,
                )
            except asyncio.TimeoutError:
                logger.warning("Tool %s timed out after 15s", tool_name)
                result = {"error": f"Tool {tool_name} timed out", "partial": True}
            except Exception as exc:
                logger.exception("Tool %s failed", tool_name)
                result = {"error": str(exc)}

            await self._send_event({
                "type": "tool_call_result",
                "tool_name": tool_name,
                "summary": f"{tool_name} returned {len(result) if isinstance(result, dict) else 0} fields",
            })

            await self._send_event({
                "type": "thinking_complete",
                "resultNodeIds": [],
                "resultEdgeIds": [],
            })

            # Trim result to avoid overflowing Gemini's context
            trimmed = self._trim_tool_result(tool_name, result)

            fr = types.FunctionResponse(
                name=tool_name,
                response=trimmed,
            )
            # Attach the ID from the original function call
            if fc_id:
                fr.id = fc_id
            responses.append(fr)

        # Send tool results back to Gemini
        self._tool_in_progress = False
        if responses and self._session is not None:
            try:
                logger.info("Sending %d tool response(s) back to Gemini", len(responses))
                await self._session.send_tool_response(
                    function_responses=responses,
                )
                logger.info("Tool responses sent successfully")
            except Exception:
                logger.exception("Failed to send tool responses to Gemini")
