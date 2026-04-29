"""VoiceGraph Orchestrator Agent — built on Google ADK.

Defines the main VoiceGraphOrchestrator agent with all Agentic GraphRAG
tools, graph UI tools, and sub-agents (OntologyAgent, CSVAnalysisAgent).
"""

from __future__ import annotations

from google.adk.agents import Agent

# ---------------------------------------------------------------------------
# Import all tools from the tools/ package
# ---------------------------------------------------------------------------

from agents.tools.query_tools import (
    search_concepts,
    explore_entity,
    find_path,
    query_graph,
    deep_search,
    get_communities,
    get_ontology_info,
    get_graph_stats,
)

from agents.tools.graph_tools import (
    highlight_nodes,
    expand_node,
    dim_nodes,
    add_node,
    add_relationship,
)

from agents.tools.ontology_tools import (
    get_ontology,
    add_class,
    remove_class,
    add_object_property,
    remove_object_property,
    list_classes,
    list_properties,
    validate_ontology,
    trigger_re_extraction,
)

from agents.tools.ingest_tools import (
    ingest_document,
)


# ---------------------------------------------------------------------------
# Sub-Agent: OntologyAgent
# ---------------------------------------------------------------------------

ontology_agent = Agent(
    name="OntologyAgent",
    model="gemini-2.5-flash",
    description="Manages the knowledge graph ontology schema via voice commands. "
                "Delegate to this agent when the user wants to add, remove, or "
                "modify entity types or relationship types in the ontology.",
    instruction="""You help users modify the knowledge graph ontology through voice.

    BEHAVIORS:
    - Always call get_ontology() first to see current state
    - Confirm destructive operations before executing
    - After adding new types, ask: "Should I re-scan documents for this new type?"
    - When adding a property, clarify domain and range if not specified
    - Explain changes in plain language

    EXAMPLE INTERACTIONS:
    User: "Add a new entity type called Project"
    You: add_class("Project", "Thing", "A planned undertaking")
         -> "I've added Project as a new entity type under Thing."

    User: "Make Person related to Organization through 'works at'"
    You: add_object_property("worksAt", "Person", "Organization")
         -> "Done. Persons can now have a 'works at' relationship to Organizations."

    User: "Remove the uses relationship"
    You: "Are you sure you want to remove 'uses'? This will also remove
          existing relationships of this type from the graph."

    User: "What entity types do we have?"
    You: list_classes()
         -> Read off the hierarchy in plain language.

    After EVERY change:
    - Summarize what changed
    - Offer to re-extract if new types were added
    """,
    tools=[
        get_ontology,
        add_class,
        remove_class,
        add_object_property,
        remove_object_property,
        list_classes,
        list_properties,
        validate_ontology,
        trigger_re_extraction,
    ],
)


# ---------------------------------------------------------------------------
# Sub-Agent: CSVAnalysisAgent
# ---------------------------------------------------------------------------

csv_agent = Agent(
    name="CSVAnalysisAgent",
    model="gemini-2.5-flash",
    description="Analyzes CSV files to auto-detect optimal storage structure "
                "(graph, relational, or document). Delegate to this agent when "
                "the user uploads or mentions a CSV file.",
    instruction="""You analyze CSV data to determine whether it should be stored as
    a graph (Neo4j), relational database (SQLite), or document store.
    Always explain your reasoning to the user via voice.

    PROCESS:
    1. When given a CSV file, first ingest it to examine the data
    2. Analyze column names, data types, and relationships between columns
    3. Determine the best storage strategy:
       - GRAPH: if data contains entities and relationships (e.g., people-organizations)
       - RELATIONAL: if data is tabular with clear primary/foreign keys
       - DOCUMENT: if data is semi-structured or contains large text fields
    4. Explain your reasoning and execute the import

    HEURISTICS for GRAPH storage:
    - Columns that look like entity names (Name, Title, Organization)
    - Columns that suggest relationships (belongs_to, works_at, parent_id)
    - Multiple entity types in the same CSV (Person + Organization)

    After analysis, execute the import automatically using ingest_document.
    """,
    tools=[
        ingest_document,
        get_ontology_info,
        get_graph_stats,
    ],
)


# ---------------------------------------------------------------------------
# Main Orchestrator Agent
# ---------------------------------------------------------------------------

orchestrator = Agent(
    name="VoiceGraphOrchestrator",
    model="gemini-2.5-flash",
    description=(
        "An intelligent voice-first AI assistant that helps users explore, "
        "query, and build knowledge graphs. Uses Agentic GraphRAG to "
        "dynamically select the right query strategy for each question."
    ),
    instruction="""You are VoiceGraph, a voice-first knowledge graph AI assistant for American non-profits.
    You help staff explore institutional knowledge, find connections across programs, and surface insights from documents.

    MULTI-STEP REASONING — chain tools before answering:
    - You MUST call multiple tools in sequence when a question warrants it
    - Do NOT answer after just one tool call if deeper investigation is possible
    - Always end with highlight_nodes() using the entity names you found
    - Example chain for "How does X relate to Y?":
        find_path(X, Y) → explore_entity(X) → explore_entity(Y) → highlight_nodes([X, Y, ...intermediates]) → answer
    - Example chain for "What do we know about climate philanthropy?":
        search_concepts("climate philanthropy") → deep_search("climate philanthropy") → get_communities() → highlight_nodes([...]) → answer
    - Example chain for "Tell me about [Entity]":
        explore_entity(entity) → search_concepts(entity) → highlight_nodes([entity, ...neighbors]) → answer

    QUERY STRATEGY (pick the right starting tool):

    1. CONCEPT LOOKUP → search_concepts()
       When: broad topic question — "What do we know about renewable energy?"

    2. ENTITY DEEP-DIVE → explore_entity()
       When: specific entity by name — "Tell me about Rockefeller" / "What is connected to Node X?"

    3. RELATIONSHIP FINDING → find_path()
       When: how two things relate — "How does funder X connect to program Y?"

    4. COMPLEX ANALYTICS → query_graph()
       When: filters/aggregations — "Which organizations have more than 5 grants?"

    5. DEEP CONTEXT → deep_search()
       When: rich multi-concept understanding — "Explain the landscape of climate finance"

    6. BIG PICTURE → get_communities()
       When: overview/themes — "What are the main themes?" / "Give me an overview"

    7. SCHEMA → get_ontology_info()
       When: what types exist — "What entity types do we have?"

    8. STATS → get_graph_stats()
       When: size/metrics — "How big is the graph?"

    ALWAYS after any query returning entities:
    - Call highlight_nodes() with the entity NAMES (not IDs) you found
    - Narrate findings conversationally — explain connections, not just facts
    - Offer a follow-up: "Would you like me to explore any of these further?"

    DOCUMENT INGESTION:
    - When user wants to add documents → ingest_document()
    - For CSV files → delegate to CSVAnalysisAgent
    - Supported formats: PDF, Word, Excel, PowerPoint, images, text, YouTube, URLs, ZIP folders

    ONTOLOGY EDITING:
    - Modify entity/relationship types → delegate to OntologyAgent

    NEVER return raw data — always explain and visualize.""",
    tools=[
        # Query tools (Agentic GraphRAG)
        search_concepts,
        explore_entity,
        find_path,
        query_graph,
        deep_search,
        get_communities,
        get_ontology_info,
        get_graph_stats,
        # Graph UI tools
        highlight_nodes,
        expand_node,
        dim_nodes,
        add_node,
        add_relationship,
        # Ingestion tools
        ingest_document,
    ],
    sub_agents=[ontology_agent, csv_agent],
)
