"""Shared module-level context for VoiceGraph agent tools.

Set by main.py on application startup. Tools import from here
to access shared resources without circular imports.
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

# Neo4j client instance (services.neo4j_client.Neo4jClient)
neo4j_client: Any = None

# Ontology manager instance (services.ontology_manager.OntologyManager)
ontology_manager: Any = None

# Async broadcast function: async def ws_broadcast(event: dict) -> None
ws_broadcast: Callable[..., Coroutine[Any, Any, None]] | None = None
