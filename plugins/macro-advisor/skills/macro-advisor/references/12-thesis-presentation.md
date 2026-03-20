# Skill 12: Thesis Presentation

## Objective

Render investment theses into readable, visual documents that a human actually wants to read. This skill takes the analytical output from Skill 7 (thesis files) and produces presentation-quality versions — with charts, structured evidence, and clear narrative — for two consumption modes: the full thesis report (Layer 2) and the briefing card (Layer 3, consumed by Skill 9).

This skill is the presentation layer. It does not generate analytical content — that's Skill 7 and Skill 11. It renders what they produce.

---

## When to Invoke

1. **After Skill 7 generates or updates a thesis.** Any new DRAFT or status change to an ACTIVE thesis triggers a re-render.
2. **During the Sunday chain.** After Skill 7 completes monitoring, Skill 12 renders updated versions of all active theses before Skill 9 compiles the briefing.
3. **Manual invocation.** When the user wants to review a specific thesis in presentation format.

Chain position: runs after Skill 7, before Skill 9.

---

## Inputs

- Thesis file from `outputs/theses/active/` (ACTIVE- or DRAFT- prefixed)
- For structural theses: the corresponding Skill 11 research brief from `outputs/research/`
- Data snapshot from `outputs/data/latest-snapshot.json` — for chart generation
- Full data file from `outputs/data/latest-data-full.json` — for time series charts
- Prior week's thesis presentation (if exists) — for change tracking

---

## Two Output Modes

### Mode A: Full Thesis Report (Layer 2)

The deep-read document. When someone clicks into a thesis from the briefing, this is what they see. It should read like a well-structured investment memo — clear narrative, supporting evidence, visual data, honest about risks.

**Structure varies by thesis type:**

#### Tactical Thesis Report

```markdown
# [Thesis Name]
**Status:** [DRAFT/ACTIVE/STRENGTHENING/WEAKENING] | **Generated:** [Date] | **Weeks Active:** [N]

---

## The Bet
[The plain English summary from the thesis file. One paragraph. This is the hook — if the reader stops here, they still understand what's being proposed and why.]

---

## Why This Works (Mechanism)
[The causal chain from the thesis file, but written as connected prose rather than numbered steps. Each link in the chain should flow into the next. Include the "why" at each step, not just the "what".]

---

## The Evidence
[Key data points that support the thesis. Each with a current reading, direction, and what it implies. Pull these from the data snapshot.]

### Chart: [Most relevant metric for this thesis]
[Generate a Chart.js time series of the key variable(s) driving this thesis. Use the full data file for trailing history. Annotate the chart with the thesis generation date and any key events.]

---

## What Has To Be True
[Assumptions from the thesis file, each with current status.]

| Assumption | Status | Current Reading | Source |
|-----------|--------|----------------|--------|
| [Assumption 1] | INTACT / UNDER PRESSURE / BROKEN | [data] | [source, date] |
| [Assumption 2] | ... | ... | ... |

---

## Risks
**Kill switch:** [From thesis file — the specific condition that kills this thesis. Bold and prominent.]

**What could go wrong:** [Render the consensus view and key risks from the thesis file as connected prose. Do not add, remove, or reweight risks — present what Skill 7 wrote.]

---

## Expression

**CRITICAL: Preserve the First / Second / Third / Avoid order labels from the Skill 7 thesis file.** These signal the causal hierarchy of the trade — first-order is the obvious direct play, second-order is less obvious and slower to price in, third-order is the contrarian or defensive angle. Do not flatten these into a generic table. The order label IS the insight.

| Order | ETF | Direction | Rationale |
|-------|-----|-----------|-----------|
| First-order | [ticker] | [buy/sell] | [one sentence — why this is the direct play] |
| Second-order | [ticker] | [buy/sell] | [one sentence — what causal link, why the market is slower to see it] |
| Third-order | [ticker] | [buy/sell] | [one sentence — the contrarian or hedge angle] |
| Avoid | [ticker] | reduce | [one sentence — why this underperforms if thesis plays out] |

---

## Status History
[If thesis has been active for 2+ weeks, show a brief log of weekly status changes.]

| Week | Status | Key Change |
|------|--------|-----------|
| [W-2] | [status] | [what changed] |
| [W-1] | [status] | [what changed] |
| Current | [status] | [what changed] |

---

## Source
**Technical thesis file:** `outputs/theses/active/[ACTIVE-or-DRAFT]-[thesis-name].md`
[This links the presentation to the underlying structured thesis with raw assumptions, kill switch definitions, and mechanism details.]
```

#### Structural Thesis Report

Everything in the tactical report, plus these additional sections inserted after "The Evidence":

```markdown
## Structural Foundation
[From the Skill 11 research brief. The binding constraints — physical, economic, or structural realities that bound what's possible. Each with a number, source, and why it matters.]

### Chart: Supply-Demand Trajectory
[Generate a chart showing the supply-demand gap trajectory from the research brief data. If the thesis involves a commodity, show supply vs. demand curves or projected deficit. If it involves a structural shift (e.g., capex cycle), show the relevant investment vs. requirement trajectory.]

---

## What We Have To Believe
[The independently testable assumptions from the structural thesis template. More prominent than the tactical version because these are the core of a structural thesis.]

| # | Assumption | Testable By | Current Status | Last Checked |
|---|-----------|-------------|---------------|-------------|
| 1 | [assumption] | [observable data point] | INTACT | [date] |
| 2 | [assumption] | [observable data point] | INTACT | [date] |
| 3 | ... | ... | ... | ... |

---

## The Bear Case (Steelmanned)
[The contrarian stress-test from the thesis file, rendered prominently. This is not a footnote — it gets the same visual weight as the bull case. Include the quantified contrarian claims table from the Skill 11 brief.]

### Quantified Bear Claims
| Claim | Impact | Source | Date |
|-------|--------|--------|------|
| [claim] | [quantified] | [source] | [date] |
| ... | ... | ... | ... |

---

## Conviction / Expression / Timing
**Thesis conviction:** [High/Medium/Low] — [one sentence on why]
**Entry timing:** [Immediate/Scale in/Defer] — [current cyclical picture assessment]
**Monitoring approach:** Weekly kill switch check. Full structural review triggered by assumption pressure, binding constraint data changes, or regime shifts.
```

### Mode B: Briefing Card (Layer 3)

A compressed summary for the Monday Briefing thesis table. Skill 9 consumes this directly. The format below matches what Skill 9's Active Theses section expects — if Skill 9's template changes, this format should be updated to match.

```markdown
### [Thesis Name] [TACTICAL/STRUCTURAL badge]
**Status:** [emoji + status] | **Conviction:** [H/M/L] | **Weeks Active:** [N]
[One sentence: what's the bet, in plain English.]
**This week:** [One sentence: what changed, what to do.]
**Key risk:** [One sentence: the kill switch or nearest risk, in plain English.]
```

---

## Chart Generation

This skill generates thesis-specific charts using the system's data. Charts are embedded directly in the HTML dashboard (via Chart.js in `generate_dashboard.py`) rather than as separate image files.

### Chart Selection Logic

For each thesis, identify the 1-2 most relevant data series from the snapshot:

**Rate/yield theses:** Plot the relevant yield(s) from `snapshot.rates` — e.g., 10Y yield, 2Y-10Y spread, real rate.
**Credit theses:** Plot HY OAS or IG OAS from `snapshot.credit` with percentile bands.
**Liquidity theses:** Plot M2 growth, NFCI, or Fed balance sheet from `snapshot.liquidity`.
**Growth theses:** Plot the relevant growth indicator from `snapshot.growth` — unemployment, claims, LEI, retail sales.
**Inflation theses:** Plot CPI/PCE/breakevens from `snapshot.inflation`.
**Commodity/structural theses:** Plot the commodity price from `snapshot.markets` — gold, oil, copper. For structural theses, overlay with a demand driver if data is available.
**Equity theses:** Plot the relevant index or sector ETF from `snapshot.markets`.

### Chart Data Format

For each thesis that gets a chart, produce a JSON block that `generate_dashboard.py` can consume:

```json
{
  "thesis_name": "string",
  "chart_type": "line",
  "title": "string",
  "datasets": [
    {
      "label": "string",
      "data_series": "snapshot.path.to.series",
      "color": "#hex"
    }
  ],
  "annotations": [
    {
      "type": "line",
      "value": "number or date",
      "label": "string"
    }
  ]
}
```

Save chart specifications as **separate JSON files** alongside the thesis presentation files: `outputs/theses/presentations/[thesis-name]-charts.json`. The dashboard generator reads these files to render the charts as interactive Chart.js canvases.

**CRITICAL: Do NOT embed chart JSON in the report markdown.** The chart spec is machine-readable input for the dashboard renderer, not human-readable content. If you put the JSON in the report, it shows up as a raw code block in the dashboard instead of a rendered chart. The report should reference the chart ("See chart above" or similar) — the dashboard generator handles rendering.

---

## Output Files

- **Full thesis reports:** `outputs/theses/presentations/[thesis-name]-report.md`
- **Briefing cards:** Embedded directly in the Skill 9 briefing output (not separate files)
- **Chart specs:** `outputs/theses/presentations/[thesis-name]-charts.json`

---

## Quality Standards

### The Reader Test
Read the full thesis report aloud. Would a smart friend who invests through ETFs understand the thesis, the evidence, the risks, and the expression without Googling anything? If not, rewrite the section that fails.

### Evidence Balance
The bear case section must be visually and substantively comparable to the bull case. If the evidence section has 5 paragraphs and the bear case has 2 sentences, the presentation is dishonest — go back to the thesis file or research brief and render the contrarian case properly.

### Chart Relevance
Every chart must directly support the thesis mechanism. No decorative charts. If the thesis is about credit stress, the chart shows credit spreads — not the S&P 500 just because it looks interesting. One well-chosen chart beats three tangential ones.

### Change Tracking
When re-rendering an active thesis, highlight what changed since last week. New data, assumption status changes, kill switch proximity. The reader should see the delta, not just the current state.

### No Editorializing
This skill renders what Skill 7 and Skill 11 produced. It does not add analytical conclusions, upgrade/downgrade conviction, or introduce new assumptions. If the underlying thesis is weak, the presentation will make that visible — which is the point.

---

## What This Skill Does NOT Do

- **Generate theses.** That's Skill 7.
- **Run structural research.** That's Skill 11.
- **Compile the Monday Briefing.** That's Skill 9. This skill feeds Skill 9 with briefing cards.
- **Monitor thesis assumptions.** That's Skill 7's Function B. This skill reads the monitoring output and renders it.
- **Override analytical conclusions.** If the thesis says conviction is Medium, the presentation says Medium. No spin.

---

## Meta Block

```yaml
---
meta:
  skill: thesis-presentation
  skill_version: "1.0"
  run_date: "[ISO date]"
  theses_rendered: [number]
  tactical_reports: [number]
  structural_reports: [number]
  charts_generated: [number]
  briefing_cards: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
