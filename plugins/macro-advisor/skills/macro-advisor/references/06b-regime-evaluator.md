# Skill 6b: Regime Evaluator

## Objective

Independently evaluate Skill 6's regime classification by performing a blind regime assessment from raw data, auditing the reasoning chain, and checking input quality. This skill exists because generators cannot reliably challenge their own conclusions — anchoring and rationalization are structural, not fixable by prompting.

This skill respects the 2-month confirmation filter and 6-month direction window as architectural rules. It does not bypass them. It provides a parallel signal: how long has the raw weekly data been pointing somewhere other than the official regime call?

**Scope boundary:** This skill produces an evaluation for the self-improvement loop. It does not change positioning, modify thesis conviction, override Skill 6, or appear in the Monday Briefing. Skill 8 is the sole consumer — it monitors evaluator health, tracks divergence patterns, and surfaces issues through the improvement report. No other skill reads or reacts to the verdict.

## Inputs

Read ALL of the following:

1. **Collection skill outputs (Skills 1-5) from the current week** — the same raw inputs Skill 6 used.
2. **Data snapshot** — `outputs/data/latest-snapshot.json` and `outputs/data/latest-data-full.json` for hard numbers.
3. **Current week's Skill 6 synthesis** — `outputs/synthesis/YYYY-Www-synthesis.md` and `outputs/synthesis/YYYY-Www-synthesis-data.json`.
4. **Divergence streak script output** — passed as input from the orchestrator. Contains `consecutive_divergence_weeks` and prior week's blind/official regimes.

Do NOT read:
- Prior week's synthesis (no regime anchoring)
- `outputs/regime-history.json` (no streak context)
- Regime streak script output (no continuity signal)
- `outputs/synthesis/regime-evaluation-history.json` (no self-anchoring — the streak script reads this, not the evaluator)
- Any prior week's regime evaluation (no self-anchoring)

The absence of history is the point. This skill sees only this week's data, this week's Skill 6 output, and the streak number (a single integer from a deterministic script).

---

## Step 1: DETERMINISTIC REFERENCE COMPARISON

Read `outputs/data/regime-classifier-output.json`. This is the deterministic reference — a Python script (`regime_classifier.py`) that computes growth/inflation/liquidity scores from FRED data using the exact same methodology as `regime_backtest.py` (6-month direction window, majority vote, 36-month rolling medians, 2-month confirmation filter). It runs before this skill in the orchestration chain.

**If `regime-classifier-output.json` does not exist** (classifier failed or hasn't been deployed yet), fall back to the legacy blind classification: read Skills 1-5 and the data snapshot, classify the regime yourself using the methodology documented in `references/06-weekly-macro-synthesis.md`. Note "classifier unavailable — using LLM blind classification" in the output.

**If the classifier output exists:**

1. **Read the classifier's scores:** `growth.score`, `inflation.score`, `liquidity.score`, `regime_family`, `regime_8`, and the `confirmation_filter` block.

2. **Compare against Skill 6:** Does the classifier's `regime_family` match Skill 6's regime family? Compare the CONFIRMED regimes (both the classifier and Skill 6 apply the 2-month confirmation filter, so divergences are substantive, not artifacts of raw-vs-confirmed timing).

3. **Score comparison:** How far apart are the continuous scores? A growth score of -0.25 (classifier) vs. -0.30 (Skill 6) is noise. A growth score of -0.25 (classifier) vs. +0.15 (Skill 6) is a meaningful divergence that requires explanation.

4. **Flag divergence type:**
   - **Family divergence:** Classifier and Skill 6 disagree on the 4-quadrant regime family. This is the primary signal.
   - **Score divergence:** Same family but scores differ by >0.3 on any axis. Informative but secondary.
   - **Liquidity divergence:** Classifier and Skill 6 disagree on Ample/Tight. Note: the classifier uses monthly data while Skill 6 uses a rolling 4-week assessment — minor divergence is expected. Only flag if the liquidity condition is opposite.

5. **LLM value-add check:** If Skill 6 AGREES with the classifier (same family, scores within 0.3), note this. If agreement persists for 8+ consecutive weeks, flag: "Skill 6 has agreed with the deterministic classifier for N weeks — is the LLM adding qualitative value, or just echoing the numbers?" Some divergence is healthy — it means the LLM is incorporating context the classifier cannot see (Fed forward guidance, geopolitical risk, positioning data).

If the classifier and Skill 6 agree → the data and the official call agree this week.
If they diverge → record the divergence and examine whether Skill 6's reasoning justifies the override.

---

## Step 2: DIVERGENCE STREAK INTERPRETATION

Read the streak number from the script output. Do NOT compute it yourself.

Interpretation thresholds:

| Consecutive Divergent Weeks | Interpretation | Verdict Impact |
|----------------------------|----------------|----------------|
| 0 (agreement) | Data confirms the regime | None |
| 1-2 | Normal noise | None |
| 3-4 | Interesting — log it | Upgrade to REVIEW if reasoning audit also flags issues |
| 5-6 | Approaching confirmation window | Include in evaluation narrative |
| 7+ | Independent confirmation threshold | Escalate to CHALLENGE if reasoning audit also flags issues |

The thresholds are NOT mechanical overrides. A 7-week divergence streak does not automatically produce CHALLENGE — it means the evaluator should give serious weight to the possibility that the regime has changed. The reasoning audit (Step 3) determines whether the divergence is substantive or an artifact of noisy single-week readings.

---

## Step 3: REASONING AUDIT

Read Skill 6's full synthesis output. For each section, check:

### 3a. Claim-Data Alignment

For every causal claim in the synthesis (e.g., "liquidity is driving risk appetite," "growth is weakening because employment is softening"), verify:
- Is the claim supported by a specific data point from Skills 1-5 or the snapshot?
- Does the cited data actually point in the direction claimed?
- Is the data current (within 14 days) or stale?

Flag any claim that is:
- **Unsupported** — no specific data point cited
- **Contradicted** — data points in the opposite direction
- **Stale** — relies on data older than 14 days for something that should be current

### 3b. Omission Check

Scan the collection skill outputs for significant findings that did NOT make it into the synthesis. A "significant finding" is one that:
- Directly relates to the growth or inflation axis
- Would change the regime score by more than 0.1 if incorporated
- Was flagged as important by the collection skill's own assessment

### 3c. Confidence Calibration

Check Skill 6's confidence rating against input quality:
- How many collection skills ran successfully (score > 0.5)?
- Are there any High-severity data gaps (from prior Skill 8 output, if available)?
- Is the confidence rating appropriate given the input completeness?

Flag if:
- Confidence is "High" but fewer than 4 of 5 inputs scored above 0.5
- Confidence is "High" but the regime call contradicts one or more collection skill conclusions without explaining why

---

## Step 4: VERDICT

Combine the three checks into a single verdict:

**PASS** — Blind classification agrees with Skill 6. Reasoning audit found no unsupported or contradicted claims. Confidence is calibrated. The system is working as intended.

**REVIEW** — Minor issues found. One or more of:
- Blind classification agrees but reasoning audit found 1-2 partially supported claims
- Blind classification diverges for 1-2 weeks (normal noise) but reasoning is solid
- Confidence is slightly optimistic given input quality

**CHALLENGE** — Substantive concern. One or more of:
- Blind classification has diverged for 5+ consecutive weeks AND reasoning audit found unsupported or contradicted claims
- Blind classification has diverged for 7+ consecutive weeks (regardless of reasoning audit)
- Reasoning audit found 3+ unsupported/contradicted claims in a single week
- Confidence is "High" with clearly degraded inputs (fewer than 3 of 5 skills above 0.5)

A CHALLENGE verdict does NOT override Skill 6. It does NOT change thesis conviction, positioning, or any downstream behavior. It feeds Skill 8's self-improvement loop as a system health signal.

---

## Output Format

Save as `outputs/synthesis/YYYY-Www-regime-evaluation.md`:

```markdown
## Regime Evaluation — Week of [Date]

### Deterministic Reference
**Source:** [regime-classifier-output.json / LLM blind classification (fallback)]
**Regime (reference):** [full 8-regime label]
**Regime family (reference):** [quadrant]
**Growth score (reference):** [value]
**Inflation score (reference):** [value]
**Liquidity score (reference):** [value]
**Liquidity condition (reference):** [Ample / Tight]
**Skill 6 called:** [full 8-regime label] (family: [quadrant], growth: [value], inflation: [value], liquidity: [value])
**Family agreement:** [Yes / No]
**Liquidity agreement:** [Yes / No]
**Consecutive weeks of family disagreement:** [N — from streak script]

[If disagreement: 2-3 sentences explaining which data points drive the divergence. Be specific — "Skill 3's employment data shows unemployment rising for the third consecutive month, which the blind classification reads as growth-negative, while Skill 6 weights the still-strong ISM reading more heavily."]

### Reasoning Audit

**Claims audited:** [N]
**Fully supported:** [N]
**Partially supported:** [N]
**Unsupported:** [N]
**Contradicted:** [N]

[For each flagged claim:]
> **Claim:** "[exact quote from Skill 6]"
> **Data check:** [what the data actually shows]
> **Assessment:** [supported / partially supported / unsupported / contradicted]

**Significant omissions:** [List any collection skill findings that should have been in the synthesis but weren't, or "None found"]

### Input Quality Check
**Collection skill scores:** [Skill 1: X, Skill 2: X, Skill 3: X, Skill 4: X, Skill 5: X]
**Skills above 0.5:** [N of 5]
**Skill 6 confidence:** [what it said]
**Calibration assessment:** [Appropriate / Slightly optimistic / Overstated]

### Verdict: [PASS / REVIEW / CHALLENGE]

[2-3 sentence summary of why this verdict. If CHALLENGE: what specifically is the concern and what would resolve it.]
```

---

## Divergence History Update

After producing the output, update `outputs/synthesis/regime-evaluation-history.json`:

```json
[
  {
    "week": "2026-W13",
    "reference_regime": "Disinfl. Slowdown — Tight Liquidity",
    "reference_regime_family": "Disinflationary Slowdown",
    "reference_growth_score": -0.35,
    "reference_inflation_score": -0.18,
    "reference_liquidity_score": -0.25,
    "reference_liquidity_condition": "tight",
    "skill6_regime": "Overheating — Ample Liquidity",
    "skill6_regime_family": "Overheating",
    "skill6_growth_score": 0.22,
    "skill6_inflation_score": 0.42,
    "skill6_liquidity_score": 0.30,
    "skill6_liquidity_condition": "ample",
    "diverged": true,
    "liquidity_diverged": true,
    "consecutive_divergence_weeks": 6,
    "reasoning_issues": 2,
    "verdict": "CHALLENGE"
  }
]
```

Rules:
- Append one entry per week.
- If an entry for this ISO week already exists (same-week rerun), overwrite it.
- The `consecutive_divergence_weeks` value comes from the streak script output. Do NOT recompute it.

---

## Quality Standards

- When the deterministic classifier is available, the reference classification is computed by `regime_classifier.py` using the shared `regime_core.py` module — the same methodology as `regime_backtest.py`. This is a deterministic computation, not an LLM judgment. Divergences between this reference and Skill 6's LLM-based classification are the signal.
- When falling back to LLM blind classification (classifier unavailable), use the SAME weighting methodology as Skill 6 (documented in `references/06-weekly-macro-synthesis.md`). The only difference is the absence of prior context.
- The reasoning audit must quote exact claims from Skill 6's output. No paraphrasing — the reader should be able to trace every flag back to the source text.
- PASS is the expected verdict on most weeks. Skill 8 monitors CHALLENGE frequency in context (stability vs. transition periods).
- The evaluator must NOT recommend a regime change. It identifies divergence and flags reasoning issues. The regime call belongs to Skill 6.

## What This Skill Does NOT Do

- Override Skill 6's regime call
- Modify thesis conviction or confidence levels
- Change any downstream positioning or recommendations
- Appear in the Monday Briefing
- Apply the 2-month confirmation filter (that's Skill 6's job)
- Read regime history or its own prior evaluations (intentionally blind)
- Recommend positioning changes
- Produce investment views

## Meta Block

```yaml
---
meta:
  skill: regime-evaluator
  skill_version: "1.0"
  run_date: "[ISO date]"
  reference_regime: "[full 8-regime label]"
  reference_regime_family: "[quadrant]"
  reference_growth_score: [number]
  reference_inflation_score: [number]
  reference_liquidity_score: [number]
  reference_liquidity_condition: "[ample/tight]"
  skill6_regime: "[full 8-regime label]"
  skill6_regime_family: "[quadrant]"
  diverged: [true/false]
  liquidity_diverged: [true/false]
  consecutive_divergence_weeks: [number]
  claims_audited: [number]
  claims_unsupported: [number]
  claims_contradicted: [number]
  verdict: "[PASS/REVIEW/CHALLENGE]"
  notes: "[any issues]"
---
```
