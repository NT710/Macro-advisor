# Skill 6c: Empirical Sentiment (Analog Matching)

## Objective

Find historical periods with the most similar macro environment to the current state and compute forward risk/reward ratios per asset class. This provides an empirical check on the regime template allocations — the data may show patterns that qualitative reasoning would miss.

**Core principle:** Empirical evidence informs but does not override judgment. The regime label is the starting point, the data fills in the detail. Analog matching is one signal among several — it must never appear as the sole justification for a position.

## When This Runs

After Skill 6 (Weekly Macro Synthesis) completes. Consumes the regime scores from the synthesis-data.json sidecar.

## Inputs

1. **Current state vector** — `growth_score`, `inflation_score`, `liquidity_score` from the current week's `synthesis-data.json` (regime block).
2. **Historical FRED data** — pulled via `analog_matcher.py` (same series as `regime_backtest.py`).
3. **Historical weekly asset prices** — pulled via yfinance for the core ETF universe.

## Execution

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/analog_matcher.py \
  --fred-key "FRED_KEY_FROM_CONFIG" \
  --output-dir outputs/synthesis/ \
  --state-file outputs/synthesis/YYYY-Www-synthesis-data.json
```

The script:
1. Computes monthly state vectors (growth, inflation, liquidity scores) for all historical months
2. Finds the top 20 most similar periods using cosine similarity
3. Computes forward 4/12/26-week returns per asset in those analog periods
4. Expresses results as upside/downside risk/reward ratios
5. Flags surprising findings that contradict textbook expectations
6. Saves output to `outputs/synthesis/empirical-sentiment.json`

## Output Format

The script produces `empirical-sentiment.json` with this structure:

```json
{
  "current_state": {
    "growth_score": -0.28,
    "inflation_score": 0.42,
    "liquidity_score": -0.35
  },
  "analog_count": 20,
  "mean_similarity": 0.92,
  "analog_periods": [
    {"date": "2018-11", "similarity": 0.97},
    {"date": "2015-08", "similarity": 0.95}
  ],
  "signals": {
    "SPY": {
      "name": "S&P 500",
      "windows": {
        "4w": {
          "ratio": 0.8,
          "signal": "neutral",
          "mean_upside": 2.1,
          "mean_downside": -2.6,
          "hit_rate": 45.0,
          "n": 18,
          "mean": -0.3,
          "median": 0.1,
          "std": 3.2,
          "confidence": "medium",
          "forward_weeks": 4
        },
        "12w": { "..." : "..." },
        "26w": { "..." : "..." }
      }
    }
  },
  "surprises": [
    "Utilities (XLU) shows bullish at 12w despite falling growth"
  ],
  "forward_windows_weeks": [4, 12, 26],
  "methodology": {
    "method": "cosine_similarity",
    "dimensions": ["growth_score", "inflation_score", "liquidity_score"],
    "top_n": 20,
    "min_analogs": 10,
    "history_months": 180
  }
}
```

### Signal Interpretation

| Risk/Reward Ratio | Signal | Meaning |
|-------------------|--------|---------|
| ≥ 5.0 | strong_bullish | Upside ≥5x downside in analogs |
| 2.0 – 5.0 | bullish | Clear upside skew |
| 1.2 – 2.0 | slightly_bullish | Mild upside skew |
| 0.8 – 1.2 | neutral | Symmetric risk/reward |
| 0.5 – 0.8 | slightly_bearish | Mild downside skew |
| 0.2 – 0.5 | bearish | Clear downside skew |
| < 0.2 | strong_bearish | Downside ≥5x upside in analogs |

### Confidence Levels

| Analog Count | Confidence |
|-------------|------------|
| ≥ 20 | high |
| 10 – 19 | medium |
| 5 – 9 | low |
| < 5 | insufficient_data (signal not generated) |

## How Downstream Skills Use This

### Skill 9 (Monday Briefing)
Surface the most noteworthy findings in the narrative. If there are `surprises` (counter-intuitive signals), note them but do not invent post-hoc explanations. Example: "The analog matcher found 18 similar historical periods. Utilities showed strong upside in these analogs despite the growth-negative environment — this may be noise (n=18), or it may reflect structural shifts not captured by the regime model. Treat with caution."

Do NOT reproduce the full signal table in the briefing. Reference the overall pattern and highlight 1-2 surprising or high-conviction signals.

### Trading Engine T1 (Signal Parser)
Reads `empirical-sentiment.json` as a new signal source. Passes per-asset signals to T3 alongside regime template weights and thesis signals.

### Trading Engine T3 (Trade Reasoner)
References empirical risk/reward ratios as data input, NOT as sole positioning justification. The empirical signal should:
- Corroborate regime template allocations (increases conviction)
- Flag divergences (triggers deeper analysis)
- Surface non-obvious opportunities (like the utilities example)

**Hard rule:** An analog_matcher output must never appear as the sole justification for a position. It must be corroborated by at least one other concrete signal: regime template allocation direction, an active thesis with matching direction, or a specific data point from the macro synthesis. "Qualitative reasoning" alone does not count — the corroborating signal must be identifiable and named.

## Guardrails

1. **Minimum 10 analogs** before generating any signal. Below 10, the output flags `insufficient_data`.
2. **12-month exclusion window** for the most recent data (macro regimes persist 12-18 months; shorter exclusions risk same-episode contamination).
3. **Confidence intervals** — every signal includes sample size and confidence level.
4. **Surprise flagging** — counter-intuitive signals are explicitly flagged for human review.
5. **No mechanical execution** — signals feed reasoning, not order placement.

## Out-of-Sample Validation

Run periodically to verify the analog matcher adds value:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/analog_matcher.py \
  --fred-key "FRED_KEY_FROM_CONFIG" \
  --output-dir outputs/synthesis/ \
  --backtest --train-end 2019-12-31
```

This tests 2020-2025 using only pre-2020 data for analog matching. The output includes a directional hit rate — what percentage of bullish/bearish signals correctly predicted the direction of the actual forward return.

## Quality Standards

- Every signal must include the sample size (`n`). Signals with `n < 10` are flagged as low confidence.
- The `analog_periods` list provides full transparency — which historical months were used.
- The `methodology` block documents exactly how the matching was done.
- Surprising findings must be evaluated, not explained away. Some surprises are noise — label them as such. If a plausible mechanism exists (e.g., rate cut expectations), note it as a hypothesis, not a conclusion. If no mechanism is apparent, say "unexplained — likely noise" and reduce weight accordingly.

## What This Skill Does NOT Do

- Override the regime template allocations
- Determine position sizing (that's T3's job)
- Replace qualitative thesis reasoning
- Generate trade orders
- Modify risk limits or kill switches

## Meta Block

```yaml
---
meta:
  skill: empirical-sentiment
  skill_version: "1.0"
  run_date: "[ISO date]"
  state_vector:
    growth_score: [number]
    inflation_score: [number]
    liquidity_score: [number]
  analog_count: [number]
  mean_similarity: [number]
  surprises_count: [number]
  confidence: [high/medium/low/insufficient_data]
  notes: "[any issues]"
---
```
