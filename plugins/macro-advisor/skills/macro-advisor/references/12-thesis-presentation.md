# Skill 12: Thesis Presentation

## Objective

Generate thesis-specific charts and briefing cards. The dashboard renders thesis content directly from the raw Skill 7 thesis files — Skill 12 does NOT rewrite, restructure, or summarize thesis content. The dashboard's `generate_dashboard.py` handles all formatting (tables, highlighted cards, etc.) automatically.

Skill 12 produces two things:
1. **Chart JSON specs** — data-resolved Chart.js configurations for each thesis
2. **Briefing cards** — compressed summaries consumed by Skill 9 for the Monday Briefing

---

## When to Invoke

1. **During the weekly chain.** After Skill 7 completes monitoring, Skill 12 generates charts and briefing cards before Skill 9 compiles the briefing.
2. **After `/investigate-theme` or `/structural-scan` creates a new thesis.** New theses need chart specs.

Chain position: runs after Skill 7 (and Skill 11 if triggered), before Skill 9.

---

## Inputs

- **All thesis files from `outputs/theses/active/`** (ACTIVE- or DRAFT- prefixed) — list the directory and process every file found. Theses may have been created outside the weekly chain (via `/investigate-theme` or `/structural-scan`), so do not rely on Skill 7's output as the thesis list. The directory listing is the authoritative set.
- Data snapshot from `outputs/data/latest-snapshot.json` — for chart generation
- Full data file from `outputs/data/latest-data-full.json` — for time series charts
- For structural theses: the corresponding Skill 11 research brief from `outputs/research/`

---

## What Skill 12 Does NOT Do

- **Rewrite thesis content.** The dashboard renders raw thesis files directly via `md_to_html` with section-aware formatting. Skill 12 must not produce alternative versions of thesis content.
- **Generate theses.** That's Skill 7.
- **Run structural research.** That's Skill 11.
- **Compile the Monday Briefing.** That's Skill 9. This skill feeds Skill 9 with briefing cards.
- **Override analytical conclusions.** If the thesis says conviction is Medium, the briefing card says Medium.

---

## Output 1: Chart JSON Specs

Generate thesis-specific charts using the system's data. Charts are embedded directly in the HTML dashboard (via Chart.js in `generate_dashboard.py`) rather than as separate image files.

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

For each thesis that gets a chart, produce a JSON block that `generate_dashboard.py` can consume. **The chart spec must be self-contained** — the dashboard generator is a dumb renderer that plots whatever data it receives. It does not resolve references or look up data series.

**CRITICAL: Resolve all data series into actual `{x, y}` arrays before writing the chart spec.** The `data` field in each dataset must contain an array of `{x: "YYYY-MM-DD", y: number}` objects — NOT a reference string like `"snapshot.markets.oil_wti"` or `"data_series"`. If you write a reference string instead of resolved data, the chart canvas will render empty and the presentation is broken.

**How to resolve data — follow this exact process:**

1. Read `outputs/data/latest-data-full.json`
2. Navigate to the series: FRED data is at `fred.data.[SERIES_ID].history`, Yahoo data is at `yahoo.data.[TICKER].history`
3. Each history entry is `{"date": "YYYY-MM-DD", "value": number}`
4. Map to chart format: `{"x": entry.date, "y": entry.value}`

**Concrete example — resolving 10Y yield for a rate thesis:**
```
# In latest-data-full.json:
fred.data.DGS10.history = [{"date": "2026-01-05", "value": 4.17}, {"date": "2026-01-12", "value": 4.22}, ...]

# In chart JSON you write:
"data": [{"x": "2026-01-05", "y": 4.17}, {"x": "2026-01-12", "y": 4.22}, ...]
```

**Common mistake:** Writing `"data": "fred.data.DGS10.history"` or `"data": "data_series"` — this is WRONG. The dashboard renderer is a dumb plotter. It does not resolve references. You must put the actual numbers in the array.

**If the series is not found** in the data file, write `"data": []` and add an annotation: `{"type": "note", "label": "Data series [name] not available in snapshot"}`.

```json
{
  "thesis_name": "string",
  "chart_type": "line",
  "title": "string",
  "datasets": [
    {
      "label": "WTI Crude Oil",
      "data": [
        {"x": "2025-09-15", "y": 72.3},
        {"x": "2025-09-22", "y": 74.1},
        {"x": "2025-09-29", "y": 76.8}
      ],
      "color": "#f87171",
      "source": "markets.oil_wti"
    }
  ],
  "annotations": [
    {
      "type": "line",
      "value": "2026-01-15",
      "label": "Thesis generated"
    }
  ]
}
```

The `source` field is metadata for provenance — it records which data series was used, but the `data` array is what gets plotted.

Save chart specifications as **separate JSON files**: `outputs/theses/presentations/[thesis-name]-charts.json`. The dashboard generator reads these files to render the charts as interactive Chart.js canvases.

### Pre-Output Checklist (charts)

Before writing each chart JSON, verify:

1. **Chart data resolved?** Does every `data` array contain actual `{x, y}` objects with real numbers? If any `data` field contains a string, STOP and resolve it from `latest-data-full.json`.
2. **Chart relevant?** Does the chart directly support the thesis mechanism? No decorative charts.
3. **One chart per thesis.** One well-chosen chart beats three tangential ones.

---

## Output 2: Briefing Cards

A compressed summary that Skill 9 consumes as input data. Skill 9 weaves thesis references into its narrative prose — these cards are NOT rendered as a table in the memo. The format below gives Skill 9 the structured facts it needs to reference each thesis naturally in the briefing narrative.

```markdown
### [Thesis Name] [TACTICAL/STRUCTURAL badge]
**Status:** [emoji + status] | **Conviction:** [H/M/L] | **Weeks Active:** [N]
[One sentence: what's the bet, in plain English.]
**This week:** [One sentence: what changed, what to do.]
**Key risk:** [One sentence: the kill switch or nearest risk, in plain English.]
```

Briefing cards are embedded directly in the Skill 9 briefing output (not separate files).

**Rules for briefing cards:**
- Content comes from the thesis file. Do not invent or editorialize.
- "This week" reflects Skill 7 Function B's monitoring output — what changed in the data, not a generic restatement of the thesis.
- If nothing changed this week, say "No material change this week. Monitoring continues."

---

## Output Files

- **Chart specs:** `outputs/theses/presentations/[thesis-name]-charts.json`
- **Briefing cards:** Embedded in Skill 9's briefing (not separate files)

Note: Skill 12 no longer produces `-report.md` files. The dashboard renders thesis files directly from `outputs/theses/active/`.

---

## Meta Block

```yaml
---
meta:
  skill: thesis-presentation
  skill_version: "2.0"
  run_date: "[ISO date]"
  charts_generated: [number]
  briefing_cards: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
