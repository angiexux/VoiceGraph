# VoiceGraph — Designer Brief

## To: World-Class UI Designer
## From: Product Lead
## Re: Design system for a voice-first AI knowledge graph platform

---

## What this is

VoiceGraph is a real-time voice-controlled knowledge graph. Users talk to their data. The AI agent builds, explores, and explains a knowledge graph through natural voice conversation. The graph is the centerpiece — a living 3D particle network that REACTS to every voice command. Nodes light up as the AI thinks. Paths glow as relationships are discovered. New entities fly in when documents are processed.

This is not a dashboard. This is mission control for human knowledge.

## What I need from you

A design system and high-fidelity component library for a React web application. Dark theme only. Desktop only (min 1280px). The aesthetic must feel like the CretaX genome visualization UI — cinematic, data-dense, alive — but adapted for a knowledge graph / AI agent context.

---

## The Feel

Imagine you're a researcher in 2035. You sit down at your station. The screen is mostly void — deep, dark, breathing. In the center floats your knowledge graph — a 3D network of glowing nodes connected by luminous threads. Around it, glass panels float with data: entity details, relationship maps, provenance chains, AI analytics.

You speak: "How does this company connect to that regulation?"

The graph dims. A path ignites — node by node, edge by edge — tracing the connection. A translucent panel slides up showing the AI's reasoning in real-time. The agent's voice narrates the discovery. A floating annotation card appears on each traversed node, showing its role in the chain.

You speak: "Open canvas and explain this visually."

The graph slides left. A rendering space opens. Flowcharts materialize. Comparison tables build themselves. A timeline populates. All while the voice continues explaining.

Everything is connected. Everything moves. Nothing is static.

**That's the feel.**

---

## Design DNA (from CretaX reference)

These specific patterns from the CretaX genome map MUST be preserved:

1. **The void.** Near-black background (#06090f) with no noise, no texture. The visualization floats in space.

2. **Annotated nodes.** Floating callout cards connected to specific nodes in the 3D visualization via thin dashed lines. Each card has: an ID code (monospace), a title (bold), a description (light), and optionally a status badge.

3. **Glass cards.** Every UI panel is a glass-morphism card: semi-transparent dark background, subtle blur, barely-visible border. They feel like they're hovering.

4. **Status badges.** Small pill shapes with colored borders. Uppercase, tracked, tiny. They communicate state at a glance: ACTIVE SYNC (green), RISK LVL: MEDIUM (orange), OVEREXPRESSED (red).

5. **The stat block.** Large monospace numbers with tiny labels beneath. Arranged in 2x2 grids. "78% / Incubation Viability". This pattern is used EVERYWHERE for metrics.

6. **The left column.** Analytics panel with AI stats and action cards. Dense. Scrollable. Each action card has an icon + title + one-line description.

7. **Data tables.** Not spreadsheet-style. Minimal. Key-value pairs with the key left-aligned in secondary color and the value right-aligned in primary color. Like a spec sheet, not a data grid.

8. **The three-column layout.** Left (controls/analytics) | Center (hero visualization) | Right (contextual details). The center is ALWAYS the largest.

---

## Screens & Components to Design

### Screen 1: Main View (Graph + Voice)
- 3D knowledge graph in center (you can use a placeholder particle network)
- Left panel: AI Analytics stat blocks, query tool action cards, ingestion panel
- Right sidebar: selected node details (key-value data), relationship list, provenance card
- Bottom bar: voice panel (connection indicator, waveform, mic button, transcript)
- Floating: thought stream panel (bottom-right, showing reasoning steps)
- Floating: node annotation cards on the graph (2-3 examples)

### Screen 2: Graph with Active Query
- Same layout, but graph is dimmed (20% opacity on non-matching nodes)
- A path of 4-5 nodes is glowing brightly with particle effects on edges
- Thought stream shows completed reasoning steps
- Right sidebar shows the path details
- Voice transcript shows the query and response

### Screen 3: Ingestion Active
- File upload card (floating, left area) showing phases A/B/C with progress
- Graph has new nodes appearing with trailing light effects
- Status badges updating live: "EXTRACTING", "47 ENTITIES", "COMPLETE"

### Screen 4: Ontology View
- Replace right sidebar with ontology tree (class hierarchy)
- Each class shows badge count of entities
- Relationship types listed with domain → range
- Status: "VOICE EDITING ACTIVE" badge

### Screen 5: Canvas View (V1.1)
- Graph slides to left 40%
- Canvas area on right 60%
- 2-3 rendered components: a mermaid flowchart, a comparison table, a timeline
- Each component in its own glass card
- Canvas has a subtle grid background (optional)

### Component Sheet
- Glass Card (default, elevated, active, alert variants)
- Status Badge (5 color variants)
- Stat Block (single and 2x2 grid)
- Action Card (with icon)
- Node Annotation Card (with connector line)
- Thought Stream Panel (with multiple step types)
- Voice Panel (connected, recording, idle states)
- Ingestion Progress Card (all phases)
- Data Table (key-value)
- Relationship List Item (with edge label and direction arrow)
- Search Input (dark, with icon)
- Tab Bar (like CretaX navigation)
- Mic Button (idle, recording, processing states)

---

## Technical Constraints

- Built in React + TypeScript + Tailwind CSS
- 3D graph rendered by Reagraph (React library — we control node/edge colors, sizes, selections, but not the 3D rendering itself)
- All fonts from Google Fonts (Inter + JetBrains Mono)
- Icons from Lucide React
- CSS animations only (no Lottie, no After Effects exports)
- Glass-morphism via `backdrop-filter: blur()` (Chrome/Safari/Edge supported)
- Must work at 60fps with 500+ graph nodes visible

---

## What GOOD looks like

- A judge at a hackathon sees this for 5 seconds and thinks "this team is serious"
- The UI feels like it cost $500K to build even though it's two people in two weeks
- Every interaction (voice query, node click, file upload) has a visual response within 100ms
- The graph animations make people lean forward
- The data density communicates "this system understands something deep about your data"
- Nothing looks generic, template-y, or Material Design

## What BAD looks like

- A chatbot with a graph widget
- Generic React dashboard with shadcn/ui defaults
- Light backgrounds anywhere
- Rounded-corner-friendly consumer app aesthetic
- Static graph that just sits there
- "Loading..." spinners instead of progressive animations

---

## Deliverables

1. Figma or high-fidelity mockups of all 5 screens
2. Component library with all variants documented
3. Color tokens, typography scale, spacing scale as design tokens
4. Animation specifications (duration, easing, trigger) for every interactive element
5. One hero screenshot that we put in the README and presentation deck

---

## Timeline

We need this ASAP. The hackathon is in ~2 weeks. Speed > perfection. Get us to 90% of the CretaX quality level. We'll iterate from there.
