# Skill 7: Thesis Generator & Monitor

## Objective

Two functions in one skill. Function A generates new investment thesis candidates from data patterns identified in the weekly synthesis. Function B monitors active theses against their stated assumptions and kill switches. This is where surveillance becomes actionable.

## Also Available On-Demand

This skill can be invoked manually to structure any macro thesis. You don't need the weekly chain running to use it. If you have a macro view you want to formalize, use Function A's template to structure it with explicit assumptions, kill switches, and time horizons.

---

## Thesis Classification

Before generating a thesis, classify it. This determines which template to use and how deep the research needs to go.

**Tactical thesis** — Generated from weekly data patterns. The mechanism is well-understood and operates within the current macro cycle. Time horizon: weeks to quarters. Uses the standard thesis template below. No prerequisite research step required.

Examples: "Duration will outperform as the Fed pivots," "Positioning is extreme in treasuries ahead of FOMC," "Regime shift from Goldilocks to Overheating favors value over growth."

**Structural thesis** — Involves physical constraints, supply-side bottlenecks, multi-year cycles, or structural market dislocations where the mechanism operates on a longer timescale than the weekly data cycle. Time horizon: quarters to years. Requires a Skill 11 Structural Research Brief as input before generation. Uses the expanded structural thesis template.

Examples: "Decade of mining underinvestment meets three concurrent demand shocks — metals supercycle," "AI capex cycle drives structural power infrastructure deficit," "Demographic shift reshapes housing demand for 10+ years."

**How to decide:** Ask three questions:

1. **What is the binding constraint?** Name the specific bottleneck, supply constraint, or structural dynamic the thesis rests on.
2. **How long does it take to change?** Estimate in months or years. A Fed rate decision changes in weeks. A copper mine takes 15 years.
3. **How long will the current deviation from equilibrium persist?** Even if the constraint loosens, will the gap take more than 4 quarters to close?

If the constraint takes >12 months to change OR the deviation persists >4 quarters, classify as structural. Otherwise, tactical.

When genuinely uncertain, classify as tactical but include a note: "Flagged for potential structural upgrade if [specific condition] is observed." Do not use "uncertain" as a reason to avoid Skill 11 research when the constraint timeline clearly exceeds 12 months.

**If structural:** Before generating the thesis, check for an existing Skill 11 research brief in `outputs/research/`. If none exists, flag: "This pattern warrants structural research before thesis generation. Invoke Skill 11 on [theme]." Do not generate a structural thesis without the research foundation — it will lack the quantified depth that makes structural theses monitorable.

---

## Function A: Generate Thesis Candidates

Thesis candidates come from two sources: data patterns (primary) and external analyst frameworks (secondary). Both feed into the same classification and template system.

### Source 1: Data Patterns

Read the weekly synthesis output. These are common pattern categories, not an exhaustive list:

1. **Divergences between macro data and market pricing** — when the data says one thing and prices say another
2. **Regime shifts not yet reflected in positioning** — the macro picture is turning but positioning hasn't caught up
3. **Cross-market dislocations** — two related markets sending contradictory signals (one of them is wrong)
4. **Policy shifts with delayed market impact** — an action was taken but the price effect hasn't materialized yet
5. **Positioning extremes aligned with macro catalysts** — crowded positions meeting an incoming catalyst for reversal
6. **Anything else that looks anomalous.** The categories above are common patterns, not a closed set. If something in the data strikes you as unusual, investigate it even if it doesn't fit these five boxes. The best theses often come from noticing something no framework predicted.

### Source 2: Analyst-Sourced Investigation Candidates

Read the current week's analyst monitor output (`outputs/collection/YYYY-Www-analyst-monitor.md`). Look for structural views, novel frameworks, or macro arguments that meet ALL of these criteria:

1. **Not already captured by an existing thesis.** Check `outputs/theses/active/` — if we already have a thesis covering this theme, the analyst view belongs in Function B's cross-referencing, not here.
2. **Not already being pursued as a thesis candidate from data patterns.** If Source 1 already flagged this theme for thesis generation this week, the analyst view belongs as supporting evidence, not a separate investigation. However: if the analyst offers a *different mechanism* or *different time horizon* than what the synthesis identified, that IS worth investigating separately — same theme, different thesis.
3. **Contains a testable mechanism.** "Markets will crash" is an opinion. "Japan's YCC exit will force a repricing of global duration because Japanese institutional investors hold $X trillion in foreign bonds and will repatriate as domestic yields rise" is a mechanism. Only the second is worth investigating.

When a candidate passes all three criteria, flag it for Skill 11 investigation:

```
ANALYST-SOURCED INVESTIGATION CANDIDATE
Source analyst: [name]
Original insight: [what they said, dated, with reasoning — not just conclusion]
Source file: outputs/collection/YYYY-Www-analyst-monitor.md
Why this is novel: [what does this see that our data/synthesis doesn't?]
Proposed investigation: [what would Skill 11 need to research to validate or invalidate this?]
Classification: [likely tactical / likely structural — based on the three classification questions above]
```

This automatically triggers Skill 11 to investigate. No human approval gate — the quality filter is Skill 11's research standards. If Skill 11 can't find quantified structural evidence, the thesis either doesn't get generated (research brief concludes "not viable") or lands as a low-conviction DRAFT. The provenance tag ensures the user can always see where the idea originated.

**Guardrails against analyst-dependency:**
- An analyst saying something doesn't make it true. The investigation must produce independent evidence.
- If Skill 11 research relies primarily on the analyst's own data/claims rather than independent sources, flag it: "Evidence base is thin — primarily sourced from originating analyst."
- Do not generate more than 2 analyst-sourced investigation candidates per week. If the analyst monitor surfaces 5 interesting ideas, pick the 2 with the clearest testable mechanisms. The rest can be noted in the monitor output for future weeks.
- Track analyst-sourced vs. data-sourced thesis origins in the meta block. If analyst-sourced theses consistently outnumber data-sourced ones, the system is drifting from data-driven to opinion-driven — Skill 8 should flag this.

### Tactical Thesis Template

For tactical theses (the default), produce:

```markdown
### THESIS CANDIDATE: [Short descriptive name]
**Status:** DRAFT — Pending review
**Generated:** [Date]
**Source:** Weekly Synthesis [Week reference] OR Analyst-sourced: [analyst name] via [Week reference] analyst monitor
**Provenance:** [data-pattern / analyst-sourced]

**Plain English Summary:**
[One paragraph for a smart non-specialist. What are we betting on, why, what ETFs would we use, and what would make us exit? No jargon. If your non-finance friend couldn't understand this paragraph, rewrite it.]

**Claim:** [One sentence. What is the bet? Be specific — not "equities will go up" but "US large cap growth (QQQ) will underperform US large cap value (VTV) by >5% as the regime shifts from Goldilocks to Overheating." Include the expected time horizon only if the mechanism implies one — some theses resolve in weeks, others play out over a year or more.]

**Mechanism:** [How does this play out? What is the causal chain from macro data to price action? 3-5 sentences tracing the logic step by step. Explain WHY each link in the chain works, not just that it does.]

**Assumptions:** [What has to be true for this thesis to work? List each explicitly and make them testable.]
1. [Assumption 1 — specific, measurable]
2. [Assumption 2]
3. [Assumption 3]

**Consensus view:** [What does the market currently believe? Where is the specific mispricing? Reference positioning data if available.]

**ETF Expression:** Trace the causal chain from the thesis to specific ETFs. Every thesis has first, second, and third-order effects — name the ETF for each.

- **First-order** (obvious, direct exposure): [ETF ticker(s)] — [tilt size] — [why this is the direct play]
- **Second-order** (less obvious, slower to price in): [ETF ticker(s)] — [tilt size] — [what causal link connects this to the thesis? why might the market be slower to see it?]
- **Third-order** (contrarian or defensive): [ETF ticker(s)] — [tilt size] — [what's the non-consensus play or the hedge?]
- **Reduce/Avoid:** [ETF ticker(s) that underperform if this thesis plays out]

Refer to the thematic ETF table in RULES.md for common plays. For themes not in the table, run the ETF lookup script:
```bash
python scripts/etf_lookup.py --theme "[theme keywords]"
```
This searches ~100 liquid ETFs, verifies real price data, and returns ticker + AUM + performance. Only recommend ETFs the script has verified — never guess a ticker.

The non-obvious second/third-order plays are often the better risk/reward because the market prices the first-order effect fastest.

**Trigger to add:** [What specific, measurable data point would increase conviction? e.g., "NFCI crosses above zero for 3 consecutive weeks" or "ISM Manufacturing drops below 48." Explain in plain language why this trigger matters.]

**Kill switch:** [What specific, measurable outcome invalidates this thesis? This is the most important field. If this condition is met, the thesis is dead. No negotiating. Include the plain English meaning: "If oil goes above $100 (meaning the geopolitical situation is getting worse, not better), exit the trade."]

**Time horizon:** [When should this thesis be re-evaluated if neither trigger nor kill switch fires? The horizon should follow from the mechanism, not from a default. A thesis driven by a single policy meeting might resolve in weeks. A thesis about a credit cycle turning might play out over 12-18 months. A structural shift in energy policy could be multi-year. Don't force a short horizon on a long thesis or vice versa. Examples: "Reassess after June Fed meeting", "12 months from generation — credit cycles are slow", "Reassess when US election outcome is known."]

## Analyst Cross-References
[Initially empty. Populated by Function B monitoring step 7 when external analyst insight is relevant to this thesis.]
```

### Generation Standards

- **No fixed limit on thesis count.** Generate as many candidates as the data warrants. Some weeks the data shows five distinct opportunities. Some weeks it shows zero. Don't force candidates to fill a quota, and don't suppress a valid candidate because you've already generated three. Let the data decide. Zero is a valid output — not every week produces a tradeable insight.
- Every thesis must have a clear mechanism, not just a correlation observation
- Kill switches must be specific enough that there's no ambiguity about whether they've been triggered
- Assumptions must be testable against observable data — "the economy will slow" is not testable; "ISM Manufacturing will stay below 50 for 3+ months" is testable
- The claim must be falsifiable. "Things might go down" is not a thesis.
- **Quality over quantity.** One thesis with a rigorous mechanism and specific kill switch is worth more than three with vague logic. If a candidate doesn't survive scrutiny during generation, discard it rather than shipping a weak thesis.
- **Time horizons follow the mechanism.** Do not default to 3-6 months. A policy-driven thesis might resolve in weeks. A structural thesis about demographics, energy transition, or credit cycles might have a 12-24 month horizon. The time horizon is set by the causal chain in the mechanism, not by a convention. Longer theses need monitoring checkpoints (e.g., "12-month thesis, weekly kill switch check, full review triggered by assumption pressure or constraint data changes") but should not be artificially shortened to fit a medium-term template.

### Structural Thesis Template

For structural theses (requires Skill 11 research brief as input), produce:

```markdown
### STRUCTURAL THESIS CANDIDATE: [Short descriptive name]
**Status:** DRAFT — Pending review
**Classification:** Structural
**Generated:** [Date]
**Source:** Structural Research Brief [reference] + Weekly Synthesis [Week reference] OR Analyst-sourced: [analyst name] via [Week reference] analyst monitor
**Provenance:** [data-pattern / analyst-sourced]
**Research Brief:** `outputs/research/STRUCTURAL-[theme-name]-[date].md`

**Plain English Summary:**
[One paragraph for a smart non-specialist. What are we betting on, why, what is the structural reality driving it, what ETFs would we use, and what would make us exit? No jargon.]

**Claim:** [One sentence. What is the bet? Be specific. Include the time horizon derived from the structural constraint — not from convention.]

**Structural Foundation:**
[The physical, economic, or structural reality this thesis rests on. Drawn directly from the Skill 11 research brief. Each claim quantified with source and date. This section answers: why can't the market resolve this quickly?]

- [Binding constraint 1] — [quantified] — [source, date]
- [Binding constraint 2] — [quantified] — [source, date]
- [Binding constraint 3] — [quantified] — [source, date]

**Quantified Causal Chain:**
[The mechanism, but every link carries a number. Not "demand exceeds supply" but "demand growing at X%/yr while supply is constrained by Y-year development timelines, producing a deficit of Z units by [date]." Trace from the structural reality through to the price implication. Each link must explain WHY it works, not just that it does.]

1. [Link 1 — quantified, with causal explanation]
2. [Link 2 — quantified, with causal explanation]
3. [Link 3 — quantified, with causal explanation]
4. [Link 4 — price implication, quantified where possible]

**What We Have To Believe:**
[Independently testable assumptions, drawn from the Skill 11 research brief. Each one stands alone — if any single assumption breaks, the thesis weakens or dies.]

1. [Assumption] — Testable by: [specific observable data point or event]
2. [Assumption] — Testable by: [specific observable data point or event]
3. [Assumption] — Testable by: [specific observable data point or event]
4. [Assumption] — Testable by: [specific observable data point or event]

**Consensus view:** [What does the market currently believe? Where is the specific mispricing? Quantify the gap between current positioning and what the structural picture implies.]

**Contrarian Stress-Test:**
[The strongest case against this thesis, steelmanned. Not a kill switch — this is the structural risk that could weaken the entire causal chain. Attributed to specific analysts or frameworks where possible.]

- Strongest counter-argument: [1-2 paragraphs]
- Key risk 1: [specific, with assessment of likelihood]
- Key risk 2: [specific, with assessment of likelihood]
- Assessment after considering contrarian case: [Does conviction hold? At what level?]

**ETF Expression:** Separate thesis conviction from expression selection from entry timing.

*Thesis conviction:* [High / Medium / Low — based on structural evidence vs. contrarian case]

*Expression:*
- **First-order** (obvious, direct exposure): [ETF ticker(s)] — [tilt size] — [why this is the direct play]
- **Second-order** (less obvious, slower to price in): [ETF ticker(s)] — [tilt size] — [what causal link connects this to the thesis? why might the market be slower to see it?]
- **Third-order** (contrarian or defensive): [ETF ticker(s)] — [tilt size] — [what's the non-consensus play or the hedge?]
- **Reduce/Avoid:** [ETF ticker(s) that underperform if this thesis plays out]

*Entry timing:* [Is the cyclical picture (current regime, positioning) reinforcing or working against the structural thesis right now? Should entry be immediate, scaled, or deferred?]

**Trigger to add:** [What specific, measurable data point would increase conviction?]

**Kill switch:** [What specific, measurable outcome invalidates this thesis? For structural theses, also include a "structural break" condition — what would change the binding constraint itself?]

**Time horizon:** [Derived from the structural constraint. Include monitoring approach for long-duration theses — e.g., "18-month thesis, weekly kill switch check, full structural review triggered by assumption pressure or binding constraint data changes."]

**Monitoring cadence:** Weekly kill switch and assumption status check. Full structural review is data-triggered, not calendar-based.

**Weekly check (same as tactical):** Kill switches, assumption status (INTACT / UNDER PRESSURE / BROKEN), regime alignment.

**Full structural review triggers** — run a complete re-examination of the Structural Foundation, all "What We Have To Believe" assumptions, and the contrarian case when ANY of these occur:
- Any assumption moves from INTACT to UNDER PRESSURE
- A major data release directly impacts a binding constraint (e.g., new supply data, policy change affecting the structural dynamic)
- The macro regime shifts in a way that changes how the structural thesis expresses in markets

**Safety net:** If a structural thesis has been ACTIVE for 6+ months with no trigger firing, run a full review anyway. This is a calendar-based backstop — it catches slow-moving changes that don't cross weekly thresholds individually but may have shifted the picture cumulatively. Be honest about what it is: a hedge against monitoring blind spots, not a data signal.

If a full review reveals material changes to the structural picture, flag for Skill 11 research update.

## Analyst Cross-References
[Initially empty. Populated by Function B monitoring step 7 when external analyst insight is relevant to this thesis.]
```

### Additional Generation Standards for Structural Theses

All standards from the tactical template apply, plus:
- **Requires a Skill 11 research brief.** Do not generate a structural thesis on narrative conviction alone. The quantified research foundation is what makes these theses rigorous.
- **Minimum 3 quantified claims in the Structural Foundation.** Each must have a source and date.
- **Minimum 4 independently testable assumptions in "What We Have To Believe."** Each must specify how it would be tested.
- **The Contrarian Stress-Test must be genuinely argued.** If you can't write a credible paragraph against the thesis, the research is incomplete — go back to Skill 11.
- **Separate conviction from entry timing.** A structural thesis can have high conviction but poor entry timing if the cyclical picture is working against it. Say so explicitly rather than suppressing the thesis or ignoring the timing.

---

## Function B: Monitor Active Theses

### Inputs

Read ALL of the following before monitoring:
- Active thesis files from `outputs/theses/active/`
- Weekly synthesis output (Skill 6) — for regime assessment and cross-asset view
- Analyst themes index (`outputs/collection/analyst-themes.md`) — scan for themes relevant to active theses. If a theme overlaps with a thesis (e.g., analyst focused on "credit complacency" and you have a credit spread thesis), follow the `Detail` link to read the full weekly analyst monitor output for that week's substance. Only read the full weekly file when a theme is relevant — don't read every historical analyst file every week.
- Current week analyst monitor output (Skill 10, `outputs/collection/YYYY-Www-analyst-monitor.md`) — always read the current week's full output for fresh insights.
- Data snapshot — for hard numbers to check assumptions against

### Monitoring Process

For each active thesis, check:

1. **Are the stated assumptions still intact?** Check each one individually against the latest data from the snapshot and synthesis. Mark each as: INTACT / UNDER PRESSURE / BROKEN.
2. **Has any kill switch condition been met?** Be rigorous — if it's met, call it. No "well, it's close but..." If the condition is met, the status is INVALIDATED.
3. **Has any trigger-to-add condition been met?** If yes, flag for potential position increase.
4. **Has the macro regime shifted in a way that changes the thesis?** Cross-reference with the weekly synthesis regime assessment.
5. **Is the time horizon approaching without resolution?** Flag theses approaching their review date.
6. **[Structural theses only] Has a full structural review been triggered?** Structural theses get a weekly kill switch check like everything else. A full structural review fires when: (a) any assumption moves to UNDER PRESSURE, (b) a major data release impacts a binding constraint, (c) the regime shifts in a way that changes thesis expression, or (d) the thesis has been ACTIVE 6+ months without any trigger firing (staleness check). When triggered: re-examine each "What We Have To Believe" assumption against updated data, re-assess the contrarian case, and check whether the binding constraints in the Structural Foundation have changed. If a Skill 11 research update is warranted (new data materially changes the picture), flag it.
7. **Does any external analyst insight directly challenge or refine a thesis parameter?** Cross-reference the analyst monitor output against each thesis's assumptions, kill switches, and mechanism. If an analyst publishes data or a framework that is directly relevant to a thesis parameter — for example, a different threshold for the same variable, or new evidence about the mechanism — flag it as a "Parameter Review" recommendation. Do not automatically change the parameter, but surface the conflict:
   ```
   PARAMETER REVIEW: [Thesis name]
   Current parameter: [e.g., kill switch at $X]
   External insight: [what the analyst said, with date and source]
   Relevance: [why this matters to the thesis]
   Recommendation: [review/adjust/no change — with reasoning]
   ```
   This is not about adopting external views uncritically. It's about ensuring the system doesn't ignore relevant information just because it arrived through a different skill.

   **Write the finding to the thesis file.** When a Parameter Review is generated, append it to the relevant thesis file in `outputs/theses/active/`. Add it under an `## Analyst Cross-References` section at the bottom of the file. If the section doesn't exist yet, create it. Each entry is timestamped and attributed:

   ```markdown
   ## Analyst Cross-References

   ### [Date] — [Analyst name]
   **Parameter reviewed:** [which assumption, kill switch, or mechanism element]
   **External insight:** [what the analyst said — the substance, not a summary of the summary]
   **Source:** [link to weekly analyst monitor file, e.g., outputs/collection/YYYY-Www-analyst-monitor.md]
   **Recommendation at time of review:** [review/adjust/no change — with reasoning]
   **Action taken:** [Pending user review / Parameter adjusted / No change]
   ```

   This ensures the analyst insight travels with the thesis it informed. When a thesis is later reviewed (by Skill 12 for presentation, by the user for decision-making, or by this skill in future weeks), the cross-reference history is right there — not buried in a weekly analyst file from three weeks ago. It also creates a record of how external views influenced (or didn't influence) thesis parameters over time.

   Keep the entries chronological. Don't remove old entries even if the parameter was later adjusted — the history of what was considered and why matters for the self-improvement loop.

### Status Table

```markdown
### ACTIVE THESIS MONITOR — [Date]

| Thesis | Status | Weeks Active | Key Change This Week | Action Required |
|--------|--------|-------------|---------------------|-----------------|
| [Name] | [Tracking/Strengthening/Weakening/INVALIDATED] | [N] | [What changed] | [None/Review/Add/Close] |
```

### Detailed Notes

For each active thesis, produce a paragraph with:
- Specific data references supporting the status assessment
- Each assumption checked individually (INTACT / UNDER PRESSURE / BROKEN)
- Kill switch proximity (how close are we to trigger?)
- Any new information that changes the probability weighting

### Thesis Lifecycle States

```
DRAFT → User reviews → ACTIVE or DISCARD
ACTIVE → Monitored weekly
  → STRENGTHENING (trigger-to-add condition met, consider increasing position)
  → WEAKENING (one or more assumptions under pressure but not broken)
  → INVALIDATED (kill switch triggered — close the position, no exceptions)
  → TIME EXPIRED (review date reached without resolution — reassess or close)
CLOSED → Final status. Record outcome in thesis log.
```

### State Transition Rules

- **ACTIVE → STRENGTHENING:** Trigger-to-add condition met AND all assumptions intact
- **ACTIVE → WEAKENING:** Any assumption moves from INTACT to UNDER PRESSURE
- **ANY → INVALIDATED:** Kill switch condition met. This is automatic. No override.
- **WEAKENING → ACTIVE:** Assumptions recover to INTACT
- **STRENGTHENING → ACTIVE:** Trigger condition was transient and reverted
- **ANY → TIME EXPIRED:** Review date reached. User must decide: renew (with updated parameters) or close.
- **INVALIDATED / TIME EXPIRED → CLOSED:** After user acknowledges and outcome is logged.

### Thesis Log Entry (for closed theses)

```markdown
### CLOSED: [Thesis Name]
**Opened:** [Date]
**Closed:** [Date]
**Duration:** [Weeks]
**Final Status:** [INVALIDATED / TIME EXPIRED / USER CLOSED]
**Exit Reason:** [Specific — which kill switch fired, or why manually closed]
**Outcome:** [What actually happened? Did the thesis play out, get stopped out, or expire?]
**Lessons:** [One sentence: what did this thesis teach about the methodology or the market?]
```

---

## Storage

- New thesis candidates: save to `outputs/theses/active/DRAFT-[thesis-name].md`
- When user activates: rename to `ACTIVE-[thesis-name].md`
- When invalidated/closed: move to `outputs/theses/closed/CLOSED-[thesis-name].md`
- Thesis log: append all closed thesis entries to `outputs/theses/thesis-log.md`
- Weekly monitor output: save with weekly collection outputs

## Meta Block

```yaml
---
meta:
  skill: thesis-generator-monitor
  skill_version: "1.5"
  run_date: "[ISO date]"
  function: [generate/monitor/both]
  theses_monitored: [number]
  theses_generated: [number]
  theses_generated_data_sourced: [number]
  theses_generated_analyst_sourced: [number]
  analyst_investigation_candidates_flagged: [number]
  analyst_investigations_triggered: [number]
  theses_invalidated: [number]
  theses_strengthened: [number]
  theses_weakened: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
