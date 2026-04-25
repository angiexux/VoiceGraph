# VoiceGraph — Design Prompt for Stitch

## What is this product?

VoiceGraph is a voice-first AI knowledge graph explorer. Users speak to their data and watch it come alive. You talk, and a 3D network of glowing nodes and edges reacts in real-time — lighting up paths, expanding neighborhoods, flying in new entities as documents are ingested.

It's not a dashboard. It's not a chatbot with a sidebar. It's a living, breathing mission control for human knowledge.

## The experience

The screen is dominated by a 3D particle graph floating in dark space. Around it, panels hover with contextual data. The user speaks naturally — "How does OpenAI connect to this regulation?" — and the graph dims, a path ignites node by node, and a reasoning panel streams the AI's thought process in real-time.

When a user uploads a document, new entities materialize on the graph with trailing light effects. Status indicators pulse. Entity counts tick upward.

When the user asks for an explanation, a canvas area opens alongside the graph and renders flowcharts, comparison tables, and timelines — all generated live by the AI while it narrates.

Everything moves. Everything responds. Nothing is static.

## Screens to design

### 1. Main View
- **Center**: 3D knowledge graph (placeholder particle network is fine — we use a library called Reagraph for the actual rendering)
- **Left panel**: AI analytics stats + action cards for tools (query, search, ingest, explore)
- **Right panel**: Selected node details (key-value properties), relationship list, data provenance
- **Bottom bar**: Voice interface — connection indicator, audio waveform, mic button, live transcript
- **Floating overlay (bottom-right)**: AI thought stream — shows reasoning steps as the agent thinks (icons + short text lines, streaming in)
- **Floating on graph**: 2-3 annotation cards pointing to specific nodes (ID code, title, description, optional status tag)

### 2. Active Query View
- Same layout, but non-matching graph nodes are dimmed to ~20% opacity
- A glowing path of 4-5 connected nodes traces the answer
- Thought stream shows completed reasoning
- Right panel shows path details
- Voice transcript shows the question and response

### 3. Ingestion View
- Floating progress card showing extraction phases (Discovery → Ontology → Extraction) with progress indicators
- New nodes appearing on graph
- Live-updating status tags: "EXTRACTING", "47 ENTITIES", "COMPLETE"

### 4. Ontology Editor View
- Right panel replaced with a class hierarchy tree
- Each class shows entity count
- Relationship types listed with domain/range
- "VOICE EDITING ACTIVE" indicator

### 5. Canvas View
- Graph slides to take ~40% width
- Canvas area opens on the remaining ~60%
- Shows 2-3 AI-generated components: a flowchart, a comparison table, a timeline
- Each in its own card, appearing one by one

### Component Library
- Panel/Card (default, elevated, active/selected, alert variants)
- Status tag/badge (multiple semantic colors — success, warning, error, info, neutral)
- Stat block (large number + small label beneath — for metrics like "1,247 / Total Entities")
- Action card (icon + title + description — clickable)
- Node annotation card (floating callout pointing to graph node via connector line)
- Thought stream panel (scrolling list of reasoning steps with icons)
- Voice bar (connected/recording/idle states)
- Ingestion progress card (multi-phase with progress bar)
- Key-value data table (label left, value right — like a spec sheet, not a spreadsheet)
- Relationship list item (with edge label and direction arrow)
- Search input
- Navigation tabs
- Mic button (idle, recording, processing states with pulse animation)

## What the backend provides (data shapes)

The AI agent sends these types of data to the frontend:

- **Graph nodes**: `{ id, label, type, properties }` — types include Person, Organization, Concept, Event, Location, Technology, Document
- **Graph edges**: `{ id, source, target, label }`
- **Thinking events**: Sequential steps like "Searching for entities...", "Found 3 matching nodes", "Traversing path...", "Query complete" — each with an icon type (search, eye, brain, check)
- **Stats**: Entity count, relationship count, document count, query count, connected status
- **Ingestion progress**: Phase name, progress percentage, entity/relationship counts discovered so far
- **Voice state**: Connected/disconnected, recording/idle, transcript text (streaming character by character)
- **Canvas components**: Flowcharts (Mermaid syntax), comparison tables (headers + rows), timelines (date + event pairs), stat grids

## Design soul

This should feel like what a knowledge researcher in 2035 uses at their workstation. Cinematic. Data-dense. Alive. Think NASA mission control meets Bloomberg Terminal meets sci-fi film UI.

The 3D graph is the hero — everything else exists to serve it. Panels should feel like they float. The dark background should feel like deep space. Information density should be high but never cluttered. Every element should feel like it belongs in a system that understands something deep about data.

**It should NOT look like**: a generic SaaS dashboard, a chatbot with a sidebar, Material Design, a consumer app with friendly rounded corners, anything with a light background.

**It should feel like**: the kind of interface that makes someone lean forward. Dense, dark, beautiful, and alive.

## Technical constraints
- Dark theme only, desktop only (min 1280px)
- React + TypeScript + Tailwind CSS
- Fonts: Google Fonts only (suggest Inter for UI, monospace for data)
- Icons: Lucide React
- CSS animations only (no Lottie)
- Must feel performant with 500+ graph nodes

## Let your creativity lead

You have full creative freedom on: color palette, typography choices, spacing system, border treatments, animation style, layout proportions, and overall aesthetic direction. The constraints above are functional — the visual identity is yours to define. Make it unforgettable.
