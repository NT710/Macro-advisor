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

## Step 1: BLIND CLASSIFICATION

Read only the collection skill outputs (Skills 1-5) and the data snapshot. Without referencing Skill 6's conclusions, classify the current regime:

1. **Growth direction:** Extract growth indicators from Skill 3 and the snapshot. ISM manufacturing, unemployment direction, NFP trend, retail sales, GDP tracking. Is growth rising or falling based on this week's data alone?

2. **Inflation direction:** Extract inflation indicators from Skill 3 and the snapshot. Core PCE, PPI, breakeven inflation, wage growth, commodity prices. Is inflation rising or falling based on this week's data alone?

3. **Liquidity condition:** Extract liquidity indicators from Skill 2 and the snapshot. M2 YoY vs. 36-month median, NFCI vs. 36-month median, Fed balance sheet YoY vs. 36-month median. Classify as Ample (majority above trend) or Tight (majority below trend). Note: this is a single-week blind reading. Skill 6 uses a rolling 4-week assessment for its official liquidity condition — a single-week divergence is expected and not concerning. Only flag liquidity divergence if the blind reading has disagreed for 3+ consecutive weeks.

4. **Classify:** Place the data in the regime model. First determine the regime family (four-quadrant: Growth × Inflation), then apply the liquidity condition for the full 8-regime label. Growth × inflation classification is a point-in-time reading. Liquidity classification is compared against Skill 6's 4-week rolling assessment.

5. **Score:** Produce growth_score (-1.0 to +1.0), inflation_score (-1.0 to +1.0), and liquidity_score (-1.0 to +1.0) using the same weighting methodology as Skill 6 (documented in `references/06-weekly-macro-synthesis.md`).

6. **Compare:** Does the blind classification match Skill 6's regime call? Compare on `regime_family` (four-quadrant) for the primary divergence check. Flag liquidity condition divergence separately — it's informative but does not drive the streak count.

If yes → the data and the official call agree this week.
If no → record the divergence.

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

### Blind Classification
**Regime from data alone:** [full 8-regime label]
**Regime family (blind):** [quadrant]
**Growth score (blind):** [value]
**Inflation score (blind):** [value]
**Liquidity score (blind):** [value]
**Liquidity condition (blind):** [Ample / Tight]
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
    "blind_regime": "Disinfl. Slowdown — Tight Liquidity",
    "blind_regime_family": "Disinflationary Slowdown",
    "blind_growth_score": -0.35,
    "blind_inflation_score": -0.18,
    "blind_liquidity_score": -0.25,
    "blind_liquidity_condition": "tight",
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

- The blind classification must use the SAME weighting methodology as Skill 6 (documented in `references/06-weekly-macro-synthesis.md`). The only difference is the absence of prior context. If the methodology produces a different result without history, that's the signal.
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
  blind_regime: "[full 8-regime label]"
  blind_regime_family: "[quadrant]"
  blind_growth_score: [number]
  blind_inflation_score: [number]
  blind_liquidity_score: [number]
  blind_liquidity_condition: "[ample/tight]"
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
