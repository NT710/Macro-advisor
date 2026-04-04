# Skill T1: Signal Parser

## Objective

Read the macro advisor's outputs and translate them into a normalized set of trading signals. This skill is a translator — it does not make trading decisions. It converts the macro advisor's qualitative analysis into a structured format the position reconciler (T2) and trade reasoner (T3) can consume.

T1 is stateless. It reads the macro advisor outputs fresh every run. It does not reference prior parses, prior signals, or the current portfolio. It reports what the macro advisor says right now.

## Inputs

Read the macro advisor output path from `config/user-config.json` → `macro_advisor_outputs`. This is an absolute path resolved during setup. All paths below are relative to that directory.

1. **Latest weekly synthesis** — find the most recent file in `{macro_advisor_outputs}/synthesis/`. If the synthesis directory is empty, check the briefing for embedded regime assessment.
2. **Active theses** — all files in `{macro_advisor_outputs}/theses/active/`
3. **Latest data snapshot** — `{macro_advisor_outputs}/data/latest-snapshot.json`
4. **briefing-data.json (fallback)** — `{macro_advisor_outputs}/briefings/briefing-data.json` (if available). Used as a fallback source for cross-asset signals and thesis-level detail when synthesis-data.json sidecar does not cover this. See Step 2 below.
5. **Empirical sentiment (optional)** — `{macro_advisor_outputs}/synthesis/empirical-sentiment.json` (if available). Per-asset risk/reward ratios from analog matching. See Step 6 below.
6. **ETF reference** — look for `etf-reference.md` by checking these paths in order:
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

### Preferred source: synthesis-data.json

Before parsing the markdown synthesis, check for a structured JSON sidecar at `{macro_advisor_outputs}/synthesis/YYYY-Www-synthesis-data.json` (same week prefix as the synthesis markdown). If this file exists, use it as the primary data source for Steps 1, 1b, and parts of Step 2. The JSON sidecar contains pre-structured regime data, forecasts, driver readings, and narrative content — eliminating the need to parse markdown.

When the JSON sidecar is available:
- **Step 1 (Regime Signal):** Read directly from `sidecar.regime` (quadrant, confidence, direction, weeks_held).
- **Step 1b (Regime Forecast):** Read directly from `sidecar.forecasts` (regime, probability, score ranges, assumptions, triggers) and `sidecar.drivers` (growth/inflation/liquidity readings). The `sidecar.forecast_table` array contains the full forecast summary table.
- **Step 2 (Cross-Asset and Sector):** Still read from the briefing-data.json or synthesis markdown — the sidecar covers regime and forecasts, not thesis-level detail.

If the JSON sidecar does not exist (older synthesis from before this feature), fall back to markdown parsing as described below.

### Step 1: Regime Signal

From the weekly synthesis (or briefing, or synthesis-data.json sidecar), extract:

```json
{
  "regime": {
    "regime": "Stagflation — Tight Liquidity",
    "regime_family": "Stagflation",
    "liquidity_condition": "tight",
    "confidence": "High|Medium|Low",
    "direction": "Stable|Moving toward [quadrant]",
    "weeks_in_regime": 0,
    "regime_changed_this_week": false,
    "prior_regime": null,
    "growth_score": -0.28,
    "inflation_score": 0.42,
    "liquidity_score": -0.35
  }
}
```

Note: `regime_family` is used for template lookup (the 4 family-level templates in `regime-templates.json`). `liquidity_condition` drives the liquidity modifier overlay. Both `regime` (full 8-label) and `regime_family` are passed so T2 can apply the two-tier allocation (family template + liquidity modifier) and T3 has the full context for reasoning.

### Step 1b: Regime Forecast

From the weekly synthesis "Regime Forecast — 6 and 12 Months" section, extract the forward-looking regime view. This data is informational context for T3's reasoning — it does not feed into T2's target allocation.

The macro advisor's regime model is built on three underlying forces: **Growth**, **Inflation**, and **Liquidity**. The regime quadrant is an output of where these forces sit and where they're heading. The forecast extraction must capture both the regime label AND the underlying driver trajectories — the drivers are what make the forecast actionable for T3's position-level reasoning.

```json
{
  "regime_forecast": {
    "current_drivers": {
      "growth": {
        "score": -0.35,
        "direction": "decelerating",
        "key_data": ["LEI -1.3% 6-month", "CFNAI -0.01", "payrolls -92K", "unemployment 4.4% rising"]
      },
      "inflation": {
        "score": 0.52,
        "direction": "rising",
        "driver": "supply-side (oil shock)",
        "key_data": ["WTI $98.32 (+48% monthly)", "5Y breakeven 2.63%", "Michigan expectations 4.0%"]
      },
      "liquidity": {
        "state": "loose but tightening at margin",
        "direction": "transitioning to controlled tightening",
        "key_data": ["NFCI -0.4857 (96th pct loose)", "HY spreads 324bps widening from 306", "M2 4-week -0.81%"]
      }
    },
    "6_month": {
      "most_likely": {"regime": "quadrant name", "probability_pct": 50, "base_rate_pct": 40, "adjustment_rationale": "why the LLM deviated from base rate"},
      "secondary": {"regime": "quadrant name", "probability_pct": 35, "base_rate_pct": 25},
      "tail": {"regime": "quadrant name", "probability_pct": 15},
      "key_assumption": "one sentence — the central scenario that drives the base case",
      "confidence": "High|Medium-High|Medium|Low-Medium|Low",
      "conditional_triggers": [
        "specific event or data point that would shift probabilities — extract each 'What would change it' bullet"
      ],
      "driver_trajectories": {
        "growth": "where growth is heading and why — extract from synthesis Growth Picture and forecast assumptions",
        "inflation": "where inflation is heading and why — extract the primary driver (demand-pull vs supply-push) and what resolves or sustains it",
        "liquidity": "where liquidity is heading — Fed policy path, credit conditions trajectory, balance sheet direction"
      }
    },
    "12_month": {
      "most_likely": {"regime": "quadrant name", "probability_pct": 40, "base_rate_pct": 35, "adjustment_rationale": "why the LLM deviated from base rate"},
      "secondary": {"regime": "quadrant name", "probability_pct": 35, "base_rate_pct": 30},
      "tail": {"regime": "quadrant name", "probability_pct": 25},
      "key_assumption": "one sentence",
      "confidence": "High|Medium-High|Medium|Low-Medium|Low",
      "conditional_triggers": [],
      "driver_trajectories": {
        "growth": "12-month growth path",
        "inflation": "12-month inflation path",
        "liquidity": "12-month liquidity path"
      }
    }
  }
}
```

Parsing rules:
- **Current drivers:** Extract the growth score and inflation score from the "Regime coordinates" section of the synthesis. Extract direction and key data points from the Growth Picture, the inflation discussion in the Regime Assessment, and the Liquidity Picture. These are the starting point — T3 needs to know where the forces are *now* to understand where they're *going*.
- **Driver trajectories:** For each horizon, extract the synthesis's view on where each force is heading. The growth trajectory comes from the forecast's key assumption and the Growth Picture's forward signals. The inflation trajectory comes from the forecast's oil/energy assumptions and the inflation data trend. The liquidity trajectory comes from the Policy Picture's Fed path and the Liquidity Picture's credit conditions trend. Write these as concise narrative sentences, not data dumps.
- **Current driver data:** Extract 3-5 of the most regime-relevant data points for each force. Prefer hard data (FRED series, official releases) over sentiment indicators. These give T3 specific numbers to reference in reasoning.
- Extract probability percentages as integers. If the synthesis gives a range (e.g., "25-30%"), use the midpoint.
- **Base rate extraction:** If the synthesis sidecar includes `base_rate_probability` in the forecast objects, extract it as `base_rate_pct` (multiply by 100, round to integer). Also extract `adjustment_rationale`. These tell T3 how much the LLM deviated from historical base rates and why. If `base_rate_probability` is null or absent, set `base_rate_pct` to null. A large deviation (>20pp) with weak rationale is a signal for T3 to discount the forecast's confidence.
- The `conditional_triggers` array should contain every specific scenario the synthesis identifies as capable of shifting the probability distribution. These are critical — they tell T3 what data to watch for regime transition signals.
- If the synthesis does not contain a regime forecast section (older format or missing), set `regime_forecast` to `null` and note this in the `conflicts` array. Do not fabricate forecasts.

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

### Step 6: Empirical Sentiment (Optional)

Check for `{macro_advisor_outputs}/synthesis/empirical-sentiment.json`. If available, extract the per-asset risk/reward ratios as an additional signal source:

```json
{
  "empirical_sentiment": {
    "available": true,
    "analog_count": 20,
    "mean_similarity": 0.92,
    "signals": {
      "SPY": {
        "4w": {"ratio": 0.8, "signal": "neutral", "confidence": "medium"},
        "12w": {"ratio": 1.5, "signal": "slightly_bullish", "confidence": "medium"},
        "26w": {"ratio": 2.1, "signal": "bullish", "confidence": "high"}
      }
    },
    "surprises": ["Utilities (XLU) shows bullish at 12w despite falling growth"]
  }
}
```

Parsing rules:
- If the file does not exist, set `"empirical_sentiment": {"available": false}` and continue. This signal is optional.
- Pass through the per-asset signals with their confidence levels. T3 will decide how to weight them.
- Pass through the `surprises` array — these are counter-intuitive findings that T3 should consider.
- **Hard rule:** Empirical sentiment must never be the sole justification for a position. It must be corroborated by at least one other signal (regime template, thesis, or qualitative reasoning).

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
  "regime_forecast": { ... },
  "asset_signals": [ ... ],
  "sector_signals": [ ... ],
  "thesis_signals": [ ... ],
  "empirical_sentiment": { ... },
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
  regime_forecast_extracted: [true/false]
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
