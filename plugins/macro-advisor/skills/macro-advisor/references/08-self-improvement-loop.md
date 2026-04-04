# Skill 8: Self-Improvement Loop

## Objective

Review the meta blocks from all skill outputs produced in the current weekly run. Identify systematic patterns in data gaps, quality degradation, and search effectiveness. Propose specific, targeted amendments to skill instructions. This runs at the end of every weekly chain, not monthly.

## Core Framework: Observe → Inspect → Amend → Evaluate

Based on the cognee self-improving skills architecture. Skills are living system components, not static prompt files. The environment around them (data sources, search result quality, market information availability) changes constantly. Without structured observation, skill degradation is invisible until the output becomes useless.

## Inputs

Read ALL of the following:

**Amendment tracker (read first):**
`outputs/improvement/amendment-tracker.md` — persistent record of all proposed amendments, their implementation status, and evaluation results. Check this before proposing new amendments to avoid re-proposing ones already implemented. When evaluating, update this file with results.

**Accuracy tracker (read for cumulative scoring):**
`outputs/improvement/accuracy-tracker.md` — persistent record of all weekly analytical calls and their outcomes. Each week, append a new scorecard row for the prior week. Compute cumulative accuracy rates from the full file. This is what tells the user — and us — where the system adds value and where it doesn't.

**Meta blocks from all skill outputs produced in the current run:**
1. Central Bank Watch meta
2. Liquidity & Credit Monitor meta
3. Macro Data Tracker meta
4. Geopolitical & Policy Scanner meta
5. Market Positioning & Sentiment meta
6. Weekly Synthesis meta
7. Thesis Monitor meta
8. Structural Scanner meta (bi-weekly — read from `outputs/structural/YYYY-Www-structural-scan.md` if it ran this cycle)
9. Structural Scanner last-run tracker (`outputs/structural/last-scan.json` — always read, even on weeks the scanner didn't run)
10. Regime Evaluator output (`outputs/synthesis/YYYY-Www-regime-evaluation.md`) and evaluation history (`outputs/synthesis/regime-evaluation-history.json`)
11. Empirical Sentiment output (`outputs/synthesis/empirical-sentiment.json`) — analog count, mean similarity, surprises, per-asset signal confidence
12. Trading engine improvement output (if available, from prior week) — for cross-checking empirical sentiment hard rule compliance in section 2g-v. This runs on a separate schedule so may be one week behind.

Also read the prior improvement loop output (if it exists) for trend context and to check whether previous amendments were effective.

---

## Step 1: OBSERVE — Extract Structured Metrics

From each skill's meta block, extract and compile:

```markdown
### Observation Summary — [Date]

| Skill | Self Score | Confidence | Data Points Found/Expected | Gaps Count | Freshest Source | Oldest Source |
|-------|-----------|-----------|---------------------------|-----------|----------------|--------------|
| Central Bank Watch | [score] | [conf] | [n/n] | [n] | [date] | [date] |
| Liquidity & Credit | [score] | [conf] | [n/n] | [n] | [date] | [date] |
| Macro Data Tracker | [score] | [conf] | [n/n] | [n] | [date] | [date] |
| Geopolitical | [score] | [conf] | [n/n] | [n] | [date] | [date] |
| Positioning | [score] | [conf] | [n/n] | [n] | [date] | [date] |
| Synthesis | [score] | [conf] | [inputs: n/5] | — | — | — |
| Thesis Monitor | [score] | [conf] | — | — | — | — |
| Structural Scanner | [score or "skipped"] | [conf] | [signals: n/6] | [n] | [date] | [date] |
| Regime Evaluator | [score] | [conf] | blind_diverged: [Y/N] | verdict: [P/R/C] | streak: [N] | — |
| Empirical Sentiment | [score] | [conf] | analogs: [N], mean_sim: [X] | surprises: [N] | — | — |
```

Also compile the complete list of gaps across all skills:
```markdown
### Data Gaps Inventory
| Skill | Gap Description | Consecutive Weeks Missing | Severity |
|-------|----------------|--------------------------|----------|
| [skill] | [what couldn't be found] | [n — count from improvement history] | [high/medium/low] |
```

Severity classification:
- **High:** Core methodology variable (M2, credit spreads, NFCI, COT data, central bank decisions)
- **Medium:** Supporting variable that enriches analysis but isn't regime-defining
- **Low:** Nice-to-have context that doesn't change the regime assessment

---

## Step 2: INSPECT — Pattern Detection

Analyze the observation data for systematic patterns. Check for:

### 2a. Persistent Data Gaps
Which data points are consistently missing? A gap that appears 3+ consecutive weeks is a systematic problem, not bad luck. The search strategy for that data point needs to change.

### 2b. Quality Trends
Compare self_scores against prior weeks (read from improvement history). Are any skills trending downward? A skill going from 0.8 → 0.7 → 0.6 over three weeks is degrading.

### 2c. Source Freshness Decay
Are oldest_source_used dates getting further from the run_date? This indicates search queries are surfacing stale content instead of current data.

### 2d. Synthesis Input Completeness
How often is the synthesis running on fewer than 5 inputs? Which collection skills are the most frequent failure points?

### 2e. Search Effectiveness
Calculate the ratio: searches_with_useful_results / searches_attempted. If this ratio is below 0.5 for any skill, the search strategy is broken.

### 2f. Thesis Quality
Are thesis candidates specific enough? Do they have measurable kill switches? Are active theses being monitored with actual data references, or are the monitoring notes vague?

Additionally, check these two specific quality metrics across all active theses:

- **Testable criteria coverage:** What percentage of "What Has To Stay True" assumptions across all active theses include a "Testable by:" clause? Target: 100%. If below 80%, flag as a data quality gap — Skill 7 Function A is generating assumptions without testable criteria, or legacy theses have not been backfilled by Function B.
- **Status assessment coverage:** What percentage of assumptions across all active theses have a current status assessment (INTACT / UNDER PRESSURE / BROKEN) written back to the thesis file? Target: 100% for theses that have been through at least one monitoring cycle. If any thesis has assumptions without status after being monitored, Skill 7 Function B is not writing back its monitoring results — flag as a process gap and propose an amendment.

### 2g. Reasoning Quality (Cross-Skill Information Flow)
This is not about data collection — it's about whether the system is connecting information across skills. Check:

1. **Did the thesis monitor (Skill 7) cross-reference the analyst monitor (Skill 10)?** If the analyst monitor surfaced a framework or data point directly relevant to an active thesis, did Skill 7 flag it? If not, that's a missed connection.

2. **Did the synthesis (Skill 6) incorporate all collection skill findings?** Not just "read them all" but actually used them. If one collection skill found something important that doesn't appear in the synthesis, that's a reasoning gap.

3. **Were there insights in one skill that should have changed conclusions in another?** For example: if the geopolitical scanner found escalation evidence, did the thesis monitor assess its impact on theses that assume de-escalation? If the macro data showed labor deterioration, did the liquidity skill consider the credit implications?

4. **Are thesis kill switches and assumptions calibrated against the best available data?** If better data emerged from any skill this week (e.g., analyst monitor finding a more rigorous threshold metric than the one in the thesis), was that flagged?

For each missed connection found, produce a reasoning quality note:
```
REASONING GAP: [description]
Skill A found: [what]
Skill B should have used it for: [what]
Impact: [what conclusion would have changed]
```

### 2g-ii. Structural Scanner Health (from Skill 13 meta + last-scan.json)

Read `outputs/structural/last-scan.json` every week, even if the scanner didn't run this cycle. Check:

1. **Emptiness ratio:** `signals_with_no_finding / total_signals_checked`. A healthy ratio is 2-5 findings out of 7 detectors (includes technology displacement as Signal 7). If the scanner consistently finds tension in all 7 signals (emptiness = 0), the detection thresholds are too loose — propose an amendment to tighten them. If it consistently finds 0-1 findings, thresholds may be too tight or the data sources may be stale.

2. **Kill rate:** `historical_kill_rate.survived_skill_11 / total_candidates_generated`. A healthy kill rate is 40-60%. If >80% of scanner candidates survive Skill 11 research, the scanner's bar is too low — it's advancing weak candidates. If <20% survive, the scanner is generating noise. Either way, flag for threshold review.

3. **Provenance ratio (expanded):** Track three provenance categories in the thesis portfolio: `data-pattern`, `analyst-sourced`, and `structural-scanner`. No single category should dominate (>60% of active theses). If scanner-sourced theses dominate, the system is over-weighting structural findings relative to cyclical signals. If scanner-sourced theses are 0% after 4+ scanner runs that produced candidates, the pipeline is broken — candidates are being generated but not making it through Skill 11 → Skill 7.

4. **Domain recurrence:** Check `last-scan.json` for domains flagged 3+ consecutive cycles. If the quantified gap is not growing, the scanner may be stuck on a narrative rather than tracking a worsening imbalance. Flag for review.

5. **Sector clustering:** If the scanner's findings cluster in one area for 3+ consecutive runs (e.g., all energy, all commodities), flag as potential signal-set bias. Do not force diversification — but note the clustering.

### 2g-iii. Decade Horizon Health (from Skill 14 meta + last-horizon.json)

Read `outputs/strategic/last-horizon.json` if it exists. This is a quarterly check — most weeks this data is unchanged. Check:

1. **Force stability:** How many mega-forces changed between the last two quarterly runs? If >1 force changes per quarter (added/removed/fundamentally revised), the selection criteria may be too loose. Mega-forces should persist for years.

2. **Blind spot conversion rate:** `historical_conversion.became_active_theses / total_blind_spots_flagged`. A healthy rate is 20-40% over 4 quarters when blind spots are flagged. If blind spots never convert, the horizon map may be too abstract. If they all convert, it's duplicating the scanner. Note: zero blind spots in a given quarter is valid — it means thesis book coverage is adequate. Flag for review only if the skill reports zero blind spots for 3+ consecutive quarters, which may indicate the coverage comparison is too loose.

3. **Consensus vs. novel ratio:** What percentage of identified blind spots were second/third-order impacts vs. first-order consensus views? Target >50% novel. If the horizon map is dominated by consensus first-order impacts, it's not adding value beyond what the market already prices.

4. **Horizon-scanner alignment:** When both Skill 14 and Skill 13 run, do the horizon's blind spots align with scanner findings? Convergence suggests the system is internally consistent. Divergence isn't necessarily bad — the two skills look at different things — but persistent total divergence may indicate one layer is miscalibrated.

### 2g-iv. Regime Evaluator Health (from Skill 6b output + evaluation history)

Read `outputs/synthesis/YYYY-Www-regime-evaluation.md` and `outputs/synthesis/regime-evaluation-history.json`. Check:

1. **Divergence frequency:** Over the last 8 weeks, how often did the blind classification disagree with Skill 6? A healthy rate is 20-40%. If divergence is 0% over 8+ weeks, the evaluator may be too agreeable — check whether it's anchoring on data that naturally confirms the regime rather than stress-testing. If divergence is >60%, either the evaluator's classification logic is miscalibrated or Skill 6's confirmation filter is holding a stale regime.

2. **Divergence-to-change lead time:** When a regime DID change (in Skill 6), how many weeks in advance did Skill 6b's blind classification start diverging? Track this as "early warning lead time." A healthy lead time is 3-6 weeks before the official change. If the evaluator diverges at the same time as Skill 6 changes (lead time = 0), it's not adding value — it's a redundant check. If lead time is consistently >8 weeks, the evaluator may be too trigger-happy and the signal gets diluted by false alarms.

3. **CHALLENGE verdict accuracy (transition-aware):** When CHALLENGE was issued, did Skill 6 eventually change its regime call within the next 4 weeks? Track hit rate. But distinguish between two contexts:
   - **CHALLENGE during regime stability** (Skill 6 did NOT change regime in the surrounding 8-week window): A healthy false-alarm rate is 30-50%. Some false CHALLENGEs are expected — the evaluator should be skeptical. If false-alarm rate is >70% during stable periods, the evaluator is generating noise.
   - **CHALLENGE during regime transitions** (Skill 6 DID change regime within 4 weeks): This is the evaluator doing its job. Track whether CHALLENGE preceded the change (early warning = good) or followed it (redundant = not useful).

   Do NOT blend these two contexts into a single accuracy number. A CHALLENGE that fires during a genuine transition is categorically different from one that fires during stability.

4. **Reasoning audit hit rate:** What percentage of Skill 6b's flagged reasoning gaps were confirmed by Skill 8's accuracy scorecard? If Skill 6b flags "claim X is unsupported" and the next week's scorecard shows the corresponding call was WRONG, that's a confirmed hit. Track over time.

5. **CHALLENGE frequency check:** If CHALLENGE fires >25% of the time over a 12-week window AND none of those CHALLENGEs preceded a regime change, the evaluator's thresholds are too loose. Propose an amendment to tighten the CHALLENGE criteria. But if >25% of CHALLENGEs occurred during a period that included a regime transition, that's expected behavior — do not flag it.

For each issue found, produce a note:
```
EVALUATOR HEALTH: [description]
Metric: [which metric]
Value: [current value]
Healthy range: [expected range]
Context: [during stability / during transition]
Implication: [what to do about it]
```

### 2g-v. Empirical Sentiment Health (from Skill 6c output)

Read `outputs/synthesis/empirical-sentiment.json` if it exists. Also read `outputs/synthesis/analog-backtest-results.json` if it exists — this is auto-generated every 90 days by the analog matcher during normal weekly runs.

**Model version tracking:** Check `current_state.dimensionality` in the sentiment output and `state_vector_dimensions` in the backtest results. The system upgraded from 3D (composite growth/inflation/liquidity scores) to 11D (individual features + HY OAS + yield curve) in April 2026. Compare backtest results across model versions to verify the 11D upgrade added value.

**Acceptance gate for 11D:** The 11D model must show 3+ percentage point improvement in `excess_accuracy_vs_naive` over the prior 3D baseline. If backtest results show `excess_accuracy_vs_naive` is still negative or within 3pp of the old baseline, flag for reversion to 3D.

1. **Prediction asymmetry:** Check `bullish_prediction_pct` across equity tickers. If the model predicts "bullish" >80% of the time for equities, the signal is just restating the equity risk premium — not adding information. Flag as a bias concern.

2. **Naive baseline comparison:** Read `excess_accuracy_vs_naive` from the latest backtest results. If negative (model worse than always predicting the majority direction), the signal is net-negative and should be downweighted or suspended. Track this value across backtest runs to detect trend.

3. **Confidence inflation:** Check whether signals labeled "high confidence" (n ≥ 20) perform differently from "medium confidence" (n ≥ 10). If there is no difference, the confidence label is misleading and should be flagged for recalibration.

4. **Hard rule compliance (cross-check with T7):** When reading the trading engine's improvement output, check whether any T3 reasoning logs cite empirical sentiment as the primary driver of a position. The hard rule says it must be corroborated by a named concrete signal. If compliance is unclear, flag for human review.

5. **Surprise signal noise rate:** Track what percentage of flagged "surprises" from the analog matcher were later evaluated as noise vs. genuine structural patterns. If >80% of surprises are noise after 8+ weeks of tracking, propose tightening the surprise detection criteria or removing the surprise feature entirely.

6. **Backtest freshness:** Check the modification date of `analog-backtest-results.json`. If older than 90 days and the weekly run did not auto-refresh it, flag as stale validation. The auto-validation should have triggered — investigate why it didn't.

For each issue found:
```
EMPIRICAL SENTIMENT HEALTH: [description]
Metric: [which metric]
Value: [current value]
Concern: [what's wrong]
Recommendation: [downweight / suspend / recalibrate / keep monitoring]
```

### 2h. Analytical Accuracy (Prior Week Scorecard)

Read last week's briefing and synthesis from `outputs/briefings/` and `outputs/synthesis/`. Compare what we said against what actually happened this week. This is the most important quality metric over time — not whether we collected the data, but whether our conclusions were right.

Check:

1. **Regime call accuracy:** What regime did we call last week? Does this week's data confirm or contradict it? If we said "Overheating moving toward Stagflation" and this week's data shows growth accelerating and inflation falling, the call was wrong.

2. **Asset/sector tilt accuracy:** What did we favor and avoid? Did those tilts perform directionally as expected? Use the data snapshot price changes (week_change_pct) to check.

3. **"What to Watch" accuracy:** What events did we flag as important? Did they happen? Did they matter? What did we miss that turned out to be the week's biggest story?

4. **Thesis prediction accuracy:** For each active thesis, did the assumptions hold? Did the mechanism play out as described? Track a running hit rate over time.

5. **Signal vs. Noise accuracy:** What we called noise — did it stay noise? What we called signal — did it matter?

For each call, score as: CORRECT / PARTIALLY CORRECT / WRONG / TOO EARLY TO TELL

```
SCORECARD: [Week]
Regime call: [what we said] → [what happened] → [CORRECT/WRONG/PARTIAL]
Key tilt: [what we favored] → [actual performance] → [CORRECT/WRONG/PARTIAL]
Key watch: [event we flagged] → [what happened] → [CORRECT/WRONG/PARTIAL]
Biggest miss: [what we didn't see coming]
```

**After scoring, update the accuracy tracker** (`outputs/improvement/accuracy-tracker.md`):
- Append the scorecard row for this week
- Recompute the cumulative accuracy rates from the full file (all rows, not just this week)
- Update the cumulative table

Over time (4+ weeks), the cumulative rates reveal where the system adds value and where it doesn't. This is the most important output of the improvement loop — it tells the user how much to trust each section of the briefing.

### 2i. LLM Forecast Alpha (Base Rate Comparison)

This section measures whether the LLM's probability adjustments improve or degrade forecasting accuracy compared to raw empirical base rates. It is the system's first falsifiable feedback loop for regime forecasts.

**When to evaluate:** Check each prior synthesis sidecar (`synthesis-data.json`) for the `forecasts` array. For each forecast where `base_rate_probability` is not null AND the horizon has elapsed (e.g., a 6-month forecast from 6+ months ago), score it:

1. Read `regime-history.json` to determine what regime actually occurred at the target date.
2. Compute **Brier score** for both the base rate distribution and the LLM-adjusted distribution:
   - Brier score = sum over all regimes of (probability - actual)^2, where actual = 1 for the regime that occurred, 0 for all others
   - Lower Brier score = better calibration
3. Track per resolved forecast:
   - `base_rate_brier`: Brier score using `base_rate_probability` values
   - `adjusted_brier`: Brier score using `probability` values (the LLM-adjusted ones)
   - `alpha`: base_rate_brier minus adjusted_brier. Positive = LLM adjustments improved the forecast.
   - `adjustment_magnitude`: average of |probability - base_rate_probability| across target regimes

**Cumulative tracking** (append to accuracy tracker):

```
FORECAST ALPHA (cumulative, N resolved forecasts):
  Mean base rate Brier:   [score]
  Mean adjusted Brier:    [score]
  Mean alpha:             [+/- score]  (positive = LLM adds value)
  Mean adjustment magnitude: [score]
  Verdict: [LLM adds value / LLM neutral / LLM degrades]
```

**Quantitative-only baseline:** Also track what would have happened with zero LLM adjustment (just using base rate probabilities as-is). This is the benchmark the LLM must beat to justify its adjustments.

**Alert threshold:** If alpha is negative (LLM degrades forecast) for 8+ consecutive resolved forecasts, flag an amendment: "Regime forecast adjustments are consistently making predictions worse. Consider: (a) reducing adjustment magnitudes, (b) deferring to base rates for the next 4 weeks, (c) investigating which adjustment types are most harmful."

**Minimum sample size:** Do not compute cumulative alpha or trigger alerts until at least 20 forecasts have resolved. Before that threshold, track individual scores but note "insufficient sample for statistical significance."

Produce an inspection report:

```markdown
### Inspection Report

**Analytical Accuracy (Prior Week):**
[Scorecard from 2h above. If first week, skip.]

**Cumulative Accuracy (if 4+ weeks of data):**
[Running hit rate by category: regime calls, asset tilts, event predictions, thesis accuracy]

**Persistent Gaps (3+ weeks):**
[List each with proposed root cause]

**Degrading Skills:**
[Any skill with self_score trending down over 3+ data points.]

**Source Freshness Issues:**
[Any skill consistently using sources older than 7 days for data that should be current.]

**Search Effectiveness:**
[Any skill with useful_results/attempted ratio below 0.5.]

**Synthesis Completeness:**
[Frequency of incomplete inputs to synthesis. Which skills are the weak links?]

**Reasoning Quality:**
[Any missed connections between skills. Any insights that were found but not used downstream. Any thesis parameters that should have been reviewed based on new information.]

**Regime Evaluator Health:**
[Divergence frequency, lead time, CHALLENGE accuracy (split by stability vs. transition context), reasoning audit hit rate. If fewer than 4 weeks of data, note "insufficient data for evaluator health assessment."]
```

---

## Step 3: AMEND — Propose Specific Changes

For each issue identified in the inspection, propose a targeted amendment. **Before proposing any amendment, read the target skill's definition file** from `references/` to verify the capability doesn't already exist. If the skill definition already covers the proposed change — for example, Skill 7 already defines thesis monitoring, or Skill 12 already defines chart generation — do not propose the amendment. Instead, note that the capability exists and diagnose why it didn't fire (e.g., first-run timing, missing input, execution order). Proposing infrastructure that already exists wastes human review time and signals that the improvement loop isn't reading the system it's trying to improve.

Amendments must be:

1. **Specific** — not "improve search strategy" but "in Skill 2, replace search query 'M2 money supply latest' with 'Federal Reserve H.6 money stock [month] [YEAR]'"
2. **Targeted** — change one thing at a time, not rewrite the whole skill
3. **Justified** — explain why this change should fix the issue based on the evidence
4. **Reversible** — the original instruction must be preserved in the changelog
5. **Non-redundant** — verified against the target skill's definition that this capability doesn't already exist

### Amendment Template

```markdown
### AMENDMENT PROPOSAL: [ID — e.g., A-2026W12-001]

**Skill:** [which skill]
**Issue:** [what's broken, with evidence from observations]
**Root Cause:** [why it's happening — be specific]

**Current Instruction:**
> [exact text being changed]

**Proposed Instruction:**
> [new text]

**Rationale:** [why this change should fix the issue]

**Expected Impact:** [which metric should improve — e.g., "searches_with_useful_results for M2 should increase from 0/4 to 2+/4"]

**Risk:** [could this break something else?]
```

### Amendment Types (from cognee framework)

- **Tighten search terms** — make queries more specific to surface the right data
- **Add missing condition** — skill instruction doesn't handle a case that keeps occurring
- **Reorder execution steps** — current order causes a dependency to be missed
- **Change output format** — a section isn't producing useful signal, restructure it
- **Remove dead weight** — a data target that web search consistently can't find; stop looking and note it as a manual check item
- **Add fallback sources** — if primary search strategy fails, try alternative queries

---

## Step 4: EVALUATE — Assess Prior Amendments

Read `outputs/improvement/amendment-tracker.md`. For each amendment with status IMPLEMENTED (not yet evaluated), check whether the target metric improved:

```markdown
### Amendment Evaluation

| Amendment ID | Applied Week | Target Metric | Before | After (this week) | Verdict |
|-------------|-------------|--------------|--------|-------------------|---------|
| [ID] | [week] | [metric] | [value] | [value] | [EFFECTIVE / INEFFECTIVE / INCONCLUSIVE] |
```

- **EFFECTIVE:** Target metric improved. Amendment stays. Update the tracker.
- **INEFFECTIVE:** No improvement after 2 weeks. Recommend revert. Update the tracker.
- **INCONCLUSIVE:** Not enough data yet (first week after amendment). Keep and check next week.

**After evaluation, update the amendment tracker file** (`outputs/improvement/amendment-tracker.md`):
- Move evaluated amendments to the correct status
- Update the "After" metric column with this week's actual numbers
- Add a log entry for this week's evaluation
- Before proposing any new amendments, check the tracker to ensure you're not re-proposing something already implemented

---

## Output Format

Save the full improvement loop output as `YYYY-Www-improvement.md` in the improvement outputs directory.

### Dashboard Data JSON (mandatory)

After writing the markdown report, write a structured JSON sidecar alongside it:

**Path:** `outputs/improvement/YYYY-Www-improvement-data.json` (e.g. `2026-W13-improvement-data.json` — week prefix must match the markdown filename)

This file provides the dashboard's System Health tab with all structured data. The dashboard reads this JSON for tables and KPI cards. The markdown report stays as the expandable full report.

```json
{
  "meta": {
    "week": "2026-W13",
    "run_date": "2026-03-28",
    "skill": "skill-8-improvement-loop",
    "version": "1.0"
  },
  "health": {
    "overall_score": 88,
    "trend": "stable",
    "skills_at_risk": "None"
  },
  "skill_scores": [
    {
      "skill": "Central Bank Watch",
      "self_score": 0.92,
      "data_points_extracted": 24,
      "data_points_expected": 18,
      "confidence": "high",
      "freshest_data": "2026-03-28"
    }
  ],
  "accuracy": {
    "cumulative_accuracy": 0.85,
    "scoreable_calls": 13,
    "correct_predictions": 10,
    "partial_predictions": 2,
    "wrong_predictions": 1,
    "by_category": [
      {
        "category": "Regime",
        "correct": 1,
        "partial": 0,
        "wrong": 0,
        "total": 1,
        "accuracy_pct": 100,
        "confidence": "High"
      }
    ],
    "scorecard": [
      {
        "call": "Regime: Stagflation (5th week)",
        "outcome": "NFP -92K, Michigan 53.3, oil $99.64 — deepening confirmed",
        "verdict": "CORRECT",
        "reasoning": "All growth/inflation indicators confirmed stagflation continuation"
      }
    ]
  },
  "amendments": [
    {
      "id": "A-2026W13-001",
      "proposed": "2026-03-28",
      "skill": 3,
      "title": "Remove Non-Existent FRED Series",
      "description": "Remove NAPMNOI, NAPMPI (confirmed non-existent on FRED)",
      "target_metric": "data_success_rate",
      "status": "approved_for_immediate_implementation",
      "verdict": "approved",
      "before": 0.954,
      "after": 1.0
    }
  ],
  "data_gaps": [
    {
      "gap_id": "DG-001",
      "title": "TGA balance (FRED WTREGEN)",
      "skill": 3,
      "severity": "HIGH",
      "consecutive_weeks": 3,
      "status": "escalated",
      "action": "Add alternative series"
    }
  ]
}
```

> **Dashboard compatibility:** The dashboard normalizes key variations. For example, `overall_score` and `score` both work for health; `self_score` and `score` both work for skill scores; `cumulative_accuracy` (0-1 float) and `cumulative_pct` (0-100 int) both work for accuracy. Use the key names above (matching the W13 actual output) as the canonical schema going forward.

**Rules for the JSON sidecar:**
1. `health.overall_score` is an integer (0-100). The dashboard normalizes to percentage display. Include `trend` ("stable", "improving", "degrading") when determinable.
2. `accuracy.cumulative_accuracy` is a float (0.0-1.0) OR `cumulative_pct` as integer (0-100). Both work. This feeds the Track Record KPI card on the Overview tab.
3. `accuracy.by_category` should include all categories from the cumulative accuracy table in the accuracy tracker. Each entry: `category`, `correct`, `partial`, `wrong`, `total`, `accuracy_pct`, `confidence`.
4. `accuracy.scorecard` should include **every scored call** from the current week's scoring — not just a summary. Each entry needs `call` (what we predicted), `outcome` (what happened), `verdict` ("CORRECT", "PARTIALLY CORRECT", "WRONG", or "TOO EARLY"), and `reasoning` (one sentence why). If the scorecard is too large to include inline, the dashboard falls back to `accuracy-tracker.md`.
5. `skill_scores` — one object per skill. Use `self_score` (float 0-1), `skill` (name string), `data_points_extracted`, `data_points_expected`, `freshest_data`, `confidence`.
6. `amendments` — one object per amendment. Use `id`, `proposed` (date), `skill` (number or string), `title`, `description`, `target_metric`, `status`, `verdict`, `before`, `after`.
7. `data_gaps` — one object per gap. Use `gap_id`, `title`, `skill` (number), `severity` (HIGH/MEDIUM/LOW), `consecutive_weeks`, `status`, `action`.
8. All values must be the **actual data** from the analysis — not placeholders. Copy from the corresponding markdown sections.

```markdown
## Self-Improvement Loop — Week of [Date]

### System Health Summary
**Overall system score:** [average of all skill self_scores]
**Trend:** [improving / stable / degrading]
**Skills at risk:** [any skill with self_score < 0.5 or 3-week downtrend]

### Observation Summary
[Table from Step 1]

### Data Gaps Inventory
[Table from Step 1]

### Inspection Report
[From Step 2]

### Amendment Proposals
[From Step 3 — 0 or more amendments]

### Amendment Evaluation
[From Step 4 — only if prior amendments exist]

### Changelog
[Running log of all amendments applied, with dates and version numbers]

### Recommendations for Human Review
[Anything that requires judgment rather than automated fixing — e.g., "Consider removing TGA balance from Skill 2 expected data points. Web search has not surfaced this data in 6 consecutive weeks. Recommend checking FRED manually and removing from automated expectations."]
```

## Quality Standards

- Every amendment proposal must include the exact text to change and the exact replacement text — no vague "improve the search terms"
- Evaluations must reference actual metric values, not subjective assessments
- The loop should produce 0 amendments on a good week. Not every run needs to propose changes. If the system is working well, say so.
- Never apply amendments automatically to the skill files. All proposals go to the output file for human review.
- Track consecutive weeks for each persistent gap — this is the evidence base for deciding when to remove a data target vs. fix the search strategy

## Meta Block

```yaml
---
meta:
  skill: self-improvement-loop
  skill_version: "1.1"
  run_date: "[ISO date]"
  amendments_proposed: [number]
  amendments_evaluated: [number]
  amendments_effective: [number]
  amendments_reverted: [number]
  system_health_score: [average of all skill self_scores]
  system_health_trend: [improving/stable/degrading]
  notes: "[any issues]"
---
```
