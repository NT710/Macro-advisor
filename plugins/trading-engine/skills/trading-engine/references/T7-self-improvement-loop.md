# Skill T7: Self-Improvement Loop

## Objective

Review all meta blocks and performance data from the current run. Identify systematic patterns in execution quality, reasoning quality, and trading performance. Propose specific amendments. Evaluate prior amendments. This mirrors the macro advisor's Skill 8 but tracks trading-specific metrics.

## Core Framework: Observe → Inspect → Amend → Evaluate

Same cognee-inspired architecture as the macro advisor's improvement loop. The trading engine's skills are living components. Without structured observation, degradation is invisible.

## Inputs

Read ALL of the following:

**Amendment tracker (read first):**
`outputs/improvement/amendment-tracker.md` — check before proposing new amendments.

**Performance tracker (read for cumulative scoring):**
`outputs/improvement/performance-tracker.md` — persistent record of execution quality over time.

**Meta blocks from all skills produced in the current run:**
1. T0 Portfolio Snapshot meta
2. T1 Signal Parser meta
3. T2 Position Reconciler meta
4. T3 Trade Reasoner meta
5. T4 Order Executor meta
6. T5 Trade Logger meta
7. T6 Performance Tracker meta

**Latest performance report:** `outputs/performance/`

**Prior improvement loop output** (if exists) for trend context.

---

## Step 1: OBSERVE — Extract Structured Metrics

```markdown
### Observation Summary — [Date]

| Skill | Self Score | Confidence | Key Metric | Notes |
|-------|-----------|-----------|-----------|-------|
| T0 Snapshot | [score] | [conf] | positions: [N] | |
| T1 Parser | [score] | [conf] | signals: [N], alerts: [N] | |
| T2 Reconciler | [score] | [conf] | deltas: [N], violations: [N] | |
| T3 Reasoner | [score] | [conf] | orders: [N], skipped: [N] | |
| T4 Executor | [score] | [conf] | filled: [N], rejected: [N] | |
| T5 Logger | [score] | [conf] | logged: [N] | |
| T6 Performance | [score] | [conf] | return: [X]%, drawdown: [X]% | |
```

---

## Step 2: INSPECT — Pattern Detection

### 2a. Execution Quality
- **Fill rate:** What percentage of orders got filled? If below 90%, the order type or limit price buffer may need adjustment.
- **Slippage:** Average slippage across all filled orders. If consistently above 0.5%, limit order buffers may be too tight.
- **Rejection rate:** Any rejected orders? Categorize reasons (insufficient funds, invalid symbol, market closed).
- **Kill switch response time:** When a kill switch fired, how many runs elapsed before the exit was executed? Target: 0 (same run). If any kill switch exit was delayed, that's a critical failure.

### 2b. Reasoning Quality
- **Devil's advocate rigor:** Are the bear cases specific and actionable, or are they generic boilerplate? Read the actual text. "Markets could go down" is useless. "If tariff escalation reaches EU auto sector by May, this value tilt loses its catalyst" is useful.
- **Expression sizing quality:** Are sizing decisions well-reasoned? Look for signs of lazy defaults (e.g., always skipping third-order, always sizing first-order at midpoint). The reasoner should be making differentiated decisions based on conviction and context.
- **Skip quality:** Were skipped trades later shown to be good skips (the position would have lost money) or bad skips (missed opportunity)?

### 2c. Signal Parsing Quality
- **Staleness:** How often does T1 report stale signals?
- **Kill switch scanning accuracy:** Did T1 correctly identify kill switch proximity? Cross-reference with what actually happened.
- **Thesis parsing completeness:** Are all active theses being parsed? Any parsing failures?

### 2d. Performance Quality (DO NOT optimize by asset class)

This is where the anti-confirmation-bias rule matters most. Track performance by:

- **Mechanism type:** Which thesis mechanisms (divergence, regime shift, etc.) are profitable?
- **Layer:** Is the edge in regime tilts or thesis overlays?
- **Time horizon:** Do tactical or structural theses perform better?
- **Devil's advocate accuracy:** What percentage of losses were anticipated in the bear case?

DO NOT track or optimize by:
- Which asset classes recently performed well
- Which specific ETFs had the best returns
- Which sectors were profitable

That would be curve-fitting to recent winners, not improving the system's reasoning.

### 2e. Scaling Quality
- Are we hitting target allocations within the expected number of runs?
- Is the scaling pace appropriate? (Too slow means we miss moves. Too fast means we overshoot.)

### 2f. Risk Discipline
- Any risk limit violations during the week?
- Drawdown trajectory: improving, stable, or worsening?
- Was the circuit breaker ever triggered?

---

## Step 3: AMEND — Propose Specific Changes

Same amendment standards as the macro advisor: specific, targeted, justified, reversible.

### Amendment Template

```markdown
### AMENDMENT PROPOSAL: [ID — e.g., AT-2026W13-001]

**Skill:** [which trading skill]
**Issue:** [what's broken, with evidence]
**Root Cause:** [why it's happening]

**Current Instruction:**
> [exact text being changed]

**Proposed Instruction:**
> [new text]

**Rationale:** [why this fixes the issue]
**Expected Impact:** [which metric improves]
**Risk:** [could this break something?]
```

### What CAN Be Amended
- Limit order buffer width (if fill rates are low)
- Scaling pace (if consistently over/under-shooting)
- Devil's advocate prompt specificity (if bear cases are too generic)
- Signal parsing logic (if theses are being misread)
- Reconciliation threshold (the 1% minimum delta for action)

### What CANNOT Be Amended
- Risk constraints (max position, max sector, max drawdown, min cash, max thesis overlay)
- The kill switch = immediate exit rule
- The anti-confirmation-bias rules (T3 doesn't see P&L, T1 is stateless, no optimizing by asset class)
- The devil's advocate requirement

These are structural safeguards. If the improvement loop could remove them, it would eventually optimize them away in pursuit of short-term performance — which is exactly how systems blow up.

---

## Step 4: EVALUATE — Assess Prior Amendments

Same as macro advisor Skill 8:

```markdown
### Amendment Evaluation

| Amendment ID | Applied Week | Target Metric | Before | After | Verdict |
|-------------|-------------|--------------|--------|-------|---------|
| [ID] | [week] | [metric] | [value] | [value] | EFFECTIVE/INEFFECTIVE/INCONCLUSIVE |
```

EFFECTIVE → keep. INEFFECTIVE after 2 weeks → revert. INCONCLUSIVE → keep checking.

Update `outputs/improvement/amendment-tracker.md` with results.

---

## Output Format

Save as `outputs/improvement/YYYY-Www-trading-improvement.md`:

```markdown
## Trading Engine Self-Improvement — Week of [Date]

### System Health Summary
**Overall score:** [average of all skill scores]
**Trend:** [improving / stable / degrading]
**Skills at risk:** [any below 0.5 or 3-week downtrend]

### Observation Summary
[Table from Step 1]

### Inspection Report

**Execution Quality:**
- Fill rate: [X]%
- Avg slippage: [X]%
- Kill switch response: [pass/fail]

**Reasoning Quality:**
- Devil's advocate rigor: [adequate/needs improvement]
- Expression sizing differentiation: [adequate/lazy defaults detected]
- Skip quality: [N] skips were [good/bad/mixed]

**Performance Quality:**
- Best mechanism type: [type] at [X]% win rate
- Worst mechanism type: [type] at [X]% win rate
- Layer attribution: regime [X]% return vs thesis [X]% return
- Bear case accuracy: [X]% of losses anticipated

**Risk Discipline:**
- Violations: [N]
- Drawdown trend: [direction]

### Amendment Proposals
[From Step 3 — 0 or more]

### Amendment Evaluation
[From Step 4 — only if prior amendments exist]

### Recommendations for Human Review
[Anything requiring judgment — e.g., "Consider reducing thesis overlay cap from 25% to 20%.
The thesis layer has contributed -2.3% over 6 weeks while regime tilts contributed +4.1%.
This suggests the thesis overlays are net negative at current sizing."]
```

## Quality Standards

- Zero amendments is a valid output. The system doesn't need to fix something every week.
- Never propose amending the hardcoded risk constraints or anti-bias rules.
- Every evaluation must reference actual metric values, not subjective impressions.
- The "Recommendations for Human Review" section is for structural questions the loop can't resolve autonomously — sizing philosophy, whether to change risk limits, whether the macro advisor's thesis quality is good enough to trade on.

## Meta Block

```yaml
---
meta:
  skill: self-improvement-loop
  skill_version: "1.0"
  run_date: "[ISO date]"
  amendments_proposed: [number]
  amendments_evaluated: [number]
  amendments_effective: [number]
  amendments_reverted: [number]
  system_health_score: [average]
  system_health_trend: [improving/stable/degrading]
  execution_fill_rate: [number]
  kill_switch_response: [pass/fail]
  notes: "[any issues]"
---
```
