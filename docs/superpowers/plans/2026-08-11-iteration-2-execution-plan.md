# Iteration 2 Execution Plan — Deck Build Plan

> **For agentic workers:** Build the deck via `user-ppt-mcp`. Discover tool schemas with GetMcpTools before calling tools. Do not edit the Cursor plan file. Do not create a git commit unless asked.

**Goal:** Produce `Iteration 2 Execution Plan.pptx` — 10 slides, ~10 minutes, Iteration 1 Milestones visual style, with ~1-minute speaker notes on every slide.

**Architecture:** Create a new 16:9 PowerPoint via MCP COM interop. Match navy/blue accent patterns from Iteration 1 Milestones (accent bar, section labels, overview cards, one message per slide). Content source: `docs/superpowers/specs/2026-08-11-iteration-2-execution-plan-design.md`.

**Tech Stack:** Microsoft PowerPoint desktop, PptMcp (`user-ppt-mcp`).

## Global Constraints

- Exactly 10 main slides; no appendix required.
- Path: `Iteration 2 Execution Plan.pptx` at workspace root.
- 16:9 widescreen; light technical-blueprint; navy/blue accents.
- Do **not** modify `Iteration 1 Milestones.pptx` content.
- PowerPoint COM is single-instance: `file(action:'list')` first; close any open session before create/open.
- Speaker notes (~1 minute) on every slide.
- No git commit unless explicitly requested.

## File structure

- Spec (done): `docs/superpowers/specs/2026-08-11-iteration-2-execution-plan-design.md`
- This plan: `docs/superpowers/plans/2026-08-11-iteration-2-execution-plan.md`
- Output: `Iteration 2 Execution Plan.pptx`
- Optional preview export folder if MCP image export is used during QA

## Colour / layout reference (Iteration 1 Milestones style)

- Slide size: 13.333" × 7.5" (16:9)
- Accent bar at top (~0.12" height), navy/blue
- Section label (small, bold accent) under bar
- Title (~28–32 pt bold navy)
- Body Calibri; muted secondary text for subtitles
- Cards: rounded rectangles with pale fill or white + thin line
- Metric callouts for Iteration 1 numbers only where cited
- Margins ~0.55" left/right

---

### Task 1: Session hygiene and create deck

**Files:**
- Create: `Iteration 2 Execution Plan.pptx`

- [ ] **Step 1: Discover MCP schemas**

Call `GetMcpTools` for `user-ppt-mcp` tools needed: `file`, `slide`, `shape`, `text`, `notes`, `pagesetup`, `export`/`image`, `accessibility`.

- [ ] **Step 2: List open sessions**

```
file(action: "list")
```

If another session is open (e.g. Iteration 1 Milestones), close it:

```
file(action: "close", session_id: "<id>", save: false)  # or true if that deck had intentional unsaved work you must keep
```

Do not edit Iteration 1 Milestones content.

- [ ] **Step 3: Create new presentation**

```
file(action: "create", path: "<workspace>\\Iteration 2 Execution Plan.pptx", show: true)
```

- [ ] **Step 4: Set 16:9 page setup**

Use `pagesetup` (or equivalent) for widescreen 16:9 / 13.333 × 7.5 in.

---

### Task 2: Build slides 1–3 (title, recap, overview)

- [ ] **Step 1: Slide 1 — Title**

Content:
- Title: Iteration 2 Execution Plan
- Subtitle: Priority search → validated research workstreams
- Footer line: UQ × Northrop Grumman · Semester 2

Notes (~1 min): Frame Iteration 2 as moving from a working priority VNS baseline to validated research workstreams. Stakeholder takeaway: we know what works, what is hill-climbing, and what we will test next.

Layout: large title, short subtitle, accent bar; minimal chrome.

- [ ] **Step 2: Slide 2 — Where Iteration 1 left us**

Content:
- Section: Iteration 1 recap
- Title: Priority VNS delivered a practical baseline
- Metric cards: Min availability 15 → 18 · Runtime ~15.4 s
- Bullets: deterministic priority buckets; rule-aware rebuild; incremental availability; **acceptance is strict hill-climbing**

Notes: Celebrate measured gains, then pivot: the search machinery is strong, but accept/filter logic only climbs. That gap is why SA is an integration question, not a free lunch.

- [ ] **Step 3: Slide 3 — Iteration 2 overview**

Content:
- Section: Roadmap
- Title: Four workstreams for Semester 2
- Four cards:
  1. SA + VNS hybrid
  2. Operational constraints
  3. Hyperparameter analysis
  4. Initial stagger

Notes: Overview of the rest of the talk. Deep-dive SA first (slides 4–5), then one slide each for constraints, hyperparameters, stagger, then timeline and success criteria.

---

### Task 3: Build slides 4–5 (SA analysis + hybrid design)

- [ ] **Step 1: Slide 4 — SA integration analysis**

Content:
- Section: SA integration
- Title: Compatible as layers — not a drop-in
- Two columns / cards:
  - **Keep (proposal):** prioritise_events, rebuild, incremental availability, VNS shift_sets, best tracking
  - **Change (acceptance):** improve-only filter, priority early-exit, strict accept / stop-on-no-improve, lex → energy or staged Metropolis
- Verdict callout: Priority + VNS = proposal/evaluation; SA replaces acceptance

Notes: Walk the verdict from code. SA needs worsening moves sometimes; current filter and early-exit prevent that. Composition is clean if we keep proposals and swap acceptance.

- [ ] **Step 2: Slide 5 — Hybrid design + work plan**

Content:
- Section: Recommended design
- Title: Priority-biased proposals + SA acceptance
- Flow: Priority buckets → VNS neighbourhoods → Metropolis / staged accept → best-so-far
- Work bullets: define energy or staged rule; freeze priority VNS baseline; experiment SA variants

Notes: Recommend hybrid and experimental protocol. Baseline stays deterministic priority VNS; SA is additive experiment with clear abandon criteria later.

---

### Task 4: Build slides 6–8 (constraints, hyperparameters, stagger)

- [ ] **Step 1: Slide 6 — Operational & logistics constraints**

Content:
- Section: Constraints
- Title: Availability-max is necessary but not sufficient
- Bullets: under-constrained vs ops/logistics; prototype availability-max windows; surrounding event move limits; local std control; validate constraint validity separately

Notes: Stakeholders care about operable schedules, not only higher min availability. Constraints are a first-class workstream, not an afterthought.

- [ ] **Step 2: Slide 7 — Hyperparameter analysis**

Content:
- Section: Sensitivity
- Title: Which knobs actually move the needle?
- Bullets: fixed today — `shift_sets`, `max_iters`, priority early-exit; if SA — temperature / cooling; sensitivity on heavy data; report quality vs runtime trade-offs

Notes: Avoid tuning theatre. Document knobs, sweep on heavy data, publish which matter.

- [ ] **Step 3: Slide 8 — Initial stagger**

Content:
- Section: Starting point
- Title: Separate start effect from algorithm gain
- Bullets: local search depends on start; controlled stagger variants; same seed/protocol across algorithms; attribute gains correctly

Notes: Without stagger controls, a “better algorithm” may just be a luckier start. Design experiments to isolate that.

---

### Task 5: Build slides 9–10 (timeline + success/risks)

- [ ] **Step 1: Slide 9 — Execution timeline**

Content:
- Section: Plan
- Title: From baseline freeze to decision gate
- Timeline nodes (L→R):
  1. Freeze baseline
  2. SA acceptance layer
  3. Energy / staged rule
  4. Constraint prototypes
  5. Sensitivity + stagger
  6. Decision gate

Notes: Order work so comparisons stay fair. Freeze baseline early; only then change acceptance and add constraint/sensitivity work before go/no-go.

- [ ] **Step 2: Slide 10 — Success criteria & risks**

Content:
- Section: Decision criteria
- Title: What “good enough” looks like — and when to stop
- Success: quality (min / std / avg), runtime budget, constraint validity
- Risks / exits: abandon SA if no gain vs baseline; staged acceptance if lex energy thrashing; keep priority VNS if hybrid underperforms

Notes: Close with measurable gates. Research continues only where evidence supports it.

---

### Task 6: Speaker notes pass

- [ ] **Step 1:** For each slide 1–10, set notes via `notes` tool to ~1 minute of spoken content matching the design spec takeaways.
- [ ] **Step 2:** Spot-check that no slide is missing notes.

---

### Task 7: QA and save

- [ ] **Step 1: Accessibility** — run `accessibility` audit if available; fix critical text/contrast issues that MCP can address.
- [ ] **Step 2: Thumbnails / export** — export slide images or use thumbnail inspection; verify text fits, cards align, no overflow.
- [ ] **Step 3: Verify** — slide count = 10; 16:9; notes present; Iteration 1 metrics cited only where intended.
- [ ] **Step 4: Save and close**

```
file(action: "close", session_id: "<id>", save: true)
```

Confirm file exists at workspace root and session list is empty (or no longer holds this file).

---

## Slide content checklist (exact 10)

| # | Title focus |
|---|-------------|
| 1 | Iteration 2 Execution Plan (title) |
| 2 | Where Iteration 1 left us |
| 3 | Iteration 2 overview (4 workstream cards) |
| 4 | SA integration analysis |
| 5 | Hybrid design + work plan |
| 6 | Operational & logistics constraints |
| 7 | Hyperparameter analysis |
| 8 | Initial stagger |
| 9 | Execution timeline |
| 10 | Success criteria & risks |

## Done when

- Design spec and this plan exist under `docs/superpowers/`
- `Iteration 2 Execution Plan.pptx` saved with 10 slides and notes
- QA completed; MCP session closed with `save: true`
- No commits created unless requested
