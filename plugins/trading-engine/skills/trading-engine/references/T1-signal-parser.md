# Skill T1: Signal Parser

## Objective

Read the macro advisor's outputs and translate them into a normalized set of trading signals. This skill is a translator — it does not make trading decisions. It converts the macro advisor's qualitative analysis into a structured format the position reconciler (T2) and trade reasoner (T3) can consume.

T1 is stateless. It reads the macro advisor outputs fresh every run. It does not reference prior parses, prior signals, or the current portfolio. It reports what the macro advisor says right now.

## Inputs

Read the macro advisor output path from `config/user-config.json` → `macro_advisor_outputs`. This is an absolute path resolved during setup. All paths below are relative to that directory.

1. **Latest weekly synthesis** — find the most recent file in `{macro_advisor_outputs}/synthesis/`. If the synthesis directory is empty, check the briefing for embedded regime assessment.
2. **Active theses** — all files in `{macro_advisor_outputs}/theses/active/`
3. **Latest data snapshot** — `{macro_advisor_outputs}/data/latest-snapshot.json`
4. **ETF reference** — look for `etf-reference.md` by checking these paths in order:
   - `{macro_advisor_outputs}/../skills/macro-advisor/references/etf-reference.md` (standard plugin layout — outputs/ is a sibling of skills/)
   - `{macro_advisor_outputs}/../../skills/macro-advisor/references/etf-reference.md` (if outputs path goes one level deeper)
   - If neither exists, log a warning: "ETF reference not found — ticker mapping will use macro advisor synthesis text only. Currency-specific ETF mapping may be incomplete."

Also check `{macro_advisor_outputs}/briefings/` for the latest dashboard HTML if synthesis files are not available — the briefing contains the regime assessment embedded in the HTML.

If the most recent macro advisor output is older than 7 days from today, flag "STALE SIGNALS" and produce no trade signals. The trading engine should not act on stale analysis.

## Freshness Check

Before parsing anything, verify the macro advisor ran recently:

```
Most recent synthesis/briefing date: [date]
Days since last run: [N]
Status: FRESH (<=7 days) / STALE (>7 days)
```

If STALE, stop here and output an empty signal set with the staleness warning.

## Extraction Process

### Step 1: Regime Signal

From the weekly synthesis (or briefing), extract:

```json
{
  "regime": {
    "quadrant": "Goldilocks|Overheating|Disinflationary Slowdown|Stagflation",
    "confidence": "High|Medium|Low",
    "direction": "Stable|Moving toward [quadrant]",
    "weeks_in_regime": 0,
    "regime_changed_this_week": false,
    "prior_regime": null
  }
}
```

### Step 2: Asset Allocation Signals

From the synthesis cross-asset implications table, extract each row:

```json
{
  "asset_signals": [
    {
      "asset_class": "US Equities",
      "stance": "Bull|Neutral|Bear",
      "etf_expression": "SPY",
      "rationale": "one sentence from synthesis"
    }
  ]
}
```

Map the stance to a target weight using the regime template from `${CLAUDE_PLUGIN_ROOT}/config/regime-templates.json`. The template provides baseline weights; the synthesis stance adjusts them (Bull = template weight * 1.2, Neutral = template weight, Bear = template weight * 0.5, or 0 if avoiding).

### Step 3: Sector Signals

From the synthesis sector view:

```json
{
  "sector_signals": [
    {
      "sector": "Technology",
      "direction": "favor|neutral|avoid",
      "timing": "tactical|structural",
      "rationale": "from synthesis"
    }
  ]
}
```

### Step 4: Thesis Signals

For each file in the active theses directory, extract:

```json
{
  "thesis_signals": [
    {
      "thesis_name": "from filename",
      "status": "DRAFT|ACTIVE|STRENGTHENING|WEAKENING",
      "classification": "tactical|structural",
      "mechanism_type": "divergence|regime_shift|positioning_extreme|policy_shift|cross_market_dislocation|structural_constraint|other",
      "etf_expressions": {
        "first_order": [{"etf": "XLE", "name": "Energy Select Sector SPDR", "sizing": "medium 3-5%", "rationale": "..."}],
        "second_order": [{"etf": "XOP", "name": "SPDR S&P Oil & Gas Exploration & Production", "sizing": "small 1-3%", "rationale": "..."}],
        "third_order": [{"etf": "OIH", "name": "VanEck Oil Services ETF", "sizing": "small 1-2%", "rationale": "..."}],
        "reduce_avoid": [{"etf": "QQQ", "name": "Invesco QQQ Trust (Nasdaq-100)"}]
      },
      "kill_switch": "specific condition from thesis",
      "kill_switch_status": "NOT_TRIGGERED|NEAR|TRIGGERED",
      "assumptions_status": {
        "all_intact": true,
        "under_pressure": [],
        "broken": []
      },
      "time_horizon": "from thesis",
      "weeks_active": 0
    }
  ]
}
```

Important parsing rules:
- **DRAFT theses get zero trade signals.** Parse them for awareness but mark `tradeable: false`.
- **ACTIVE and STRENGTHENING theses are tradeable.** STRENGTHENING gets higher conviction.
- **WEAKENING theses:** tradeable but at reduced sizing (halve the stated range).
- **INVALIDATED theses:** these should be in the closed directory, but if found in active, flag immediately for kill-switch exit.

### Step 5: Kill Switch Scan

Cross-reference each active thesis's kill switch conditions against the latest data snapshot. For each thesis, assess:

- Is the kill switch condition met? (check specific data points)
- How close is it to triggering? (express as proximity: FAR / APPROACHING / NEAR / TRIGGERED)

This is the most important step. A missed kill switch trigger means the trading engine holds a position it should have exited.

## Output Format

Produce a single JSON file: `outputs/portfolio/latest-signals.json`

```json
{
  "parsed_at": "ISO timestamp",
  "source_freshness": {
    "synthesis_date": "date",
    "days_since_run": 0,
    "status": "FRESH|STALE"
  },
  "regime": { ... },
  "asset_signals": [ ... ],
  "sector_signals": [ ... ],
  "thesis_signals": [ ... ],
  "kill_switch_alerts": [
    {
      "thesis": "name",
      "condition": "what the kill switch says",
      "current_data": "what the data shows",
      "proximity": "FAR|APPROACHING|NEAR|TRIGGERED",
      "action_required": "none|monitor|EXIT_IMMEDIATELY"
    }
  ],
  "conflicts": [
    "list any conflicts between regime signals and thesis signals"
  ]
}
```

## Quality Standards

- Every signal must trace back to a specific macro advisor output. No invented signals.
- If a field in the macro advisor output is ambiguous, extract what you can and note the ambiguity in the `conflicts` array.
- If a thesis file cannot be parsed (corrupted, missing fields), log the error and skip that thesis. Don't halt the entire run.
- The kill switch scan is non-optional. Every active thesis must be scanned.

## Meta Block

```yaml
---
meta:
  skill: signal-parser
  skill_version: "1.0"
  run_date: "[ISO date]"
  source_freshness_days: [number]
  regime_extracted: [true/false]
  thesis_count: [number]
  thesis_tradeable: [number]
  kill_switch_alerts: [number]
  conflicts: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
