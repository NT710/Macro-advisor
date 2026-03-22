# Skill 11: Structural Research

## Objective

Run first-principles research on structural macro themes before they become theses. This skill produces an internal research brief — not a user-facing document — that feeds Skill 7's expanded structural thesis template. It exists because structural theses (multi-quarter to multi-year) require a depth of analysis that weekly data pattern-matching cannot provide.

## When to Invoke

This skill fires in four ways:

1. **Flagged by Skill 7 from data patterns.** During thesis generation, if a pattern involves physical constraints, supply-side bottlenecks, multi-year cycles, or structural market dislocations, Skill 7 flags it: "This pattern warrants structural research before thesis generation. Invoke Skill 11."
2. **Flagged by Skill 7 from analyst-sourced candidates.** When Skill 7 Function A identifies an external analyst framework or structural view that isn't captured by an existing thesis or the weekly synthesis, it flags an investigation candidate that auto-triggers this skill. The analyst's view is the starting point for research, not the conclusion — this skill independently validates or invalidates the analyst's framework.
3. **Flagged by Skill 7 from structural scanner candidates.** When Skill 13 (Structural Scanner) advances a domain through its Phase 2 screening, it writes a candidate brief to `outputs/structural/candidates/`. Skill 7 reads these candidates and routes ones requiring full research to this skill. The scanner candidate file contains the quantified imbalance, base rate evidence from historical analogues, and bear case inputs — use these as the starting point for Phase 1 framing, not as conclusions. The scanner's Phase 2 subagent already did base-rate research; this skill adds the first-principles depth (binding constraints, supply-demand quantification, steelmanned contrarian case) that the scanner doesn't provide.
4. **Manual invocation.** The user identifies a structural theme worth investigating. No weekly chain dependency required.

This skill does NOT run weekly. Most weeks produce zero structural research briefs. That's correct — structural themes emerge infrequently.

---

## Data Access

Skill 11 has access to three data sources, checked in this order:

### 1. Existing data snapshot (read first)
Read `outputs/data/latest-snapshot.json` and `outputs/data/latest-data-full.json`. The weekly snapshot contains 5 years of FRED and Yahoo Finance data for the system's core series. Check here first — the data you need may already exist.

### 2. On-demand FRED pulls (if snapshot doesn't cover it)
If the investigation requires a FRED series not in the weekly snapshot, pull it directly using the data collector's targeted mode:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/research-temp/ --series "SERIES1,SERIES2" --mode historical
```
Read the FRED API key from `config/user-config.json`. The `--series` flag accepts comma-separated FRED series IDs (e.g., `"FYFSD,FGEXPND,A091RC1Q027SBEA"` for fiscal deficit, federal expenditure, interest payments). It pulls only those series (no Yahoo, no derived metrics) and saves to the specified output directory. Rate limiting is handled automatically with retry and backoff.

On-demand pulls are saved to `outputs/data/research-temp/` — NOT to the main snapshot. The weekly snapshot stays Skill 0's domain. Output files are named `research-YYYY-MM-DD-targeted.json`.

**Log every additional series pulled** in the research brief's meta block under `additional_series_pulled`. If the same series gets pulled across multiple investigations, that's a signal to Skill 8 that it should be added to the permanent weekly collection.

### 3. On-demand Yahoo Finance / ETF price data
Use the ETF lookup script for price-based historical research:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/etf_lookup.py --theme "[keywords]"
```
For specific ticker history not covered by the lookup script, use web search to find price data from Yahoo Finance or other market data sources.

### 4. Web search (for everything else)
Industry reports, government publications, analyst research, company filings, geological surveys, engineering assessments — whatever the investigation requires. This is unchanged from the current approach but is now explicitly the fourth source, not the first.

---

## Phase 1: First-Principles Framing

Before any web research or data gathering, answer these two questions from first principles. Write 150-200 words as an initial framing note:

1. **What is the physical, mathematical, or economic foundation of this theme?** What are the binding constraints — the things that cannot change quickly regardless of price or policy? (Example: a copper mine takes 15 years from discovery to production. This is geology, not economics.)

2. **What are the key variables that drive outcomes?** Identify the 3-5 variables that matter most. For each, note whether it moves fast (months), slow (years), or is effectively fixed (decades).

Do NOT formulate a hypothesis about consensus correctness at this stage. That comes after the data. The purpose of Phase 1 is to identify the physical/structural reality, not to pre-load a view about whether the market is right or wrong.

---

## Phase 2: Structured Research

Research in this order — most foundational to most current. For each pass, capture: source, date, key data point, reliability tier (per RULES.md data quality tiers).

### Pass 1: Mechanism Research
How does this physically work? What are the production timelines, physical requirements, engineering constraints, or structural bottlenecks? This is the "physics layer" — the things that don't change because someone wants them to.

### Pass 2: Supply-Demand Dynamics
Quantify both sides. What is current supply? What is the growth trajectory and what constrains it? What is current demand? What are the structural demand drivers and how fast are they growing? Where is the gap, and when does it become critical?

**Decision gate after Pass 2:** If supply and demand do not show a material and widening gap over the claimed structural timeframe, stop. Report: "Supply-demand analysis does not support a structural constraint at this time. Theme flagged for tactical monitoring." Save the partial brief and move on. Do not continue research on a theme where the physics don't support a structural thesis — sunk-cost bias from completing all six passes will color the conclusion.

### Phase 1B: Hypothesis Formation (after Pass 2)

Now — with mechanism and supply-demand data in hand — formulate the hypothesis. Answer two questions and add them to the framing note (100-150 words):

3. **What would have to be true for the consensus view to be correct?** State the implicit assumptions behind the current market pricing. Be specific — not "the economy stays strong" but "new supply from [specific projects] comes online by [date] at [capacity]."

4. **What would have to be true for the consensus to be wrong?** State the conditions that would make this a structural mispricing. Again, specific and testable.

This ordering matters. The hypothesis is grounded in data from Passes 1-2, not in pre-loaded intuition. Everything that follows is testing it.

### Pass 3: Capital Flows and Positioning
Where is money currently allocated? What is the historical range? What would a reversion to mean or to prior cycle peaks imply for flows? Is the market under-allocated, over-allocated, or neutral relative to the structural picture? Use ETF flow data, fund allocation surveys, and open interest data where available.

### Pass 4: Policy and Regulatory
What are governments doing that affects this theme? Legislation, trade policy, subsidies, tariffs, strategic reserves, export controls. Cross-reference with Skill 4 (Geopolitical & Policy Scanner) output if available.

### Pass 5: Contrarian Signals
Who disagrees with the structural thesis, and why? Find the most credible skeptics and steelman their argument. This is not a formality — if the contrarian case is stronger than expected, the research brief should say so. Address technology substitution, demand destruction scenarios, and supply-side innovations that could break the constraint.

### Pass 6: Current Synthesis
Cross-reference with the current weekly synthesis (Skill 6) output. How does the structural theme interact with the current regime? Is the cyclical picture reinforcing or working against the structural thesis? What is the current-instance context (credit conditions, positioning, policy stance) that shapes how this structural theme expresses in markets right now?

---

## Phase 3: Output — Structural Research Brief

Compile the research into a brief with the following sections. This is the input to Skill 7's structural thesis template.

```markdown
# Structural Research Brief: [Theme Name]
**Date:** [ISO date]
**Researcher:** Macro Advisor System (Skill 11)
**Classification:** Structural — [estimated time horizon for the theme to play out]

---

## First-Principles Framing
[The 200-300 word framing note from Phase 1]

---

## Binding Constraints
[The physical, mathematical, or economic constraints that bound what's possible. Each stated specifically with a number and source. These are the facts that don't change on a quarterly basis.]

1. [Constraint] — [quantified] — [source, date]
2. [Constraint] — [quantified] — [source, date]
3. [Constraint] — [quantified] — [source, date]

---

## Quantified Supply-Demand Picture
[Current state and projected trajectory of supply and demand. Every claim carries a number.]

**Supply side:**
- Current: [quantified]
- Growth trajectory: [quantified, with constraint explanation]
- Key bottleneck: [specific]

**Demand side:**
- Current: [quantified]
- Growth drivers: [each quantified separately]
- Structural demand driver 1: [name] — [quantity impact] — [timeline]
- Structural demand driver 2: [name] — [quantity impact] — [timeline]
- Structural demand driver 3: [name] — [quantity impact] — [timeline]

**Gap analysis:**
- Current surplus/deficit: [quantified]
- Projected trajectory: [when does it become critical?]

---

## Capital Flows and Market Positioning
- Current allocation: [quantified, with source]
- Historical range: [quantified]
- Prior cycle peak: [quantified]
- Implied reallocation potential: [quantified]

---

## Policy Landscape
[Government actions relevant to this theme. Each with source and date.]

---

## What We Have To Believe
[The explicit, independently testable assumptions that must hold for the structural thesis to work. This is the most important section — it's what makes the thesis monitorable.]

1. [Assumption] — Testable by: [specific observable data point or event]
2. [Assumption] — Testable by: [specific observable data point or event]
3. [Assumption] — Testable by: [specific observable data point or event]
4. [Assumption] — Testable by: [specific observable data point or event]

---

## Contrarian Stress-Test
**Strongest case against this thesis:**
[Steelmanned argument, 1-2 paragraphs. Attributed to specific analysts or frameworks where possible.]

**Quantified contrarian claims:**
[The bear case must carry numbers too. For each risk, quantify the impact on the supply-demand picture or the causal chain. This prevents the bull case from being "rigorous" while the bear case is "narrative."]

| # | Contrarian Claim | Value/Impact | Source | Date | Reliability Tier |
|---|-----------------|-------------|--------|------|-----------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

**Specific risks that could break the structural constraint:**
1. [Risk] — [quantified likelihood/impact] — [what evidence exists]
2. [Risk] — [quantified likelihood/impact] — [what evidence exists]
3. [Risk] — [quantified likelihood/impact] — [what evidence exists]

**Assessment:** [After considering the contrarian case, where does the weight of evidence sit? Be honest — if the contrarian case is strong, say so and adjust conviction accordingly. If the contrarian claims are better-sourced or more quantified than the bull claims, that is a signal, not an inconvenience.]

---

## Quantified Claims Log
[Bull and bear claims side by side. This is the evidence base that feeds the Skill 7 thesis mechanism. Minimum 6 bull claims, minimum 3 bear claims.]

**Bull case claims:**

| # | Claim | Value | Source | Date | Reliability Tier |
|---|-------|-------|--------|------|-----------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |
| 6 | | | | | |

**Bear case claims:**

| # | Claim | Value | Source | Date | Reliability Tier |
|---|-------|-------|--------|------|-----------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

---

## Thesis-Readiness Assessment
**Is this ready for Skill 7 thesis generation?** [Yes / No / Needs more research on X]
**Conviction level:** [High / Medium / Low — based on strength of quantified evidence vs. contrarian case]
**Bull-bear balance check:** [Bull claims: N, Bear claims: N. If bull claims exceed bear claims by more than 3:1, explain why the contrarian case is genuinely weaker — or reduce conviction. Lopsided evidence is a flag, not a feature.]
**Evidence independence:** [High / Medium / Low — for analyst-sourced investigations: how much of the evidence comes from independent sources vs. the originating analyst's own claims? Low independence = the research is essentially parroting the analyst. This should reduce conviction regardless of how compelling the argument sounds.]
**Recommended thesis type:** [Directional / Relative value / Hedged]
**Recommended time horizon:** [Derived from the binding constraints, not from convention]
```

---

## Quality Standards

**Pass criteria — the brief must:**
- Contain at least 6 quantified bull claims and at least 3 quantified bear claims, each with sources and dates
- Have a contrarian stress-test that is genuinely argued and quantified, not dismissed as narrative
- State at least 3 independently testable assumptions in "What We Have To Believe"
- Ground every link in the causal chain in a physical, mathematical, or economic reality — not in market narrative or historical correlation alone
- Pass the bull-bear balance check: if bull claims exceed bear claims by more than 3:1, the conviction level must be justified or reduced
- Be written in direct language free of hedging ("it might be worth considering") and empty intensifiers ("unprecedented," "remarkable")

**Fail criteria — reject and redo if:**
- Any major claim in the causal chain is unquantified when quantification was possible
- The contrarian section is weaker than the bull case section
- The "What We Have To Believe" assumptions are not independently testable
- The brief relies on historical correlation without explaining the causal mechanism
- The brief reads like it's arguing for a predetermined conclusion rather than testing a hypothesis
- [Analyst-sourced investigations] The evidence base relies primarily on the originating analyst's own data, charts, or claims without independent verification from separate sources. The analyst's framework is a hypothesis to test, not evidence to cite.

---

## Storage

- Save research briefs to `outputs/research/STRUCTURAL-[theme-name]-[date].md`
- If the brief leads to a thesis, Skill 7 will reference it in the thesis file
- If the brief concludes the thesis is not viable, save it anyway — failed research is still valuable for the self-improvement loop (Skill 8)

---

## What This Skill Does NOT Do

- **Generate theses.** That's Skill 7. This skill produces the research input.
- **Recommend ETFs or position sizes.** That's Skill 7's job.
- **Produce user-facing output.** The Monday Briefing (Skill 9) is the user-facing layer. This is internal analytical infrastructure.
- **Run weekly.** This fires only when a structural theme warrants deep research.

---

## Meta Block

```yaml
---
meta:
  skill: structural-research
  skill_version: "1.2"
  run_date: "[ISO date]"
  theme: "[theme name]"
  trigger: [skill-7-data-pattern / skill-7-analyst-sourced / skill-7-scanner-candidate / manual / investigate-theme-command]
  analyst_source: "[analyst name, if analyst-sourced — otherwise null]"
  research_passes_completed: [1-6]
  quantified_claims: [number]
  contrarian_strength: [weak/moderate/strong]
  thesis_ready: [yes/no/needs-more-research]
  conviction: [high/medium/low]
  data_access:
    snapshot_used: [true/false]
    additional_series_pulled: ["SERIES1", "SERIES2"]
    etf_lookup_used: [true/false]
    web_searches_conducted: [number]
  evidence_independence: [high/medium/low — "low" if evidence base relies primarily on originating analyst's own data]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues or gaps]"
---
```
