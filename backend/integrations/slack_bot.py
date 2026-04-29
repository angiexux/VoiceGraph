"""Slack @VoiceGraph bot — answers knowledge graph questions via @mentions.

Setup:
1. Create a Slack App at api.slack.com/apps
2. Enable Events API, subscribe to app_mention events
3. Add Bot Token Scopes: app_mentions:read, chat:write, channels:history
4. Set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET in backend/.env
5. Set APP_PUBLIC_URL to your deployed URL (e.g. https://voicegraph.example.com)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def _format_results_as_blocks(
    question: str,
    results: list[dict[str, Any]],
    subgraph_context: str,
    app_url: str,
) -> list[dict[str, Any]]:
    """Format search results as Slack Block Kit blocks."""
    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Query:* {question}",
            },
        },
    ]

    if subgraph_context:
        # Use the subgraph context as the answer summary (first 3 lines)
        summary_lines = [l for l in subgraph_context.splitlines() if l.strip()][:3]
        summary = "\n".join(summary_lines)
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Connections found:*\n{summary}"},
        })

    if results:
        entity_list = "\n".join(
            f"• *{r.get('name', '')}* — {r.get('description', '')[:80]}"
            for r in results[:5]
            if r.get("name")
        )
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Top entities:*\n{entity_list}"},
        })

    if app_url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Knowledge Graph"},
                    "url": app_url,
                    "action_id": "open_graph",
                }
            ],
        })

    blocks.append({"type": "divider"})
    return blocks


async def handle_app_mention(
    event: dict[str, Any],
    say: Any,
    neo4j_client: Any,
) -> None:
    """Handle an @VoiceGraph mention — query the graph and reply."""
    text: str = event.get("text", "")
    # Strip the bot mention (<@BOTID>) from the text
    import re
    question = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    if not question:
        await say("Hi! Ask me anything about your knowledge graph. Example: `@VoiceGraph How does X relate to Y?`")
        return

    app_url = os.getenv("APP_PUBLIC_URL", "")

    try:
        from retrieval.hybrid_retriever import hybrid_search

        result = await hybrid_search(question, neo4j_client, top_k=5)
        results = result.get("results", [])
        subgraph_context = result.get("subgraph_context", "")

        if not results and not subgraph_context:
            await say(f"I searched the knowledge graph for *{question}* but didn't find relevant entities. Try ingesting more documents!")
            return

        blocks = _format_results_as_blocks(question, results, subgraph_context, app_url)
        await say(blocks=blocks, text=f"Results for: {question}")

    except Exception as exc:
        logger.error("Slack mention handler failed: %s", exc)
        await say("Sorry, I encountered an error processing your question. Please try again.")


def create_slack_app(neo4j_client: Any) -> Any | None:
    """Create and configure the Slack Bolt app."""
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")

    if not bot_token or not signing_secret:
        logger.info(
            "SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET not set — Slack bot disabled. "
            "Set these env vars and restart to enable."
        )
        return None

    try:
        from slack_bolt.async_app import AsyncApp

        slack_app = AsyncApp(token=bot_token, signing_secret=signing_secret)

        @slack_app.event("app_mention")
        async def on_mention(event: dict, say: Any) -> None:
            await handle_app_mention(event, say, neo4j_client)

        return slack_app
    except ImportError:
        logger.warning("slack-bolt not installed — Slack bot disabled. pip install slack-bolt")
        return None
    except Exception as exc:
        logger.error("Failed to create Slack app: %s", exc)
        return None
