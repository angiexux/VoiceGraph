"""Tool executor for Gemini Live function calls.

Maps Gemini function call names to the actual Python tool functions
in agents/tools/ and executes them, returning results as dicts.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any

from agents.tools.query_tools import (
    search_concepts,
    explore_entity,
    find_path,
    get_graph_stats,
)
from agents.tools.graph_tools import (
    highlight_nodes,
    add_node,
    add_relationship,
    remove_node,
)

logger = logging.getLogger(__name__)

# Registry mapping function names to callables
TOOL_REGISTRY: dict[str, Any] = {
    "search_concepts": search_concepts,
    "explore_entity": explore_entity,
    "find_path": find_path,
    "get_graph_stats": get_graph_stats,
    "highlight_nodes": highlight_nodes,
    "add_node": add_node,
    "add_relationship": add_relationship,
    "remove_node": remove_node,
}


async def execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool by name with the given arguments.

    Handles both sync and async tool functions.
    Returns a dict with the tool result, or an error dict if the tool
    is not found or execution fails.
    """
    func = TOOL_REGISTRY.get(name)
    if func is None:
        logger.warning("Unknown tool requested: %s", name)
        return {"error": f"Unknown tool: {name}"}

    try:
        logger.info("Executing tool %s with args: %s", name, args)
        result = func(**args)
        if inspect.isawaitable(result):
            result = await result
        logger.info("Tool %s completed successfully", name)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tool %s execution failed", name)
        return {"error": f"Tool execution failed: {exc}"}
