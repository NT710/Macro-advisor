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

Thesis candidates come from three sources: data patterns (primary), external analyst frameworks (secondary), and structural scanner candidates (tertiary). All feed into the same classification and template system.

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

### Source 3: Structural Scanner Candidates

Read `outputs/structural/candidates/` for any advancing candidates from Skill 13 (Structural Scanner). These are domains where the scanner detected a quantitative tension signal, screened it through equilibrium, base rate, and consensus checks, and produced a structured candidate brief.

**How scanner candidates enter the thesis pipeline:**
1. Each candidate file contains a domain, quantified imbalance, binding constraint, bear case inputs, and a recommended investigation depth.
2. ALL scanner candidates are routed to Skill 11 for research. The scanner candidate file IS the investigation brief for Skill 11. The candidate's "recommended investigation depth" (Full / Focused / Quick check) is passed to Skill 11 as a suggestion for how much work to do — but Skill 11 always runs its first-principles framing and contrarian stress-test regardless of depth. No scanner candidate bypasses Skill 11, even if the base rate looks strong — the scanner's own assessment is not a substitute for independent first-principles validation.
3. Scanner candidates always classify as **structural** (by definition — the scanner only flags imbalances with >12-month resolution timelines).

**Deduplication:** Before processing, check whether an existing active thesis or current-week data-pattern candidate already covers the same domain. If the scanner candidate points in the same direction as the existing thesis (e.g., both say energy is supply-constrained), the scanner candidate becomes supporting evidence (add to its External Views section under "Structural Scanner Corroboration"), not a separate investigation. However, if the scanner candidate's reading conflicts with the existing thesis (e.g., thesis says supply-constrained but scanner detects demand destruction signals, or scanner flags a different binding constraint), flag the conflict explicitly: "SCANNER-THESIS CONFLICT: [domain] — existing thesis assumes [X], scanner detects [Y]." This conflict is a high-value signal and should trigger a review of the existing thesis's assumptions, not silent absorption.

**Provenance:** Scanner-originated theses carry `provenance: structural-scanner` through the entire pipeline. This is distinct from `data-pattern` and `analyst-sourced` to enable separate performance tracking by Skill 8.

**Combined investigation cap:** In any single weekly run, no more than 5 total investigation candidates should be sent to Skill 11 (across all three sources: data-pattern + analyst-sourced + scanner). If the combined count exceeds 5, prioritize by: (1) size of quantified gap or strength of mechanism, (2) novelty vs. existing thesis coverage, (3) distance from consensus. Defer the rest to next cycle.

### Tactical Thesis Template

For tactical theses (the default), produce:

```markdown
### THESIS CANDIDATE: [Short descriptive name]
**Status:** DRAFT — Pending review
**Generated:** [Date]
**Updated:** [Date — set to Generated date initially. Skill 7 Function B updates this each week the thesis is monitored.]
**Source:** Weekly Synthesis [Week reference] OR Analyst-sourced: [analyst name] via [Week reference] analyst monitor
**Provenance:** [data-pattern / analyst-sourced]

## Summary
[One paragraph for a smart non-specialist. What are we betting on, why, what ETFs would we use, and what would make us exit? No jargon. If your non-finance friend couldn't understand this paragraph, rewrite it.]

## The Bet
[One sentence. What is the bet? Be specific — not "equities will go up" but "US large cap growth (QQQ) will underperform US large cap value (VTV) by >5% as the regime shifts from Goldilocks to Overheating." Include the expected time horizon only if the mechanism implies one — some theses resolve in weeks, others play out over a year or more.]

## Why It Works

### Mechanism
[How does this play out? What is the causal chain from macro data to price action? 3-5 sentences tracing the logic step by step. Explain WHY each link in the chain works, not just that it does.]

## What Has To Stay True
[What has to be true for this thesis to work? Each assumption must be independently testable — name the specific data point, threshold, or event that would confirm or deny it. Use the exact format below.]

1. [Assumption] — Testable by: [specific observable data point, threshold, or event]
2. [Assumption] — Testable by: [specific observable data point, threshold, or event]
3. [Assumption] — Testable by: [specific observable data point, threshold, or event]

For DRAFT theses where one assumption's testable criterion is genuinely unclear (emerging pattern, no established data series yet), a single placeholder is permitted: `— Testable by: [to be specified — monitor for [specific data release/event] that would clarify]`. No more than one placeholder per thesis. Any thesis promoted from DRAFT to ACTIVE must have all placeholders resolved with concrete testable criteria.

## Where The Market Stands
[What does the market currently believe? Where is the specific mispricing? Reference positioning data if available — CFTC COT readings, ETF flow trends, fund allocation data, speculator positioning. Show both what people think and where money actually sits.]

**Conviction:** [High / Medium / Low]
Conviction is an honest assessment of how much evidence supports this thesis RIGHT NOW — not how exciting the thesis is or how large the potential payoff. Score it on two primary dimensions and one veto gate:

**Primary dimensions (both must score well for High):**
1. **Mechanism clarity:** Is the causal chain specific and testable? "Specific" means each link names a measurable indicator, a threshold, and an expected direction. "Inflation expectations rise above 3%" is specific. "Inflation worries grow" is not. If you can't point to the data series that would confirm or deny each link, mechanism clarity is Low.
2. **Data support:** How many of the stated assumptions are currently supported by observable data? Count them. If ≥75% of assumptions are currently intact, data support is Strong. If 50-75%, Moderate. Below 50%, Weak. Forward-looking assumptions count as unsupported until their trigger fires.

**Veto gate:**
3. **Consensus check:** Is this thesis already the market consensus? If the consensus view section reveals broad agreement with this thesis, conviction is **capped at Medium** regardless of mechanism and data scores. A consensus position can be correct, but the edge is priced in — calling it High conviction overstates the information advantage. This is a ceiling, not a positive scoring dimension.

**Scoring:**
- **High** = Mechanism clarity is specific AND data support is Strong AND not capped by consensus veto.
- **Medium** = Mechanism is specific but data support is only Moderate, OR conviction is capped by consensus veto, OR mechanism has one weak link.
- **Low** = Data support is Weak, OR mechanism relies on narrative rather than measurable links, OR kill switch is already within 20% of firing threshold.

If you find yourself wanting to call something High because the narrative is compelling despite Moderate data support, that's Medium. The narrative is not evidence.

## The Trade

### What to buy
Trace the causal chain from the thesis to specific ETFs. Every thesis has first, second, and third-order effects — name the ETF for each.

- **First-order** (obvious, direct exposure): [ETF ticker(s)] — [tilt size] — [why this is the direct play]
- **Second-order** (less obvious, slower to price in): [ETF ticker(s)] — [tilt size] — [what causal link connects this to the thesis? why might the market be slower to see it?]
- **Third-order** (contrarian or defensive): [ETF ticker(s)] — [tilt size] — [what's the non-consensus play or the hedge?]
- **Reduce/Avoid:** [ETF ticker(s) that underperform if this thesis plays out]

Refer to the thematic ETF table in RULES.md for common plays. For themes not in the table, run the ETF lookup script:
```bash
python scripts/etf_lookup.py --theme "[theme keywords]"
```
This searches ~160 curated ETFs (Layer 1) plus live Yahoo Finance discovery (Layer 2), verifies real price data, and returns ticker + AUM + performance. Only recommend ETFs the script has verified — never guess a ticker.

**Counter-thesis ETF search:** After running the ETF lookup for the thesis direction, run a second search for the **opposing** thesis. If the thesis is "long euro," also search for "short euro" or "dollar strength." If the thesis is "long duration," also search for "short duration" or "rising rates." This forces you to see what the other side of the trade looks like — who's on it, how liquid it is, and what the recent performance tells you about conviction on that side. State in the thesis what the counter-expression would be and why you believe it's wrong. If you can't articulate why the opposing trade is wrong, your thesis isn't ready.

**Entry timing check:** Review the `month_change_pct` across your thesis-aligned ETF results. If the move has already happened (≥80% of results moved strongly in your thesis direction), note this in the thesis as a timing consideration. This is not a reason to kill the thesis — but it is a reason to assess whether you're early or late, and to size accordingly.

The non-obvious second/third-order plays are often the better risk/reward because the market prices the first-order effect fastest.

### When to buy more
[What specific, measurable data point would increase conviction? e.g., "NFCI crosses above zero for 3 consecutive weeks" or "ISM Manufacturing drops below 48." Explain in plain language why this trigger matters.]

### When to get out
[What specific, measurable outcome invalidates this thesis? This is the most important field. If this condition is met, the thesis is dead. No negotiating. Include the plain English meaning: "If oil goes above $100 (meaning the geopolitical situation is getting worse, not better), exit the trade."]

### How long
[When should this thesis be re-evaluated if neither trigger nor kill switch fires? The horizon should follow from the mechanism, not from a default. A thesis driven by a single policy meeting might resolve in weeks. A thesis about a credit cycle turning might play out over 12-18 months. A structural shift in energy policy could be multi-year. Don't force a short horizon on a long thesis or vice versa. Examples: "Reassess after June Fed meeting", "12 months from generation — credit cycles are slow", "Reassess when US election outcome is known."]

## External Views
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

### Pre-Write Verification (tactical theses)

After drafting a tactical thesis but **before writing it to disk**, run this checklist mechanically. Each item is a binary pass/fail. If any item fails, fix the draft before writing.

1. **Every assumption testable?** Does each item under "What Has To Stay True" include a "Testable by:" clause naming a specific data point, threshold, or event? A single `[to be specified]` placeholder is permitted for DRAFT theses (see template note above), but no more than one per thesis. FAIL if any assumption lacks a testable criterion beyond the one allowed placeholder.
2. **Kill switch specific?** Is the "When to get out" condition specific enough that there's no ambiguity about whether it's been triggered? FAIL if it uses vague language ("if the economy weakens") rather than a measurable threshold ("ISM Manufacturing drops below 48 for 2 consecutive months").
3. **Mechanism traceable?** Does each link in the Mechanism section name a measurable indicator or observable event? FAIL if any link is pure narrative without a data reference.

If all three pass, write the file. If any fail, the fix is usually a 1-2 sentence edit — not a thesis rewrite.

---

### Structural Thesis Template

For structural theses (requires Skill 11 research brief as input), produce:

```markdown
### STRUCTURAL THESIS CANDIDATE: [Short descriptive name]
**Status:** DRAFT — Pending review
**Classification:** Structural
**Generated:** [Date]
**Updated:** [Date — set to Generated date initially. Skill 7 Function B updates this each week the thesis is monitored.]
**Source:** Structural Research Brief [reference] + Weekly Synthesis [Week reference] OR Analyst-sourced: [analyst name] via [Week reference] analyst monitor
**Provenance:** [data-pattern / analyst-sourced]
**Research Brief:** `outputs/research/STRUCTURAL-[theme-name]-[date].md`

## Summary
[One paragraph for a smart non-specialist. What are we betting on, why, what is the structural reality driving it, what ETFs would we use, and what would make us exit? No jargon.]

## The Bet
[One sentence. What is the bet? Be specific. Include the time horizon derived from the structural constraint — not from convention.]

## Why It Works

### What Can't Change
[The physical, economic, or structural reality this thesis rests on. Drawn directly from the Skill 11 research brief. Each claim quantified with source and date. This section answers: why can't the market resolve this quickly?]

- [Binding constraint 1] — [quantified] — [source, date]
- [Binding constraint 2] — [quantified] — [source, date]
- [Binding constraint 3] — [quantified] — [source, date]

### Mechanism
[The mechanism, but every link carries a number. Not "demand exceeds supply" but "demand growing at X%/yr while supply is constrained by Y-year development timelines, producing a deficit of Z units by [date]." Trace from the structural reality through to the price implication. Each link must explain WHY it works, not just that it does.]

1. [Link 1 — quantified, with causal explanation]
2. [Link 2 — quantified, with causal explanation]
3. [Link 3 — quantified, with causal explanation]
4. [Link 4 — price implication, quantified where possible]

## What Has To Stay True
[Independently testable assumptions, drawn from the Skill 11 research brief. Each one stands alone — if any single assumption breaks, the thesis weakens or dies.]

1. [Assumption] — Testable by: [specific observable data point or event]
2. [Assumption] — Testable by: [specific observable data point or event]
3. [Assumption] — Testable by: [specific observable data point or event]
4. [Assumption] — Testable by: [specific observable data point or event]

## Where The Market Stands
[What does the market currently believe? Where is the specific mispricing? Quantify the gap between current positioning and what the structural picture implies. Include positioning data: CFTC COT readings, investor allocation percentages, ETF flow trends, speculator positioning, capital flow data from the research brief.]

## What Could Break It
[The strongest case against this thesis, steelmanned. Not a kill switch — this is the structural risk that could weaken the entire causal chain. Attributed to specific analysts or frameworks where possible.]

- Strongest counter-argument: [1-2 paragraphs]
- Key risk 1: [specific, with assessment of likelihood]
- Key risk 2: [specific, with assessment of likelihood]
- Assessment after considering contrarian case: [Does conviction hold? At what level?]

## The Trade

*Thesis conviction:* [High / Medium / Low — based on structural evidence vs. contrarian case]

### What to buy
- **First-order** (obvious, direct exposure): [ETF ticker(s)] — [tilt size] — [why this is the direct play]
- **Second-order** (less obvious, slower to price in): [ETF ticker(s)] — [tilt size] — [what causal link connects this to the thesis? why might the market be slower to see it?]
- **Third-order** (contrarian or defensive): [ETF ticker(s)] — [tilt size] — [what's the non-consensus play or the hedge?]
- **Reduce/Avoid:** [ETF ticker(s) that underperform if this thesis plays out]

### When to buy
[Is the cyclical picture (current regime, positioning) reinforcing or working against the structural thesis right now? Should entry be immediate, scaled, or deferred? Provide specific scaling plan if applicable.]

### When to buy more
[What specific, measurable data point would increase conviction?]

### When to get out
[What specific, measurable outcome invalidates this thesis? For structural theses, also include a "structural break" condition — what would change the binding constraint itself?]

### How long
[Derived from the structural constraint. Include monitoring approach for long-duration theses — e.g., "18-month thesis, weekly kill switch check, full structural review triggered by assumption pressure or binding constraint data changes."]

**Monitoring cadence:** Weekly kill switch and assumption status check. Full structural review is data-triggered, not calendar-based.

**Weekly check (same as tactical):** Kill switches, assumption status (INTACT / UNDER PRESSURE / BROKEN), regime alignment.

**Full structural review triggers** — run a complete re-examination of the "What Can't Change" section, all "What Has To Stay True" assumptions, and the "What Could Break It" case when ANY of these occur:
- Any assumption moves from INTACT to UNDER PRESSURE
- A major data release directly impacts a binding constraint (e.g., new supply data, policy change affecting the structural dynamic)
- The macro regime shifts in a way that changes how the structural thesis expresses in markets

**Safety net:** If a structural thesis has been ACTIVE for 6+ months with no trigger firing, run a full review anyway. This is a calendar-based backstop — it catches slow-moving changes that don't cross weekly thresholds individually but may have shifted the picture cumulatively. Be honest about what it is: a hedge against monitoring blind spots, not a data signal.

If a full review reveals material changes to the structural picture, flag for Skill 11 research update.

## External Views
[Initially empty. Populated by Function B monitoring step 7 when external analyst insight is relevant to this thesis.]
```

### Additional Generation Standards for Structural Theses

All standards from the tactical template apply, plus:
- **Requires a Skill 11 research brief.** Do not generate a structural thesis on narrative conviction alone. The quantified research foundation is what makes these theses rigorous.
- **Minimum 3 quantified claims in "What Can't Change."** Each must have a source and date.
- **Minimum 4 independently testable assumptions in "What Has To Stay True."** Each must specify how it would be tested.
- **"What Could Break It" must be genuinely argued.** If you can't write a credible paragraph against the thesis, the research is incomplete — go back to Skill 11.
- **Separate conviction from entry timing.** A structural thesis can have high conviction but poor entry timing if the cyclical picture is working against it. Say so explicitly rather than suppressing the thesis or ignoring the timing.
- **Carry forward sampling bias and evidence independence warnings.** If the Skill 11 research brief flags that the evidence base has sampling bias (e.g., multiple analysts sharing the same intellectual framework, all data sourced from one industry group, or geographically concentrated evidence), that warning must appear in the thesis body — not just implicitly in the conviction level. Specifically: if the brief rates evidence independence as "Medium" or lower, or explicitly names a sampling bias, the thesis must state the limitation in plain language — add an "**Evidence Independence:**" line directly below the "What Can't Change" subsection. Do not present correlated sources as independent validation. Two analysts who share a framework are one voice, not two — say so.
- **Surface internal data contradictions — do not resolve them silently.** When the research brief contains data points that contradict each other, or when the brief's findings conflict with other skills' assessments (e.g., a Skill 2 liquidity reading that runs counter to the thesis direction), the thesis must acknowledge the contradiction explicitly. State both sides: "[Source A] indicates [X], while [Source B / Skill N] shows [Y]. These are in tension." Then assess which you weight more heavily and why. A thesis that filters out its own system's contrary data to present a cleaner narrative is not a thesis — it's advocacy.
- **Time horizon must be internally consistent.** Cross-check the "How long" subsection, the "The Bet" sentence, and the monitoring cadence before finalizing. If the structural constraint implies a 2-5 year horizon, the bet cannot reference a different timeframe, and the monitoring cadence cannot default to tactical-length language (e.g., "18-month thesis" when the mechanism is multi-year). All three must agree. If they disagree, reconcile them — don't publish the inconsistency.

### Pre-Write Verification (structural theses only)

After drafting a structural thesis but **before writing it to disk**, re-read the Skill 11 research brief one more time alongside the draft. Run this checklist mechanically — each item is a binary pass/fail. If any item fails, fix the draft before writing.

1. **Bet bounded by brief?** Does the thesis's bet (magnitude and direction) fall within what the research brief's conviction assessment supports? If the brief concluded "Low conviction" for a specific target, the bet cannot include that target in its range. FAIL if the bet's upper or lower bound exceeds what the brief explicitly supported.

2. **Evidence independence stated?** If the brief rates evidence independence below "High" or flags any sampling bias, does the thesis contain an explicit `**Evidence Independence:**` disclosure? FAIL if the limitation exists in the brief but is absent from the thesis.

3. **Internal contradictions surfaced?** Does the thesis acknowledge every data conflict identified in the brief — including conflicts between the brief's sources and other skills' assessments? FAIL if the thesis presents a clean narrative when the brief contained unresolved tensions.

4. **Time horizon consistent?** Do "The Bet", "How long", and the monitoring cadence all reference the same timeframe? FAIL if any two disagree.

5. **Contrarian case not weakened?** Compare the thesis's "What Could Break It" against the brief's "Quantified contrarian claims" table. Does the thesis give the bear case equal or greater weight than the brief did? FAIL if the thesis softened, omitted, or downplayed any contrarian claim that the brief presented with evidence.

If all five pass, write the file. If any fail, the fix is usually a 1-2 sentence edit — not a thesis rewrite. The point is to catch drift between what the research found and what the thesis asserts.

This checklist also applies to the JSON sidecar: verify the sidecar's `conviction`, `the_bet`, `the_trade.how_long`, and `what_could_break_it` fields match the corrected draft, not the pre-verification version.

---

## Function B: Monitor Active Theses

### Inputs

Read ALL of the following before monitoring:
- Active thesis files from `outputs/theses/active/` — **list every file in this directory.** This is the authoritative set of theses to monitor. Theses may have been created outside the weekly chain (via `/investigate-theme` or `/structural-scan`), so do not rely on Function A's output or prior weeks' monitor output as the thesis list. The directory listing IS the list.
- Weekly synthesis output (Skill 6) — for regime assessment and cross-asset view
- Analyst themes index (`outputs/collection/analyst-themes.md`) — scan for themes relevant to active theses. If a theme overlaps with a thesis (e.g., analyst focused on "credit complacency" and you have a credit spread thesis), follow the `Detail` link to read the full weekly analyst monitor output for that week's substance. Only read the full weekly file when a theme is relevant — don't read every historical analyst file every week.
- Current week analyst monitor output (Skill 10, `outputs/collection/YYYY-Www-analyst-monitor.md`) — always read the current week's full output for fresh insights.
- Data snapshot — for hard numbers to check assumptions against
- **[Structural theses only — read on demand, not every week]** Skill 11 research briefs from `outputs/research/`. Each structural thesis references its brief via the `**Research Brief:**` field. Do NOT read these every week — only when a full structural review is triggered (step 6 below). The brief contains the original supply-demand quantification, binding constraint evidence, and contrarian claims that the thesis was built from.

### Reconciliation Step (run before monitoring)

List all files in `outputs/theses/active/`. Compare against the theses mentioned in Function A's output (if Function A ran this cycle). Any thesis file that exists on disk but was NOT generated or mentioned by Function A this cycle is an **externally-created thesis** — it was created by `/investigate-theme`, `/structural-scan`, or a prior week's chain. These must be monitored with the same process as chain-generated theses. Flag each in the monitor output:

```
NEW TO MONITOR: [Thesis name] — created by [investigate-theme / structural-scan / prior week], first monitoring cycle.
```

This ensures no thesis falls through the cracks regardless of how it entered the system.

### Format Migration (run after reconciliation, before monitoring)

While reading each thesis file, check whether it uses old-format section headings. If any of the following headings are found, rewrite them to the current format. Content stays identical — only the heading text changes.

| Old heading | Current heading |
|---|---|
| `## Plain English Summary` | `## Summary` |
| `## Claim` | `## The Bet` |
| `## Structural Foundation` | `### What Can't Change` (under `## Why It Works`) |
| `## Quantified Causal Chain` | `### Mechanism` (under `## Why It Works`) |
| `## Assumptions` | `## What Has To Stay True` |
| `## Consensus view` or `## Consensus View` | `## Where The Market Stands` |
| `## Contrarian Stress-Test` | `## What Could Break It` |
| `## ETF Expression` | `### What to buy` (under `## The Trade`) |
| `## Trigger to add` | `### When to buy more` (under `## The Trade`) |
| `## Entry timing` | `### When to buy` (under `## The Trade`) |
| `## Kill switch` | `### When to get out` (under `## The Trade`) |
| `## Time horizon` | `### How long` (under `## The Trade`) |
| `## Analyst Cross-References` | `## External Views` |

For structural theses with old format: wrap "What Can't Change" and "Mechanism" under a new `## Why It Works` parent heading. Wrap trade subsections under a new `## The Trade` parent heading.

If a companion JSON sidecar exists with old key names (`causal_chain`, `structural_foundation`, `assumptions`, `etf_expression`, `kill_switch`, `trigger_to_add`, `time_horizon`, `plain_english_summary`, `claim`, `consensus_view`, `contrarian_stress_test`), rewrite it using the current key names (`mechanism`, `what_cant_change`, `what_has_to_stay_true`, nested `the_trade` object, `summary`, `the_bet`, `where_the_market_stands`, `what_could_break_it`). Remove any `_legacy_backward_compat` block.

Flag each migrated file in the monitor output:

```
FORMAT MIGRATED: [Thesis name] — headings updated to current template format.
```

This is a one-time migration per file. Once a file has current-format headings, this step is a no-op.

### Monitoring Process

For each thesis in `outputs/theses/active/` (the full directory listing, not a subset), check:

1. **Are the stated assumptions still intact?** Check each one individually against the latest data from the snapshot and synthesis. Mark each as: INTACT / UNDER PRESSURE / BROKEN.
2. **Has any kill switch condition been met?** Be rigorous — if it's met, call it. No "well, it's close but..." If the condition is met, the status is INVALIDATED.
3. **Has any trigger-to-add condition been met?** If yes, flag for potential position increase.
4. **Has the macro regime shifted in a way that changes the thesis?** Cross-reference with the weekly synthesis regime assessment.
5. **Is the time horizon approaching without resolution?** Flag theses approaching their review date.
6. **[Structural theses only] Has a full structural review been triggered?** Structural theses get a weekly kill switch check like everything else. A full structural review fires when: (a) any assumption moves to UNDER PRESSURE, (b) a major data release impacts a binding constraint, (c) the regime shifts in a way that changes thesis expression, or (d) the thesis has been ACTIVE 6+ months without any trigger firing (staleness check). When triggered:
   - **Read the original Skill 11 research brief.** Follow the `**Research Brief:**` path in the thesis file to `outputs/research/`. The brief contains the full supply-demand quantification, binding constraint evidence, and contrarian claims table that the thesis was built from. Use this as the evidentiary baseline — not as confirmation that the thesis is still correct. The question is: have the numbers in the brief changed?
   - **Start with the contrarian case — before re-examining bull assumptions.** The brief's "Quantified contrarian claims" table lists specific bear case data points with sources and dates. Check whether any of those claims have strengthened since the brief was written. Then ask: what new bear arguments have emerged since the brief was written that aren't in the original contrarian table? Technology shifts, policy changes, new supply sources, demand destruction evidence — anything that weakens the structural thesis but postdates the research. The brief can only contain the contrarian case as it stood at generation time. A thesis active for 6+ months may face risks the brief never anticipated.
   - Re-examine each "What Has To Stay True" assumption against updated data. Check whether the specific quantified claims in the research brief still hold — not just whether the thesis's condensed assumption text "feels" intact.
   - Check whether the binding constraints in "What Can't Change" have changed. The brief's "Binding Constraints" section has the original numbers — compare against current data.
   - If a Skill 11 research update is warranted (new data materially changes the picture), flag it. Be specific: "Research brief from [date] assumes [X]. Current data shows [Y]. Recommend Skill 11 re-investigation."
7. **Does any external analyst insight directly challenge or refine a thesis parameter?** Cross-reference the analyst monitor output against each thesis's assumptions, kill switches, and mechanism. If an analyst publishes data or a framework that is directly relevant to a thesis parameter — for example, a different threshold for the same variable, or new evidence about the mechanism — flag it as a "Parameter Review" recommendation. Do not automatically change the parameter, but surface the conflict:
   ```
   PARAMETER REVIEW: [Thesis name]
   Current parameter: [e.g., kill switch at $X]
   External insight: [what the analyst said, with date and source]
   Relevance: [why this matters to the thesis]
   Recommendation: [review/adjust/no change — with reasoning]
   ```
   This is not about adopting external views uncritically. It's about ensuring the system doesn't ignore relevant information just because it arrived through a different skill.

   **Write the finding to the thesis file.** When a Parameter Review is generated, append it to the relevant thesis file in `outputs/theses/active/`. Add it under an `## External Views` section at the bottom of the file. If the section doesn't exist yet, create it. Each entry is timestamped and attributed:

   ```markdown
   ## External Views

   ### [Date] — [Analyst name]
   **Parameter reviewed:** [which assumption, kill switch, or mechanism element]
   **External insight:** [what the analyst said — the substance, not a summary of the summary]
   **Source:** [link to weekly analyst monitor file, e.g., outputs/collection/YYYY-Www-analyst-monitor.md]
   **Recommendation at time of review:** [review/adjust/no change — with reasoning]
   **Action taken:** [Pending user review / Parameter adjusted / No change]
   ```

   This ensures the analyst insight travels with the thesis it informed. When a thesis is later reviewed (by Skill 12 for presentation, by the user for decision-making, or by this skill in future weeks), the cross-reference history is right there — not buried in a weekly analyst file from three weeks ago. It also creates a record of how external views influenced (or didn't influence) thesis parameters over time.

   Keep the entries chronological. Don't remove old entries even if the parameter was later adjusted — the history of what was considered and why matters for the self-improvement loop.

8. **Write monitoring results back to the thesis file.** After monitoring each thesis, update the file with three changes:

   a. **Update the `**Updated:**` field** to the current date. This stamps when the thesis was last reviewed.

   b. **Update the "What Has To Stay True" section** with the current status of each assumption. For each numbered item, append the status assessment to the end of the existing line:

      `1. [Assumption] — Testable by: [criterion]. Current status: INTACT (one-sentence evidence)`
      `2. [Assumption] — Testable by: [criterion]. Current status: UNDER PRESSURE (one-sentence evidence)`
      `3. [Assumption] — Testable by: [criterion]. Current status: BROKEN (one-sentence evidence)`

      **Write-back rules (to prevent file corruption):**
      - Append `. Current status: [STATUS] ([evidence])` to the end of each existing numbered item. If a status already exists from a prior week, replace only the status portion — not the assumption text or testable criterion.
      - Do NOT rewrite the assumption text itself. Do NOT change the numbering. Do NOT add or remove items.
      - Only modify lines within the "What Has To Stay True" section. Do not touch any other section of the thesis file.

      **One-time backfill for legacy theses:** If an assumption lacks a "Testable by:" clause (generated before this requirement), add one based on the data you used to assess the assumption this week. Format: insert `— Testable by: [criterion]` before the status append. This is a one-time enrichment — once a testable criterion exists, maintain it going forward. Do not invent vague criteria; if you genuinely cannot identify a testable data point for an assumption, note: `— Testable by: [manual review required — no automated data source identified]`.

   c. **Update or create the JSON sidecar.** If a companion JSON sidecar exists (e.g., `ACTIVE-thesis-name-data.json` alongside `ACTIVE-thesis-name.md`), update it. If no sidecar exists, create one following the schema defined in the "Structured Data Sidecar" section below. The dashboard reads JSON sidecars as the primary structured data source — without a sidecar, the dashboard falls back to markdown parsing, which is fragile. For each assumption in `what_has_to_stay_true`, set or update the `status` field to `"INTACT"`, `"UNDER PRESSURE"`, or `"BROKEN"`, and add a `status_evidence` field with the one-sentence evidence. Also set `testable_by` for each assumption. Update the top-level `updated` field to the current date.

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
- Kill switch proximity (how close are we to trigger? If within 20% of the firing threshold, flag this explicitly and downgrade conviction to Low if not already)
- Any new information that changes the probability weighting
- Conviction re-assessment: has conviction changed since generation? If data support has weakened or consensus has shifted, state the new conviction level explicitly. Conviction is not set-and-forget — it updates with the data.

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

## Structured Data Sidecar (thesis-name-data.json)

**After writing the markdown thesis file, also write a companion JSON file** alongside it. For example, `ACTIVE-structural-grid-bottleneck.md` gets `ACTIVE-structural-grid-bottleneck-data.json`. This file is the machine-readable source of truth for the dashboard. It eliminates the need for the dashboard generator to parse markdown tables.

The markdown file continues to be the human-readable research note. The JSON is the stable contract for structured data.

```json
{
  "name": "Structural Grid Bottleneck",
  "status": "ACTIVE",
  "classification": "structural",
  "generated": "2026-03-22",
  "updated": "2026-03-25",
  "provenance": "data-pattern",
  "conviction": "High",

  "summary": "[The full summary paragraph]",
  "the_bet": "[The one-sentence bet]",

  "what_cant_change": [
    {
      "constraint": "Transformer manufacturing capacity deficit",
      "quantified": "30% deficit, new factory capacity not online until 2027",
      "source": "Wood Mackenzie"
    }
  ],

  "mechanism": [
    {
      "step": 1,
      "link": "Data center demand is growing at infrastructure speed, but supply is constrained at regulatory speed.",
      "quantified": "Data center power consumption: 224 TWh in 2025 (5.2% of US demand), projected to reach 292 TWh in 2026 (6.5%) and 371 TWh in 2027 (8.0%). Growth rate ~35% annually.",
      "source": "McKinsey 2025; EIA 2025"
    }
  ],

  "what_has_to_stay_true": [
    {
      "text": "Data center power demand continues growing at 25%+ annually for 3+ years",
      "testable_by": "quarterly data center construction starts, EIA electricity consumption data, hyperscaler capex announcements",
      "current_status_detail": "McKinsey 3.5x by 2030, EIA +3% for 2027",
      "status": "INTACT"
    }
  ],

  "where_the_market_stands": "[Market consensus + positioning data paragraph]",

  "what_could_break_it": {
    "strongest_counter": "[The steelmanned counter-argument]",
    "key_risks": [
      {"risk": "AI efficiency gains compress demand growth to <15% annually", "probability": "30-40%"},
      {"risk": "Off-grid generation absorbs >30% of incremental data center demand", "probability": "25-35%"}
    ],
    "post_test_conviction": "High"
  },

  "the_trade": {
    "what_to_buy": {
      "first_order": [{"ticker": "XLUS.SW", "size": "Core (3-5%)", "rationale": "Diversified regulated utility exposure"}],
      "second_order": [{"ticker": "GRID", "size": "Satellite (1-2%)", "rationale": "Grid infrastructure pure-play"}],
      "third_order": [],
      "reduce_avoid": [{"ticker": "CSNDX.SW", "rationale": "Long-duration growth vulnerable if grid constraints hit data center buildout"}]
    },
    "when_to_buy": "[Entry timing — structural only, null for tactical]",
    "when_to_buy_more": "PJM capacity auction clears above $350/MW-day",
    "when_to_get_out": "FERC interconnection reform reduces queue to <2 years AND transformer deficit narrows below 5%",
    "how_long": "2-5 yr"
  },

}
```

**Rules:**
- The JSON must contain **all** structured data from the thesis — "what_has_to_stay_true", "mechanism", "what_cant_change", "the_trade". Full text, never truncated.
- Status values for assumptions: `INTACT`, `DEVELOPING`, `UNDER PRESSURE`, `WEAKENING`, `STRENGTHENING`, `WATCH`, `BROKEN`, `INVALIDATED`, `FAILED`.
- Tactical theses omit `what_cant_change` and `what_could_break_it` (set to `null`). Tactical theses also omit `the_trade.when_to_buy` (set to `null`).
- For tactical theses, `what_has_to_stay_true` uses the simpler format (no `testable_by` if not specified in the markdown — set to `""`).
- When Function B (monitor) updates a thesis, update both the markdown and the JSON sidecar. The JSON `updated` field and assumption `status` values must stay in sync with the markdown.
- The dashboard generator reads the JSON when present, falling back to markdown parsing for files without a sidecar.

## Meta Block

```yaml
---
meta:
  skill: thesis-generator-monitor
  skill_version: "1.7"
  run_date: "[ISO date]"
  function: [generate/monitor/both]
  theses_monitored: [number]
  theses_generated: [number]
  theses_generated_data_sourced: [number]
  theses_generated_analyst_sourced: [number]
  theses_generated_scanner_sourced: [number]
  analyst_investigation_candidates_flagged: [number]
  scanner_candidates_processed: [number]
  scanner_candidates_sent_to_skill11: [number]
  scanner_candidates_deduplicated: [number]
  total_investigations_triggered: [number]
  theses_invalidated: [number]
  theses_strengthened: [number]
  theses_weakened: [number]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
