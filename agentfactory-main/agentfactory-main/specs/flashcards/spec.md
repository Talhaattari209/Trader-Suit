# Flashcards Feature — Requirement Specification

**Status**: v1.1 (Review Round 2 — All open questions resolved)
**Date**: 2026-02-21
**Author**: MJS + Claude

---

## 1. Why Flashcards — The Business Case

### The Cost Problem

The learn-agentfactory skill provides AI-powered tutoring and quizzing. Every session costs API tokens — when opened to all students, cost scales linearly. Flashcards cost nothing per student. They're static content generated at build time with a client-side SRS engine.

| Feature                | Cost per student/session | Offline | Mobile               | SRS scheduling    |
| ---------------------- | ------------------------ | ------- | -------------------- | ----------------- |
| Learn skill (AI tutor) | ~$0.02-0.10              | No      | No                   | N/A               |
| Quiz component         | $0 (static)              | Yes     | Yes (web)            | No                |
| **Flashcards**         | **$0 (static)**          | **Yes** | **Yes (responsive)** | **Yes (FSRS v6)** |

### The Cognitive Case: Building the Mental CPU Cache

Agent engineering is vocabulary-dense. Students encounter hundreds of new terms across 85 chapters: Digital FTE, MCP, tool schema, function calling, context window, RLHF, LoRA...

**Without flashcards**: Every concept requires conscious lookup — slow, fragile thinking.
**With flashcards**: Primitives become automatic recall — faster architecture design, faster debugging, less documentation dependence.

This is backed by the **testing effect** — retrieval from memory strengthens neural pathways more than passive re-reading ([Karpicke & Roediger, 2008](https://www.science.org/doi/10.1126/science.1152408)). After 4-8 weeks of spaced repetition, students think in agent primitives automatically.

### Why We Own the Experience (Not Anki)

Code is cheap. A flip-card component with FSRS is ~400 lines of React + a 15KB npm dependency. What's expensive is ceding control.

| Factor               | Our Embedded Experience                | Anki Export                               |
| -------------------- | -------------------------------------- | ----------------------------------------- |
| Friction             | Zero — scroll down, start reviewing    | High — install app, download file, import |
| Design control       | Full — our brand, our UX, our theme    | None — Anki's UI                          |
| Mobile               | Works now — responsive web             | Requires app install                      |
| SRS quality          | FSRS v6 (same algorithm Anki uses)     | FSRS v6                                   |
| Student relationship | Stays on our site                      | Leaves our site                           |
| Content updates      | Automatic — always latest on page load | Must re-download and re-import .apkg      |
| Maintenance          | Zero server cost (localStorage)        | Zero                                      |

**Decision**: The embedded experience IS the product. Anki export is a secondary "power user" option.

### The Student Learning Pipeline

```
Stage 1: READ the lesson          → Comprehension (not memorization)
Stage 2: REVIEW flashcards        → Active recall + spaced repetition
Stage 3: RATE confidence          → Metacognitive calibration
Stage 4: BUILD by doing           → Apply with instant recall
```

Flashcards serve Stages 2-3. Lessons serve Stage 1. Exercises serve Stage 4.

---

## 2. Learning Science Foundation

Our embedded flashcard system implements five evidence-based techniques. This is what makes it better than basic Anki.

### 2.1 FSRS v6 — State-of-the-Art Scheduling

The **Free Spaced Repetition Scheduler** (FSRS) is a machine-learning-based algorithm that models memory using three components: stability, difficulty, and retrievability. It's the same algorithm Anki adopted in 2023, replacing the 30-year-old SM-2.

**Why FSRS over Leitner boxes**: FSRS achieves [99.6% superiority over SM-2](https://github.com/open-spaced-repetition/awesome-fsrs) in benchmarks — meaning for 99.6% of users, FSRS schedules reviews more efficiently. Students do 20-30% fewer reviews for the same retention.

**Implementation**: [`ts-fsrs`](https://github.com/open-spaced-repetition/ts-fsrs) (v4.x) — TypeScript, MIT license, supports ESM/CJS/UMD, FSRS v6, minimal bundle (~15KB). Card states: New → Learning → Review → Relearning.

### 2.2 Confidence-Based Repetition (CBR)

After revealing the answer, students rate: **Again | Hard | Good | Easy**

This isn't just scheduling input — it trains **metacognition**. Each self-assessment forces the student to evaluate "did I actually know this?" Over hundreds of repetitions, this calibration becomes increasingly precise ([Brainscape CBR research](https://www.brainscape.com/academy/confidence-based-repetition-definition/)).

The FSRS algorithm uses these ratings directly — `Rating.Again`, `Rating.Hard`, `Rating.Good`, `Rating.Easy` — to compute optimal next review time.

### 2.3 Interleaving (Mixed Practice) — Phase 1

Reviewing cards from a single lesson is **blocked practice**. Research shows [interleaved practice](https://www.retrievalpractice.org/interleaving) — mixing cards across related topics — leads to better long-term retention and transfer.

Phase 1 adds **chapter mode**: shuffled cards across all lessons in a chapter. Chapters are the natural interleaving boundary — related topics, distinct lessons.

### 2.4 Active Recall (Testing Effect)

The card always shows the **question first**. The student must attempt to recall before flipping. This is the testing effect — retrieval practice improves retention more than passive review. [Recent 2025 research](https://www.sciencedirect.com/science/article/pii/S0959475225001434) confirms this extends to complex educational concepts, not just simple facts.

The flip interaction is critical: no "show answer" autoplay, no peek. The student must commit to a mental answer first.

### 2.5 Elaborative Interrogation Hints

For intermediate/advanced cards, the back can include a **"Why?"** prompt — a brief elaborative interrogation question that pushes the student to connect the concept to their existing knowledge.

```
Front: "What are the core components of an agent?"
Back:  "Model, Tools, Memory, Instructions, State"
Why:   "Why would removing any one of these make the agent less capable?"
```

[Research shows](https://www.tandfonline.com/doi/full/10.1080/02702711.2025.2482627) elaborative interrogation activates prior knowledge and deepens encoding. It adds ~15% study time but significantly improves comprehension.

Optional per card (the `why` field). Definitions don't need it; architectural concepts benefit.

---

## 3. Solution Overview

```
Source of Truth           Web (Desktop + Mobile)          Power Users
──────────────           ──────────────────────          ───────────
flashcards.yaml    →     <Flashcards />                  .apkg export
(per lesson)              FSRS v6 scheduling              (optional download)
(version-controlled)      Confidence-based rating
                          localStorage persistence
                          Zero server cost
```

**Today**: Full-featured embedded SRS with FSRS v6 + optional Anki export
**Tomorrow**: Interleaved chapter mode, streak tracking

---

## 4. Scope

### Phase 0 (MVP — this spec)

- Flashcard YAML schema (with `deck.id`, `why` field, Zod validation)
- Remark plugin: `libs/docusaurus/remark-flashcards/`
- React `<Flashcards />` component with:
  - Flip-card UI with CSS 3D animation
  - FSRS v6 scheduling via `ts-fsrs`
  - Confidence-based rating (Again/Hard/Good/Easy)
  - Card state persistence (localStorage with wire format)
  - Due card highlighting (which cards are due for review)
  - Lesson mode (single lesson deck)
- Anki `.apkg` export (build-time generation via `anki-apkg-export`, download button)
- Pilot content: `thesis.md`, `why-ai-is-non-negotiable.md`, `preface-agent-native.md`
- CI: Zod schema validation of all `.flashcards.yaml` files

### Phase 1 (Scale + Interleaving)

- `/flashcard-author` skill for AI-assisted deck generation (lesson/chapter/part scope)
- Flashcard YAML for all 85 chapters
- Chapter mode: interleaved review across all lessons in a chapter
- Chapter/Part aggregate Anki decks

### Phase 2 (Engagement)

- Study streak tracking (localStorage)
- "Cards due today" counter badge on lessons
- Cross-chapter study sessions
- Deck content sharing via URL (share YAML content link, NOT review progress)

### Out of Scope (Permanently)

- Server-side state / user accounts for flashcard progress
- Building our own SRS algorithm (FSRS exists, ts-fsrs implements it)
- Mochi/Quizlet/Brainscape integrations
- Self-hosted flashcard backends
- Sharing review progress between devices (requires server — out of scope)

---

## 5. Flashcard Data Schema

### File Location

```
# Co-located with each lesson
apps/learn-app/docs/01-General-Agents-Foundations/01-agent-factory-paradigm/
├── 01-digital-fte-revolution.md
├── 01-digital-fte-revolution.flashcards.yaml   ← NEW
├── 02-another-lesson.md
└── 02-another-lesson.flashcards.yaml           ← NEW

# Preface-level files (pilot)
apps/learn-app/docs/
├── thesis.md
├── thesis.flashcards.yaml                      ← NEW
├── preface-agent-native.md
├── preface-agent-native.flashcards.yaml        ← NEW
├── why-ai-is-non-negotiable.md
└── why-ai-is-non-negotiable.flashcards.yaml    ← NEW
```

**Naming convention**: `{file-stem}.flashcards.yaml` — where `file-stem` is the `.md` filename without extension (e.g., `thesis.md` → `thesis.flashcards.yaml`, `01-digital-fte-revolution.md` → `01-digital-fte-revolution.flashcards.yaml`). This is the literal filename, NOT the Docusaurus route slug (which strips numeric prefixes).

### YAML Schema

```yaml
# thesis.flashcards.yaml
deck:
  id: "thesis" # REQUIRED, immutable, kebab-case
  title: "The Agent Factory Thesis"
  description: "Core concepts from the Agent Factory thesis"
  tags: ["thesis", "agent-factory", "part-0"]
  version: 1 # Increment on breaking card changes

cards:
  - id: "thesis-001"
    front: "What is a Digital FTE?"
    back: "A role-based AI system that composes tools, spawns specialist agents, and delivers outcomes at scale — functioning as a full-time digital employee."
    tags: ["definition", "core-concept"]
    difficulty: "basic"

  - id: "thesis-002"
    front: "What is the difference between an AI tool and an AI employee?"
    back: "An AI tool performs a single task when invoked. An AI employee operates autonomously within a role — managing context, composing tools, and delivering complete outcomes without step-by-step human direction."
    tags: ["distinction", "core-concept"]
    difficulty: "intermediate"
    why: "Why would a business pay 10x more for an AI employee than an AI tool?"

  - id: "thesis-003"
    front: "What does 'Spec-Driven Development' mean?"
    back: "A development methodology where human-written specifications are the source of truth, and AI agents implement from those specs. The human specifies WHAT; the agent handles HOW."
    tags: ["methodology", "sdd"]
    difficulty: "intermediate"
    why: "Why must the spec be human-written rather than AI-generated?"
```

### Schema Rules

| Field                | Required | Type     | Constraints                                                                                                                                                    |
| -------------------- | -------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `deck.id`            | **Yes**  | string   | **Immutable.** Kebab-case, unique across all decks. Used as localStorage key and Anki deck ID. Never change after first publish.                               |
| `deck.title`         | Yes      | string   | Human-readable. Can be updated without breaking state.                                                                                                         |
| `deck.description`   | Yes      | string   | 1-2 sentences.                                                                                                                                                 |
| `deck.tags`          | Yes      | string[] | For filtering/grouping.                                                                                                                                        |
| `deck.version`       | Yes      | integer  | Start at 1. **Informational only in Phase 0** — no migration or state reset triggered. Logged to console on change. Future phases may use for migration gates. |
| `cards[].id`         | **Yes**  | string   | **Immutable.** Unique within deck, kebab-case. Maps to stable Anki note GUID and localStorage key. Never reuse a deleted ID.                                   |
| `cards[].front`      | Yes      | string   | The question. Plain text or minimal markdown. No yes/no questions.                                                                                             |
| `cards[].back`       | Yes      | string   | The answer. Max 3 sentences.                                                                                                                                   |
| `cards[].tags`       | No       | string[] | Card-level tags.                                                                                                                                               |
| `cards[].difficulty` | No       | enum     | `basic` \| `intermediate` \| `advanced`. Default: `basic`.                                                                                                     |
| `cards[].why`        | No       | string   | Elaborative interrogation prompt. Recommended for intermediate/advanced.                                                                                       |

### Immutability Rules

- `deck.id`: NEVER change. Changing resets all student progress for this deck.
- `cards[].id`: NEVER reuse. If a card is removed, its ID is retired permanently.
- `deck.title`, `deck.description`, card `front`/`back`/`why`: Safe to edit — state keys are `deck.id` + `cards[].id`.

### Content Guidelines

**What makes a good card:**

- **Front**: One clear question requiring active recall. Never yes/no.
- **Back**: Concise (1-3 sentences). The "why" not just the "what".
- **Atomic**: One concept per card. If you need "and", split it.
- **Why field**: Add for concepts where connecting to prior knowledge deepens understanding.

**Deck sizing:**

- 8-20 cards per lesson
- ~40% basic, ~40% intermediate, ~20% advanced
- Conceptual lessons (preface, thesis): 8-12 cards
- Technical lessons (Python syntax, APIs): 15-20 cards

**What NOT to card:**

- Explanations longer than 3 sentences
- Multi-step procedures (use exercises)
- Opinions or "it depends" answers
- Architecture diagrams

### CI Validation (Zod Schema)

All `.flashcards.yaml` files are validated in CI via a Zod schema:

```typescript
// scripts/validate-flashcards.ts
import { z } from "zod";

const CardSchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/, "Must be kebab-case"),
  front: z.string().min(10).max(300),
  back: z.string().min(10).max(500),
  tags: z.array(z.string()).optional(),
  difficulty: z.enum(["basic", "intermediate", "advanced"]).optional(),
  why: z.string().max(200).optional(),
});

const DeckSchema = z.object({
  deck: z.object({
    id: z.string().regex(/^[a-z0-9-]+$/),
    title: z.string().min(3).max(100),
    description: z.string().min(10).max(300),
    tags: z.array(z.string()).min(1),
    version: z.number().int().positive(),
  }),
  cards: z.array(CardSchema).min(5).max(30),
});

// Additional lint rules:
// - No duplicate card IDs within a deck
// - No duplicate card IDs across all decks (globally unique)
// - front must end with "?"
// - back must not start with "Yes" or "No"
// - difficulty distribution warning if >60% same level
```

**CI wiring**:

1. Add an Nx target in `apps/learn-app/project.json`:

```json
"validate-flashcards": {
  "executor": "nx:run-commands",
  "options": {
    "command": "pnpm exec tsx scripts/validate-flashcards.ts",
    "cwd": "apps/learn-app"
  }
}
```

2. Add as a dependency of the existing `lint` target:

```json
"lint": {
  "dependsOn": ["validate-flashcards"],
  // ... existing lint config
}
```

3. The validate script globs `docs/**/*.flashcards.yaml`, parses each with `yaml`, validates against the Zod schema, and exits non-zero on any failure (with file path + error details in stderr).

**Result**: `pnpm nx lint learn-app` (and `pnpm nx affected -t lint`) automatically validates all flashcard YAML. Failures block merge via existing CI pipeline.

---

## 6. State Management

### localStorage Wire Format

**[P0 fix]**: `Date` objects are not JSON-serializable. All dates stored as epoch milliseconds.

```typescript
// Storage key: `flashcards:${deck.id}`
// Example: `flashcards:thesis`

interface PersistedDeckState {
  schemaVersion: 1; // For future migrations
  deckVersion: number; // Matches deck.version from YAML
  cards: Record<string, PersistedCardState>; // Keyed by card.id
  lastReviewMs: number; // Epoch ms
}

interface PersistedCardState {
  dueMs: number; // Epoch ms — when card is next due
  stability: number; // FSRS stability
  difficulty: number; // FSRS difficulty (0-10)
  elapsed_days: number;
  scheduled_days: number;
  reps: number; // Total reviews
  lapses: number; // Times "Again" was pressed
  state: 0 | 1 | 2 | 3; // 0=New, 1=Learning, 2=Review, 3=Relearning
  lastReviewMs?: number; // Epoch ms
}
```

### Hydration Codec

```typescript
// useFSRS.ts — explicit field mapping (no spread) to prevent field leakage

function hydrate(p: PersistedCardState): Card {
  return {
    due: new Date(p.dueMs),
    stability: p.stability,
    difficulty: p.difficulty,
    elapsed_days: p.elapsed_days,
    scheduled_days: p.scheduled_days,
    reps: p.reps,
    lapses: p.lapses,
    state: p.state as State,
    last_review: p.lastReviewMs ? new Date(p.lastReviewMs) : undefined,
  };
}

function dehydrate(c: Card): PersistedCardState {
  return {
    dueMs: c.due.getTime(),
    stability: c.stability,
    difficulty: c.difficulty,
    elapsed_days: c.elapsed_days,
    scheduled_days: c.scheduled_days,
    reps: c.reps,
    lapses: c.lapses,
    state: c.state as 0 | 1 | 2 | 3,
    lastReviewMs: c.last_review?.getTime(),
  };
}
```

### State Reconciliation (Deck/Card Edits Across Releases)

When a student visits a lesson after deck content has been updated:

| Scenario                                                | Behavior                                                                                                 |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **New card added** (ID not in localStorage)             | Initialize as `state: New`. No progress lost.                                                            |
| **Card removed** (ID in localStorage but not in YAML)   | Ignore orphaned state. Don't show card. Don't delete state (avoids accidental loss if card is re-added). |
| **Card content edited** (same ID, different front/back) | Show updated content. Preserve SRS state — the student's memory of the concept carries over.             |
| **deck.version bumped**                                 | Log to console: `Flashcards deck "${id}" updated to v${version}`. No state reset.                        |
| **deck.id changed** (should never happen)               | Fresh start — old state is orphaned under old key. This is why `deck.id` is immutable.                   |
| **Unknown card IDs in localStorage**                    | Silently ignored during render. Cleaned up after 90 days of no access (Phase 2).                         |

### Storage Budget

- **Per deck**: ~2KB for 20 cards (JSON, no compression)
- **85 chapters x avg 3 lessons**: ~510KB total at full scale
- **localStorage limit**: 5-10MB (browser-dependent)
- **Headroom**: Comfortable. No compression needed.

---

## 7. Web Component: `<Flashcards />`

### Usage in MDX

```mdx
## Flashcards

<Flashcards />
```

Auto-discovers `{file-stem}.flashcards.yaml` in the same directory via remark plugin injection.

### Component States

The component has two modes:

**Browse mode** (first visit or casual review):

```
┌──────────────────────────────────────────┐
│  Flashcards: The Agent Factory Thesis    │
│  12 cards · ~5 min                       │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │                                  │    │
│  │   What is a Digital FTE?         │    │
│  │                                  │    │
│  │       Tap to reveal answer       │    │
│  │                                  │    │
│  └──────────────────────────────────┘    │
│                                          │
│  [Prev]   [1 / 12]   [Next]             │
│                                          │
│  ─── Actions ──────────────────────      │
│  [Begin Spaced Review]                   │
│  [Export to Anki (.apkg)]                │
│                                          │
└──────────────────────────────────────────┘
```

**Review mode** (SRS active — after "Begin Spaced Review"):

```
┌──────────────────────────────────────────┐
│  Review: The Agent Factory Thesis        │
│  4 cards due · 8 reviewed · 12 total     │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │                                  │    │
│  │   [Answer revealed]              │    │
│  │                                  │    │
│  │   Why: Why would a business pay  │    │
│  │   10x more for an AI employee    │    │
│  │   than an AI tool?               │    │
│  │                                  │    │
│  └──────────────────────────────────┘    │
│                                          │
│  How well did you know this?             │
│  [Again]  [Hard]  [Good]  [Easy]         │
│   <1m      6m      10m     4d            │
│                                          │
│  ─── Progress ──────────────────────     │
│  New: 4 · Learning: 3 · Review: 5       │
│                                          │
└──────────────────────────────────────────┘
```

**No flashcards available** (YAML file does not exist for this lesson):

```
┌──────────────────────────────────────────┐
│  Flashcards are not available for this   │
│  lesson yet.                             │
└──────────────────────────────────────────┘
```

Component renders a subtle muted message when `cards={null}`. No error, no blank space, no layout shift.

**Note**: This state ONLY occurs when no `.flashcards.yaml` file exists for the lesson (remark plugin injects `null`). If a `.flashcards.yaml` file exists but contains invalid YAML or fails schema validation, the **build fails** (see Section 9, step 6). Invalid content never reaches the component at runtime.

### Component Props

```typescript
interface FlashcardsProps {
  /** Injected by remark plugin at build time. null = YAML not found. undefined = not injected. */
  cards?: FlashcardDeck | null;
  /** Filter by tags */
  tags?: string[];
  /** Filter by max difficulty */
  maxDifficulty?: "basic" | "intermediate" | "advanced";
  /** Hide Anki export button */
  hideExport?: boolean;
}
```

### Interaction

| Action                   | Browse Mode        | Review Mode                     | Non-gesture equivalent |
| ------------------------ | ------------------ | ------------------------------- | ---------------------- |
| Click/tap card           | Flip (show answer) | Flip (show answer + why prompt) | Space key              |
| Arrow keys left/right    | Prev / Next        | N/A (SRS determines order)      | —                      |
| Space                    | Flip card          | Flip card                       | Click/tap              |
| 1/2/3/4 keys             | N/A                | Again / Hard / Good / Easy      | Click rating button    |
| Swipe left/right (touch) | Prev / Next        | N/A                             | Arrow keys / buttons   |
| Swipe up (touch)         | N/A                | Show answer                     | Space / tap            |

### Accessibility Requirements

| Requirement                  | Implementation                                                                                                                                  |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **`prefers-reduced-motion`** | Replace flip animation with instant swap (opacity crossfade).                                                                                   |
| **Screen reader**            | Front and back are both in DOM. Use `aria-live="polite"` on card region. Back is `aria-hidden` until flipped, then front becomes `aria-hidden`. |
| **Focus management**         | After flip: focus moves to first rating button. After rating: focus moves to next card.                                                         |
| **Keyboard-only**            | All interactions have keyboard equivalents (see table above). Tab order: card → rating buttons → navigation.                                    |
| **ARIA roles**               | Card: `role="region" aria-label="Flashcard {n} of {total}"`. Rating buttons: `role="group" aria-label="Rate your recall"`.                      |
| **Color independence**       | Rating buttons use color AND text labels. Don't rely on color alone.                                                                            |

### Styling

- Follows `DESIGN_SYSTEM.md`
- Uses `--ifm-color-*` CSS variables (Docusaurus theme)
- Dark/light mode support
- Responsive: full-width on mobile, max-width 600px on desktop
- Flip: CSS `transform: rotateY(180deg)` with `perspective(1000px)` (disabled if `prefers-reduced-motion`)
- Rating buttons: color-coded + text (Again=red, Hard=orange, Good=green, Easy=blue)
- Next review interval shown below each rating button

### Performance Budgets

| Metric                      | Target                                  |
| --------------------------- | --------------------------------------- |
| Component JS (gzipped)      | < 20KB (ts-fsrs ~15KB + component ~5KB) |
| First render (no SRS state) | < 50ms                                  |
| Flip animation              | 60fps, < 300ms duration                 |
| localStorage read/write     | < 5ms per operation                     |
| Layout shift (CLS)          | 0 — component reserves height on mount  |

---

## 8. Anki Export (Secondary)

### Build-Time .apkg Generation

```bash
node scripts/generate-anki-decks.js
```

**Output directory**: `apps/learn-app/static/flashcards/`

**Build wiring**: CI/deploy workflows (`pr-check.yml:38`, `deploy.yml:69`) call `pnpm build` directly inside `apps/learn-app/`, bypassing Nx. So `project.json` `dependsOn` alone is insufficient. The generator must run in BOTH paths:

1. **`build.sh` (CI/deploy path)** — add generation before Docusaurus build:

```bash
#!/bin/bash
set -euo pipefail  # Fail fast — any command failure aborts build
cd "$(dirname "$0")/.."

# Generate Anki .apkg files + manifest before Docusaurus copies static/
node scripts/generate-anki-decks.js

NODE_VERSION=$(node -v | cut -d'.' -f1 | sed 's/v//')
HEAP_SIZE="--max-old-space-size=4096"
# ... rest of existing build.sh
```

**Note**: The existing `build.sh` lacks `set -e`. Adding `set -euo pipefail` is required — it ensures both the Anki generator AND the Docusaurus build fail the CI job on error.

2. **`project.json` (Nx path)** — add for `pnpm nx build learn-app`:

```json
"generate-flashcards": {
  "executor": "nx:run-commands",
  "options": {
    "command": "node scripts/generate-anki-decks.js",
    "cwd": "apps/learn-app"
  }
},
"build": {
  "dependsOn": ["generate-flashcards"],
  // ... existing build config
}
```

This ensures `.apkg` files and `manifest.json` exist in `static/flashcards/` before Docusaurus copies static assets, regardless of whether the build is triggered via Nx or `pnpm build` directly.

### Manifest

The build script generates a manifest alongside the `.apkg` files:

```json
// apps/learn-app/static/flashcards/manifest.json
{
  "generated": "2026-02-21T12:00:00Z",
  "decks": {
    "thesis": {
      "apkgPath": "/flashcards/thesis.apkg",
      "title": "The Agent Factory Thesis",
      "cardCount": 12
    },
    "preface-agent-native": {
      "apkgPath": "/flashcards/preface-agent-native.apkg",
      "title": "PREFACE: The AI Agent Factory",
      "cardCount": 15
    }
  }
}
```

The `<Flashcards />` component uses `deck.id` to look up the `.apkg` path from the manifest. If no manifest entry exists for this deck, the export button is hidden (not an error).

### Anki Deck Properties

- **Deck name**: `AgentFactory::{Part}::{Chapter}::{Lesson}`
- **Card type**: Basic (front/back) with optional "Why" field
- **Fields**: Front, Back, Why (optional), Tags, SourceURL
- **Tags**: From YAML + auto-tags (`part-1`, `ch-01`, `difficulty::basic`)
- **Note GUID**: Deterministic hash of `deck.id + card.id` — stable across rebuilds, prevents duplicates on re-import
- **SourceURL**: Resolved using the same precedence as `chapter-manifest-plugin/index.js` (line 165):

  **Resolution order**:
  1. If MDX frontmatter contains `slug:` → use it (e.g., `slug: /General-Agents-Foundations/general-agents/cross-vendor-landscape`)
  2. Else → `normalizeToDocId(filePath)` (strip `^\d+-` from each segment)

  **Single source of truth for host**: Create `libs/docusaurus/shared/siteConstants.js` that reads `url` and `baseUrl` from `docusaurus.config.ts` at build time (using `tsx` to handle the TS import):

  ```js
  // libs/docusaurus/shared/siteConstants.js
  // Extracted once, imported by generate-anki-decks.js and any future consumer.
  // Uses tsx at build time to read the TS config.
  const { url, baseUrl } = require("../../apps/learn-app/docusaurus.config.ts");
  module.exports = { siteUrl: url, baseUrl };
  ```

  **If TS import proves problematic in CI**, fall back to env vars with defaults extracted from config at implementation time — but the implementation PR must validate they match `docusaurus.config.ts` values in a test.

  The script composes: `${siteUrl}${baseUrl}docs/${route.replace(/^\/+/, "")}` (strip leading slashes from route to prevent `docs//...` double-slash).

  ```
  Example A — no frontmatter slug:
    MDX path: apps/learn-app/docs/01-General-Agents-Foundations/01-agent-factory-paradigm/01-digital-fte-revolution.md
    normalizeToDocId → General-Agents-Foundations/agent-factory-paradigm/digital-fte-revolution
    SourceURL → https://agentfactory.panaversity.org/docs/General-Agents-Foundations/agent-factory-paradigm/digital-fte-revolution

  Example B — frontmatter slug override (slug: /General-Agents-Foundations/general-agents/cross-vendor-landscape):
    route after strip leading / → General-Agents-Foundations/general-agents/cross-vendor-landscape
    SourceURL → https://agentfactory.panaversity.org/docs/General-Agents-Foundations/general-agents/cross-vendor-landscape
  ```

  `normalizeToDocId` is currently duplicated in `summaries-plugin/index.js` (line 27) and `chapter-manifest-plugin/index.js` (line 78). Extract to a shared utility at `libs/docusaurus/shared/normalizeToDocId.js`. All three consumers (`summaries-plugin`, `chapter-manifest-plugin`, `generate-anki-decks.js`) import from there. See File Changes Summary (Section 10).

### Library Decision

**Selected**: [`anki-apkg-export`](https://www.npmjs.com/package/anki-apkg-export) (JS, MIT license).

Criteria met:

- Generates valid `.apkg` files importable by Anki desktop, AnkiWeb, AnkiDroid
- Supports custom note types (for the "Why" field)
- Supports stable note GUIDs
- No native dependencies (pure JS — works in CI)
- Actively maintained

If `anki-apkg-export` proves insufficient at implementation time, fallback to [`@nicolecomputer/anki-apkg-export`](https://github.com/nicolecomputer/anki-apkg-export) fork. Decision must be made in implementation sprint, not deferred further.

---

## 9. Docusaurus Integration

### Remark Plugin: `libs/docusaurus/remark-flashcards/`

**Location**: `libs/docusaurus/remark-flashcards/` (follows existing convention: `remark-content-enhancements`, `remark-interactive-python`, `remark-os-tabs`)

**Structure**:

```
libs/docusaurus/remark-flashcards/
├── index.js          # Remark plugin
├── package.json      # { "name": "remark-flashcards", "main": "index.js" }
└── project.json      # Nx project config
```

**Behavior**:

1. Walk AST for `<Flashcards />` JSX nodes
2. Resolve co-located `{file-stem}.flashcards.yaml` using `(file.history?.[0] ?? file.path ?? "").replace(/\\/g, "/")` (follows `remark-interactive-python` convention at `index.js:35` — `file.history[0]` is the canonical path in VFile)
3. Parse YAML, validate against schema
4. Inject parsed deck data as `cards` prop: `<Flashcards cards={...} />`
5. If `.flashcards.yaml` not found: inject `cards={null}` — component handles gracefully
6. If `.flashcards.yaml` exists but is invalid YAML/schema: **fail the build**. Do NOT silently degrade. Invalid flashcard files are authoring bugs, not runtime conditions. Build failure forces the fix before deploy.

**Registration** in `docusaurus.config.ts`:

```typescript
remarkPlugins: [
  // ... existing plugins ...
  require("../../libs/docusaurus/remark-flashcards"),
],
```

### Dependencies

| Package            | Scope                   | Purpose                   | Size              |
| ------------------ | ----------------------- | ------------------------- | ----------------- |
| `ts-fsrs`          | learn-app runtime       | FSRS v6 SRS algorithm     | ~15KB gzipped     |
| `yaml`             | remark-flashcards build | YAML parsing              | Build only        |
| `anki-apkg-export` | scripts build           | .apkg generation          | Build/script only |
| `zod`              | scripts/CI              | Schema validation         | Build/CI only     |
| `tsx`              | scripts/CI (devDep)     | Run TS validation scripts | Build/CI only     |

### Global Registration

Register in `src/theme/MDXComponents.tsx` (note: `.tsx`, not `.ts`):

```typescript
import Flashcards from "@/components/Flashcards";

export default {
  ...MDXComponents,
  // ... existing components ...
  Flashcards,
};
```

---

## 10. File Changes Summary

### New Files

| File                                                             | Purpose                                          |
| ---------------------------------------------------------------- | ------------------------------------------------ |
| `libs/docusaurus/remark-flashcards/index.js`                     | Remark plugin: YAML → prop injection             |
| `libs/docusaurus/remark-flashcards/package.json`                 | Package config                                   |
| `libs/docusaurus/remark-flashcards/project.json`                 | Nx project config                                |
| `apps/learn-app/src/components/Flashcards/Flashcards.tsx`        | Main component (browse + review modes)           |
| `apps/learn-app/src/components/Flashcards/FlashcardCard.tsx`     | Individual card with flip animation              |
| `apps/learn-app/src/components/Flashcards/ReviewSession.tsx`     | SRS review mode with FSRS scheduling             |
| `apps/learn-app/src/components/Flashcards/RatingButtons.tsx`     | Again/Hard/Good/Easy with interval display       |
| `apps/learn-app/src/components/Flashcards/useFSRS.ts`            | Hook: ts-fsrs + localStorage + hydration codec   |
| `apps/learn-app/src/components/Flashcards/Flashcards.module.css` | Styles + flip animation + rating colors          |
| `apps/learn-app/src/components/Flashcards/index.ts`              | Barrel export                                    |
| `apps/learn-app/src/components/Flashcards/types.ts`              | Shared types (PersistedDeckState, etc.)          |
| `apps/learn-app/scripts/generate-anki-decks.js`                  | Build-time .apkg + manifest generator            |
| `apps/learn-app/scripts/validate-flashcards.ts`                  | Zod schema validation for CI                     |
| `apps/learn-app/docs/thesis.flashcards.yaml`                     | Pilot deck 1                                     |
| `apps/learn-app/docs/preface-agent-native.flashcards.yaml`       | Pilot deck 2                                     |
| `apps/learn-app/docs/why-ai-is-non-negotiable.flashcards.yaml`   | Pilot deck 3                                     |
| `apps/learn-app/src/__tests__/flashcards.test.tsx`               | Component unit tests                             |
| `apps/learn-app/src/__tests__/useFSRS.test.ts`                   | Hook + hydration codec tests                     |
| `libs/docusaurus/shared/normalizeToDocId.js`                     | Shared utility: strip `^\d+-` from path segments |

### Modified Files

| File                                               | Change                                                                                                                       |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `apps/learn-app/src/theme/MDXComponents.tsx`       | Register `<Flashcards />`                                                                                                    |
| `apps/learn-app/docusaurus.config.ts`              | Add `remark-flashcards` to remarkPlugins                                                                                     |
| `apps/learn-app/package.json`                      | Add `ts-fsrs` runtime dep; `anki-apkg-export`, `zod`, `tsx` dev deps                                                         |
| `apps/learn-app/project.json`                      | Add `generate-flashcards` and `validate-flashcards` Nx targets; add `generate-flashcards` to `build.dependsOn`               |
| `apps/learn-app/scripts/build.sh`                  | Add `node scripts/generate-anki-decks.js` before Docusaurus build (CI/deploy path bypasses Nx)                               |
| `libs/docusaurus/summaries-plugin/index.js`        | Import `normalizeToDocId` from `../shared/normalizeToDocId.js` instead of defining locally                                   |
| `libs/docusaurus/chapter-manifest-plugin/index.js` | Import `normalizeToDocId` from `../shared/normalizeToDocId.js` instead of defining locally (eliminates duplicate at line 78) |
| `apps/learn-app/docs/thesis.md`                    | Add `<Flashcards />` section                                                                                                 |
| `apps/learn-app/docs/preface-agent-native.md`      | Add `<Flashcards />` section                                                                                                 |
| `apps/learn-app/docs/why-ai-is-non-negotiable.md`  | Add `<Flashcards />` section                                                                                                 |

---

## 11. Requirements Traceability

### Functional Requirements

| ID        | Requirement                                                 | Acceptance Test                                                                                                                                                                                                                                            | Phase |
| --------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| **FR-01** | Card flip animation shows front then back on interaction    | Unit: click triggers flip state. Visual: CSS 3D transform renders.                                                                                                                                                                                         | 0     |
| **FR-02** | FSRS v6 schedules next review based on rating               | Unit: `useFSRS` returns correct `due` after each rating.                                                                                                                                                                                                   | 0     |
| **FR-03** | Rating buttons (Again/Hard/Good/Easy) display next interval | Unit: interval text matches ts-fsrs output.                                                                                                                                                                                                                | 0     |
| **FR-04** | Review mode shows only due cards                            | Unit: filter cards where `dueMs <= Date.now()`.                                                                                                                                                                                                            | 0     |
| **FR-05** | State persists in localStorage across reloads               | Integration: write state, reload page, verify state restored.                                                                                                                                                                                              | 0     |
| **FR-06** | Elaborative "Why?" shown on back for cards that have it     | Unit: `why` field renders when present, absent when not.                                                                                                                                                                                                   | 0     |
| **FR-07** | Browse mode: prev/next navigation                           | Unit: arrow keys and buttons change current card index.                                                                                                                                                                                                    | 0     |
| **FR-08** | Anki export downloads valid .apkg with correct SourceURL    | Integration: generate .apkg, import into Anki, verify fields. Unit tests for SourceURL: (a) non-slug lesson uses normalizeToDocId, (b) slug-override lesson uses frontmatter.slug, (c) no double-slash in output, (d) non-root baseUrl composes correctly. | 0     |
| **FR-09** | Remark plugin injects YAML data at build time               | Integration: build succeeds, component receives `cards` prop.                                                                                                                                                                                              | 0     |
| **FR-10** | Missing .flashcards.yaml shows graceful fallback            | Unit: `cards={null}` renders muted "not available" message.                                                                                                                                                                                                | 0     |
| **FR-11** | State reconciliation handles added/removed cards            | Unit: new card ID → New state; removed card ID → ignored.                                                                                                                                                                                                  | 0     |
| **FR-12** | Invalid .flashcards.yaml fails the build                    | Integration: malformed YAML → build exits non-zero with file path + error.                                                                                                                                                                                 | 0     |
| **FR-13** | Interleaved chapter mode                                    | Integration: aggregate cards across lessons, shuffle.                                                                                                                                                                                                      | 1     |

### Non-Functional Requirements

| ID         | Requirement                       | Metric                                                                            | Phase |
| ---------- | --------------------------------- | --------------------------------------------------------------------------------- | ----- |
| **NFR-01** | Component JS budget               | < 20KB gzipped (ts-fsrs + component)                                              | 0     |
| **NFR-02** | No layout shift                   | CLS = 0 for pages with flashcards                                                 | 0     |
| **NFR-03** | Mobile responsive                 | Readable and functional at 375px viewport                                         | 0     |
| **NFR-04** | Animation respects reduced motion | `prefers-reduced-motion: reduce` → no flip, use crossfade                         | 0     |
| **NFR-05** | Screen reader accessible          | `aria-live`, `aria-hidden` toggling, focus management                             | 0     |
| **NFR-06** | localStorage budget               | < 600KB for full 85-chapter deployment                                            | 0     |
| **NFR-07** | Build time impact                 | < 5s added to both `pnpm build` (CI path) and `pnpm nx build learn-app` (Nx path) | 0     |
| **NFR-08** | Keyboard navigable                | All interactions via keyboard (Space, 1-4, arrows, Tab)                           | 0     |
| **NFR-09** | Dark/light theme                  | Renders correctly in both Docusaurus themes                                       | 0     |

---

## 12. Success Criteria

### Phase 0 — Done When:

**Component (FR-01 through FR-07, FR-10, FR-11):**

- [ ] `<Flashcards />` renders in all 3 pilot pages
- [ ] Card flip animation works (CSS 3D, smooth, reduced-motion fallback)
- [ ] Browse mode: prev/next, card counter, keyboard nav
- [ ] Review mode: FSRS scheduling, due cards first, rating buttons with intervals
- [ ] "Why?" prompt renders on applicable cards
- [ ] State persists across reloads (wire format with epoch ms)
- [ ] State reconciliation: new cards initialize, removed cards ignored
- [ ] Missing YAML: graceful fallback message

**Accessibility (NFR-04, NFR-05, NFR-08):**

- [ ] `prefers-reduced-motion` disables flip animation
- [ ] Screen reader: aria-live on card, aria-hidden toggling, focus management
- [ ] Full keyboard navigation: Space, 1-4, arrows, Tab
- [ ] Color + text labels on rating buttons

**Anki export (FR-08):**

- [ ] Export button downloads valid `.apkg` (manifest lookup)
- [ ] Imports into Anki desktop + AnkiDroid without errors
- [ ] Cards show front, back, why, tags, source URL
- [ ] SourceURL correct for non-slug lesson (normalizeToDocId path)
- [ ] SourceURL correct for slug-override lesson (frontmatter.slug path)
- [ ] No double-slash in any generated SourceURL
- [ ] Button hidden when no manifest entry exists

**Infrastructure (FR-09, FR-12, NFR-01, NFR-02, NFR-07):**

- [ ] Remark plugin in `libs/docusaurus/remark-flashcards/` works
- [ ] Invalid `.flashcards.yaml` (malformed YAML or schema violation) fails the build with file path + error in stderr
- [ ] `pnpm build` (CI path via build.sh) succeeds, < 5s impact from flashcards
- [ ] `pnpm nx build learn-app` (Nx path) succeeds, < 5s impact from flashcards
- [ ] `build.sh` has `set -euo pipefail` — generator failure aborts build
- [ ] No layout shift (CLS = 0)
- [ ] JS budget < 20KB gzipped
- [ ] CI validates all `.flashcards.yaml` via Zod

**Tests:**

- [ ] Unit tests for `useFSRS` hook (hydration, dehydration, scheduling)
- [ ] Unit tests for state reconciliation
- [ ] Unit tests for component rendering (browse, review, fallback)
- [ ] Tests run in existing Vitest setup (`src/__tests__/`)

---

## 13. Flashcard Authoring Skill (Phase 1)

### `/flashcard-author` Skill

**Scope**: Generate `.flashcards.yaml` for a lesson, chapter, or part.

**Invocation**:

```
/flashcard-author lesson apps/learn-app/docs/.../01-digital-fte-revolution.md
/flashcard-author chapter 5
/flashcard-author part 2
```

**Behavior**:

1. Read target lesson(s)
2. Extract atomic concepts (definitions, primitives, protocols, commands, constraints)
3. Generate YAML following schema + content guidelines
4. Validate output against Zod schema
5. Write `.flashcards.yaml` files co-located with lessons

**Quality rules** (built into skill):

- No yes/no fronts
- Back ≤ 3 sentences
- 8-20 cards per lesson
- ~40% basic / ~40% intermediate / ~20% advanced
- `why` field on intermediate/advanced architectural cards
- IDs follow `{deck-id}-{nnn}` convention

**Output**: Human reviews generated YAML, commits. AI-generated + human-curated workflow.

---

## 14. Decisions Made

| Decision               | Choice                                          | Rationale                                                                                                    |
| ---------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Primary experience     | Embedded web component                          | Zero friction, full UX control, works on mobile web                                                          |
| SRS algorithm          | FSRS v6 via `ts-fsrs` v4.x                      | Same as Anki, 99.6% better than SM-2, MIT, TypeScript                                                        |
| State storage          | localStorage (epoch ms wire format)             | Zero server cost, serializable, acceptable loss on clear                                                     |
| State key              | `flashcards:${deck.id}`                         | Immutable deck.id prevents key instability                                                                   |
| Anki role              | Secondary export, hidden if no manifest         | Power users only — not the default experience                                                                |
| Rating system          | Again/Hard/Good/Easy                            | FSRS native ratings, trains metacognition (CBR)                                                              |
| Data format            | YAML co-located with lessons                    | Version-controlled, human-reviewable, CI-validatable via Zod                                                 |
| `why` field            | Optional per card                               | Elaborative interrogation — deepens encoding                                                                 |
| Remark plugin          | `libs/docusaurus/remark-flashcards/`            | Follows existing convention (remark-os-tabs, etc.)                                                           |
| Component registration | `MDXComponents.tsx`                             | Matches Quiz, PDFViewer, etc.                                                                                |
| Anki library           | `anki-apkg-export`                              | Pure JS, MIT, supports custom note types + stable GUIDs                                                      |
| Deck sharing (Phase 2) | Content link only, NOT progress                 | No server = no cross-device progress sync                                                                    |
| Invalid YAML at build  | Fail the build (not degrade)                    | Invalid flashcard files are authoring bugs, not runtime                                                      |
| `deck.version` role    | Informational only (Phase 0)                    | Console log on change; no migration/reset. Future phases may gate on it                                      |
| `src` prop in MVP      | Not included — strictly co-located              | Phase 0 only supports `{file-stem}.flashcards.yaml` discovery. External `src` deferred to Phase 1+ if needed |
| SourceURL derivation   | frontmatter.slug first, else `normalizeToDocId` | Config-driven host (`siteConfig.url` + `baseUrl`), matches `chapter-manifest-plugin` precedence              |

## 15. How We're Better Than Basic Anki

| Capability                | Basic Anki                    | Our Embedded Experience               |
| ------------------------- | ----------------------------- | ------------------------------------- |
| SRS algorithm             | FSRS v6                       | FSRS v6 (identical)                   |
| Zero friction start       | Install app → import → review | Scroll down → start                   |
| Elaborative interrogation | Not built-in                  | "Why?" prompts on complex cards       |
| Context-aware             | Cards isolated from content   | Cards live inside the lesson          |
| Interleaving (Phase 1)    | Manual deck management        | One-click chapter mode                |
| Theming                   | Anki's UI                     | Our brand, dark/light, responsive     |
| Mobile                    | Requires app install          | Works in browser now                  |
| Content updates           | Must re-import .apkg          | Automatic on page load                |
| Reduced-motion support    | Limited                       | Full `prefers-reduced-motion` support |

---

## References

### Learning Science

- [Testing Effect — Karpicke & Roediger (2008)](https://www.science.org/doi/10.1126/science.1152408)
- [FSRS Algorithm — 99.6% superiority over SM-2](https://github.com/open-spaced-repetition/awesome-fsrs)
- [Confidence-Based Repetition — Brainscape](https://www.brainscape.com/academy/confidence-based-repetition-definition/)
- [Interleaving — Retrieval Practice org](https://www.retrievalpractice.org/interleaving)
- [Elaborative Interrogation (2025)](https://www.tandfonline.com/doi/full/10.1080/02702711.2025.2482627)
- [Retrieval Practice for Complex Concepts (2025)](https://www.sciencedirect.com/science/article/pii/S0959475225001434)
- [Desirable Difficulties & Distributed Practice](https://journals.physiology.org/doi/full/10.1152/advan.00173.2025)
- [Spaced Repetition Algorithms Comparison](https://www.brainscape.com/academy/comparing-spaced-repetition-algorithms/)

### Implementation

- [ts-fsrs v4.x — TypeScript FSRS v6](https://github.com/open-spaced-repetition/ts-fsrs)
- [anki-apkg-export](https://www.npmjs.com/package/anki-apkg-export)
- [Open Spaced Repetition project](https://github.com/open-spaced-repetition)

### Existing Infrastructure

- `<Quiz />` — `apps/learn-app/src/components/quiz/Quiz.tsx` (precedent for interactive MDX)
- `MDXComponents.tsx` — `apps/learn-app/src/theme/MDXComponents.tsx` (registration point)
- `libs/docusaurus/remark-*` — existing remark plugin convention
- `vitest.config.ts` — test setup with `@/` alias, jsdom, CSS modules
- `DESIGN_SYSTEM.md` — styling guidelines
