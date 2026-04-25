# VoiceGraph — Design Guide

## Design Vision

**One sentence:** A mission-control interface for knowledge — where a 3D knowledge graph floats in deep space and every surrounding panel is a live, breathing data surface controlled by voice.

**Tone:** Cinematic sci-fi data visualization. Not a SaaS dashboard. Not Material Design. This is what happens when NASA's mission control meets Minority Report meets Bloomberg Terminal. Dense, dark, beautiful, and ALIVE.

---

## Reference: CretaX Genome Map

The CretaX UI is our north star. Key design DNA we're stealing:

### What makes CretaX work:
1. **The 3D visualization IS the hero.** It dominates the center. Everything else serves it.
2. **Annotated nodes on the 3D object.** Small callout cards with dotted connector lines pointing to specific locations on the visualization. Labels like "PRG-12", "NEX-04", "TH-21" with descriptions beneath.
3. **Glass cards on dark void.** Panels float on the deep dark background with subtle borders, never with solid backgrounds.
4. **Data density without clutter.** Every pixel shows information. Stats, charts, metadata, badges — but all with strict hierarchy and breathing room.
5. **Status badges with semantic color.** Green "ACTIVE SYNC", orange "RISK LVL: MEDIUM", red "OVEREXPRESSED", green "STABLE". Always pill-shaped, always uppercase, always small.
6. **Split typography.** Huge bold headings ("GENOME MAP") + small monospace detail text. Never medium-size anything.
7. **The left column = controls/analytics.** The center = visualization. The right column = contextual details.
8. **Action cards** with icons. "GENOME COMPARISON", "BEHAVIOR PREDICTOR" — each a clickable card with an icon and one-line description.

---

## Color System

### Background Layers
```
Base void:         #06090f   (near-black with blue undertone)
Surface level 1:   #0d1117   (panel backgrounds)
Surface level 2:   #161b22   (elevated cards, hover states)
Surface level 3:   #1c2333   (active/selected states)
Border default:    #1e2d3d   (subtle, barely visible)
Border active:     #2d4a6f   (slightly more visible on focus)
```

### Text Hierarchy
```
Primary text:      #e6edf3   (bright white, headings)
Secondary text:    #8b949e   (descriptions, labels)
Tertiary text:     #484f58   (disabled, timestamps)
Accent text:       #58a6ff   (links, interactive elements)
```

### Accent / Status Colors
```
Cyan/Teal accent:  #00d4aa   (primary brand, "ACTIVE SYNC" badge)
Blue accent:       #58a6ff   (interactive, highlights)
Orange warning:    #d4830a   (warnings, "RISK LVL: MEDIUM")
Red alert:         #f85149   (errors, "OVEREXPRESSED")
Green success:     #3fb950   (stable, confirmed)
Purple insight:    #a371f7   (AI-generated, thinking)
Amber data:        #e3b341   (data points, metrics)
```

### Graph Node Colors (by entity type)
```
Person:            #58a6ff   (blue)
Organization:      #a371f7   (purple)
Concept:           #00d4aa   (teal)
Event:             #e3b341   (amber)
Location:          #f85149   (red-coral)
Document:          #8b949e   (gray)
Technology:        #3fb950   (green)
Default:           #484f58   (dim gray)
Active/Highlighted:#ffffff   (pure white with glow)
```

### Glow Effects
```
Node glow (idle):    0 0 8px rgba(0, 212, 170, 0.3)
Node glow (active):  0 0 20px rgba(88, 166, 255, 0.6), 0 0 40px rgba(88, 166, 255, 0.2)
Edge glow (active):  0 0 12px rgba(88, 166, 255, 0.5)
Panel glow:          0 0 1px rgba(88, 166, 255, 0.1)
```

---

## Typography

### Font Stack
```
Headings:   'Inter', system-ui, sans-serif  (weight 700, 800)
Body:       'Inter', system-ui, sans-serif  (weight 400, 500)
Mono/Data:  'JetBrains Mono', 'SF Mono', monospace  (weight 400, 500)
Labels:     'Inter', system-ui, sans-serif  (weight 600, uppercase, letter-spacing 0.05em)
```

### Scale
```
Hero title:     2.5rem / 40px  (weight 800, tracking -0.02em) — "GENOME MAP" equivalent
Section title:  1.125rem / 18px  (weight 700, uppercase, tracking 0.05em) — "AI ANALYTICS"
Card title:     0.875rem / 14px  (weight 600) — "GENOME COMPARISON"
Body:           0.8125rem / 13px  (weight 400)
Caption/Label:  0.6875rem / 11px  (weight 500, uppercase, tracking 0.08em, secondary color)
Data value:     2rem / 32px  (weight 700, monospace) — "78%", "0.92"
Data label:     0.6875rem / 11px  (weight 400, secondary color) — "Incubation Viability"
```

---

## Component Library

### 1. Glass Card

The fundamental building block. Every panel, sidebar section, and floating element is a Glass Card.

```
Background:      rgba(13, 17, 23, 0.7)
Backdrop-filter:  blur(12px)
Border:          1px solid rgba(30, 45, 61, 0.5)
Border-radius:   12px
Padding:         16px 20px
Box-shadow:      0 4px 24px rgba(0, 0, 0, 0.3)
```

Variants:
- **Elevated:** Slightly brighter border (rgba(45, 74, 111, 0.5)), used for interactive cards
- **Active:** Cyan border-left (3px solid #00d4aa), used for selected/active items
- **Alert:** Orange or red border, used for warnings

### 2. Status Badge (Pill)

```
Display:          inline-flex
Padding:          4px 10px
Border-radius:    4px
Font:             11px, weight 600, uppercase, tracking 0.08em
Background:       transparent
Border:           1px solid {color}
Color:            {color}
```

Status variants:
- Active/Live: border #00d4aa, text #00d4aa
- Warning: border #d4830a, text #d4830a
- Error: border #f85149, text #f85149
- Info: border #58a6ff, text #58a6ff
- Neutral: border #484f58, text #8b949e

### 3. Stat Block (Big Number + Label)

Like CretaX's "78% / Incubation Viability" pattern:

```
Layout:           Vertical stack
Value:            2rem, weight 700, monospace, primary color
Label:            0.6875rem, weight 400, secondary color
Separator:        1px solid border-default (between adjacent stat blocks)
```

Arrange in 2x2 grids within Glass Cards for data density.

### 4. Action Card (Clickable Feature)

Like CretaX's "GENOME COMPARISON" / "BEHAVIOR PREDICTOR" cards:

```
Layout:           Horizontal: icon (left) + text (right)
Background:       surface-level-1
Border:           1px solid border-default
Border-radius:    8px
Padding:          12px 16px
Icon:             20px, secondary color
Title:            14px, weight 600, primary color
Description:      11px, weight 400, secondary color
Hover:            border → border-active, background → surface-level-2
Cursor:           pointer
```

### 5. Node Annotation Card (Floating on Graph)

Like CretaX's "PRG-12 / PREDATORY RESPONSE / OVEREXPRESSED" callouts:

```
Position:         Absolute, connected to graph node via dotted SVG line
Background:       rgba(13, 17, 23, 0.85)
Backdrop-filter:  blur(8px)
Border:           1px solid border-default
Border-radius:    8px
Padding:          10px 14px
Max-width:        200px

Layout:
  - Node ID:        11px, monospace, secondary color (e.g., "PRG-12")
  - Title:          13px, weight 600, primary color (e.g., "PREDATORY RESPONSE")
  - Description:    11px, weight 400, secondary color
  - Status badge:   at bottom if applicable

Connector line:   1px dashed rgba(88, 166, 255, 0.3), from card edge to node center
```

### 6. Thought Stream Panel

The agent's reasoning overlay at bottom-right:

```
Position:         Fixed, bottom-right, z-index above graph
Width:            360px
Max-height:       280px
Background:       rgba(6, 9, 15, 0.85)
Backdrop-filter:  blur(16px)
Border:           1px solid border-default
Border-radius:    12px 12px 0 0
Padding:          16px
Overflow-y:       auto (custom scrollbar: 4px wide, surface-level-3 track)

Each thought line:
  Icon:           16px (🧠/👁/🔍/✅ or custom SVG equivalents)
  Text:           13px, weight 400
  Color:          secondary → primary (fades in with typewriter)
  Margin-bottom:  8px
  Transition:     opacity 0.3s, transform 0.2s (slide up from bottom)
```

### 7. Voice Panel (Bottom Bar)

```
Position:         Fixed bottom, full width
Height:           64px
Background:       rgba(6, 9, 15, 0.9)
Backdrop-filter:  blur(20px)
Border-top:       1px solid border-default

Layout (centered):
  [Connection dot] [Waveform viz] [Mic button] [Transcript text]

Mic button:
  Size:           44px circle
  Background:     surface-level-2
  Border:         2px solid #00d4aa (when active)
  Icon:           mic icon, #00d4aa when recording
  Pulse animation: when recording, ring expands outward

Waveform:
  Width:          200px
  Height:         32px
  Color:          #00d4aa bars
  Animation:      bars animate with audio amplitude

Connection dot:
  Size:           8px circle
  Color:          #3fb950 (connected), #f85149 (disconnected)
  Pulse:          subtle pulse when connected
```

### 8. Ingestion Progress Card

```
Background:       Glass Card
Width:            300px (floating, bottom-left)

Phase indicators:
  Each phase = horizontal row:
  [●] Phase A: Discovering entities...     ← dot pulses when active
  [✓] Phase B: Ontology generated          ← checkmark when done
  [ ] Phase C: Precision extraction        ← empty when pending

Progress bar:
  Height:         2px
  Background:     surface-level-2
  Fill:           gradient #00d4aa → #58a6ff
  Animation:      smooth width transition

Stats at bottom:
  "47 entities • 89 relationships • 3 documents"
  Font: 11px, monospace, secondary color
```

---

## Layout Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  TOP BAR (56px)                                                      │
│  Logo + Nav tabs (like CretaX: OVERVIEW | GRAPH | ONTOLOGY | DATA)  │
│  Right: Search + notification bell + user avatar                    │
├────────────┬──────────────────────────────────┬──────────────────────┤
│            │                                  │                      │
│  LEFT      │  CENTER (flex-1)                 │  RIGHT               │
│  PANEL     │                                  │  SIDEBAR             │
│  (320px)   │  3D Knowledge Graph              │  (340px)             │
│            │  (Reagraph)                       │                      │
│  AI Stats  │                                  │  Selected Node       │
│  Query     │  + Floating annotation cards     │  Details             │
│  Tools     │  + Thinking animation overlay    │                      │
│  Actions   │                                  │  Relationships       │
│            │                                  │  List                │
│  ─────     │                                  │                      │
│  Ingestion │                                  │  Provenance          │
│  Panel     │                                  │  Card                │
│            │                                  │                      │
│            │                                  │  ─────               │
│            │  ┌─────────────────────┐         │  Ontology            │
│            │  │ Thought Stream      │         │  View                │
│            │  │ (bottom-right float)│         │                      │
│            │  └─────────────────────┘         │                      │
├────────────┴──────────────────────────────────┴──────────────────────┤
│  VOICE BAR (64px)                                                    │
│  [●] Connected  |  ≋≋≋≋≋≋ waveform ≋≋≋≋≋≋  |  🎤  |  transcript   │
└──────────────────────────────────────────────────────────────────────┘
```

### Responsive Behavior (desktop only — no mobile)
- Min width: 1280px
- Left panel collapses to icon-only (48px) below 1440px
- Right sidebar collapses to overlay below 1440px

---

## Animation Principles

### 1. Everything has micro-motion
- Panel appearance: fade in (opacity 0→1) + slide up (translateY 8px→0) over 200ms
- Badge appearance: scale from 0.8→1 over 150ms with ease-out
- Number changes: count up animation over 400ms
- Graph nodes: subtle idle breathing (scale 0.98→1.02 over 3s, infinite)

### 2. Graph animation is cinematic
- New nodes: fly in from edge with spring physics (overshoot + settle)
- Removed nodes: shrink to 0 + fade over 300ms
- Highlight activation: 0→glow over 200ms, with expanding ring pulse
- Path traversal: sequential 150ms delays between nodes, particle travels along edges
- Ripple: 400ms between rings, each ring fades in simultaneously

### 3. Voice feedback is immediate
- Mic button: instant pulse on press (no delay)
- Waveform: <16ms latency (requestAnimationFrame)
- Transcript: appears character-by-character (<50ms per character)
- "Agent thinking" state: thought stream panel slides up within 100ms of first thinking event

### 4. Transitions use easing
```css
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);
--spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

---

## Canvas Design (V1.1)

When the user says "Open canvas and explain X", the center area transitions:

```
Graph view slides left + shrinks to 40% width
Canvas opens on the right 60% with a slide-in animation

Canvas background: same void (#06090f)
Canvas components render as Glass Cards that appear one-by-one
Each component slides in from bottom with stagger

Supported canvas components:
  - Mermaid flowcharts (rendered with mermaid.js, themed dark)
  - Comparison tables (styled like CretaX data tables)
  - Timelines (horizontal, with node markers)
  - Stat blocks (big numbers + labels)
  - Image grids (web-searched images in glass cards)
  - Annotated text excerpts (highlighted source text with entity markers)
```

---

## Icon System

Use **Lucide React** (MIT, tree-shakeable):
- Mic, MicOff (voice)
- Search, Filter (query)
- Upload, FileText, Film, Music (ingestion)
- GitBranch, GitCommit, Network (graph)
- Brain, Eye, CheckCircle, Sparkles (thinking)
- ChevronRight, ChevronDown, X (navigation)
- Zap (status: active/live)

---

## Do NOT

- Use rounded corners >12px (this is not a friendly consumer app)
- Use gradients on backgrounds (solid dark surfaces only)
- Use shadows without blur (no hard drop shadows)
- Use any color at full saturation in large areas (always muted/dimmed)
- Use white (#ffffff) for backgrounds anywhere
- Use large padding/margins (density is part of the aesthetic)
- Center-align body text (always left-aligned)
- Use emoji in the UI itself (icons only; emoji are for the thought stream content only)
- Break the dark void illusion (the deep space feeling is sacred)
