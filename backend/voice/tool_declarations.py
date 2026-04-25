"""Gemini Live function declarations for VoiceGraph tools.

Converts our existing tool functions into google-genai FunctionDeclaration
format for use with the Gemini Live API.
"""

from __future__ import annotations

from google.genai import types


VOICE_TOOLS = [
    types.FunctionDeclaration(
        name="search_concepts",
        description=(
            "Search for entities in the knowledge graph using semantic/substring matching. "
            "Use when the user asks about a topic broadly, e.g. 'What do we know about AI?'"
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(
                    type="STRING",
                    description="The search query to find matching entities",
                ),
                "top_k": types.Schema(
                    type="INTEGER",
                    description="Maximum number of results to return (default 10)",
                ),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="explore_entity",
        description=(
            "Get the full neighborhood of a specific entity -- all connected nodes "
            "and relationships. Use when the user asks about a specific entity by name, "
            "e.g. 'Tell me about OpenAI' or 'What is connected to transformers?'"
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "entity_name": types.Schema(
                    type="STRING",
                    description="Name of the entity to explore",
                ),
                "depth": types.Schema(
                    type="INTEGER",
                    description="How many hops away to explore (default 2)",
                ),
            },
            required=["entity_name"],
        ),
    ),
    types.FunctionDeclaration(
        name="find_path",
        description=(
            "Find the shortest path between two entities in the knowledge graph. "
            "Use when the user asks how two things relate, "
            "e.g. 'How does Elon Musk connect to SpaceX?'"
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "entity_a": types.Schema(
                    type="STRING",
                    description="Name of the first entity",
                ),
                "entity_b": types.Schema(
                    type="STRING",
                    description="Name of the second entity",
                ),
                "max_hops": types.Schema(
                    type="INTEGER",
                    description="Maximum path length to search (default 5)",
                ),
            },
            required=["entity_a", "entity_b"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_graph_stats",
        description=(
            "Get statistics about the knowledge graph -- number of nodes, edges, "
            "entity type distribution, and most connected entities. "
            "Use when the user asks about graph size or structure."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={},
        ),
    ),
    types.FunctionDeclaration(
        name="highlight_nodes",
        description=(
            "Highlight specific nodes in the graph visualization. "
            "Non-highlighted nodes dim to 20% opacity. Call this after queries "
            "to visually show relevant parts of the graph. "
            "You can pass entity NAMES (like 'Donald Trump') and they will "
            "be resolved to the correct graph nodes automatically."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "node_ids": types.Schema(
                    type="ARRAY",
                    items=types.Schema(type="STRING"),
                    description="List of node IDs OR entity names to highlight",
                ),
                "edge_ids": types.Schema(
                    type="ARRAY",
                    items=types.Schema(type="STRING"),
                    description="List of edge IDs to highlight (optional)",
                ),
            },
            required=["node_ids"],
        ),
    ),
    types.FunctionDeclaration(
        name="add_node",
        description=(
            "Add a new entity to the knowledge graph and display it in the "
            "visualization. Use when the user wants to create a new entity."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "name": types.Schema(
                    type="STRING",
                    description="Name of the new entity",
                ),
                "entity_type": types.Schema(
                    type="STRING",
                    description="Type/label of the entity (e.g. Person, Organization, Concept)",
                ),
                "description": types.Schema(
                    type="STRING",
                    description="Optional description of the entity",
                ),
            },
            required=["name", "entity_type"],
        ),
    ),
    types.FunctionDeclaration(
        name="add_relationship",
        description=(
            "Add a new relationship/edge between two existing entities in the "
            "knowledge graph. Use when the user says things like "
            "'Connect Einstein to Physics' or 'Link Google to AI'."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "source_name": types.Schema(
                    type="STRING",
                    description="Name of the source entity",
                ),
                "target_name": types.Schema(
                    type="STRING",
                    description="Name of the target entity",
                ),
                "relationship_type": types.Schema(
                    type="STRING",
                    description="Type of relationship (e.g. WORKS_AT, DEVELOPED, RELATED_TO)",
                ),
            },
            required=["source_name", "target_name", "relationship_type"],
        ),
    ),
    types.FunctionDeclaration(
        name="remove_node",
        description=(
            "Remove an entity and all its relationships from the knowledge graph. "
            "Use when the user says 'Delete X' or 'Remove X from the graph'."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "name": types.Schema(
                    type="STRING",
                    description="Name of the entity to remove",
                ),
            },
            required=["name"],
        ),
    ),
]
