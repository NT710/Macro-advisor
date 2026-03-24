# Skill 6: Weekly Macro Synthesis

## Objective

Read all collection skill outputs from the current week. Synthesize into a single regime assessment with cross-asset implications. This is the "Alpine Macro research note" equivalent — one document that tells you where we are, which direction we're moving, and what it means for positioning.

## Core Framework: Four-Quadrant Regime Model

|                    | **Inflation Falling** | **Inflation Rising** |
|--------------------|-----------------------|----------------------|
| **Growth Rising**  | Goldilocks            | Overheating          |
| **Growth Falling** | Disinflationary Slowdown | Stagflation       |

### Asset Class Implications by Regime

**Goldilocks** (growth up, inflation down)
**Overheating** (growth up, inflation up)
**Disinflationary Slowdown** (growth down, inflation down)
**Stagflation** (growth down, inflation up)

We believe this regime model captures how macro conditions translate to asset performance. It is our framework.

First: classify the regime based on growth and inflation direction from the data.

### Regime Stability Principle

A regime is a structural macroeconomic condition that persists for quarters, not weeks. When classifying, assess growth and inflation direction over a 6-month horizon, not just the last few data prints. A single month's uptick in CPI within a broader disinflationary trend does not constitute a regime change — it's noise within the existing regime.

**Before calling a regime change, require confirmation:**
1. At least 2 consecutive weeks of data pointing to the new regime, not just one anomalous print.
2. The shift must be visible in the 6-month trend of the underlying indicators, not just the most recent 1-2 months.
3. If the data is ambiguous — one indicator says growth is rising, another says falling — hold the current regime and flag the conflict. The burden of proof is on the change, not on continuity.

**Equally important — challenge continuity too.** The confirmation requirement must not create a bias toward holding the current regime indefinitely. If the same regime has been active for 8+ consecutive weeks, actively stress-test it: what evidence would it take to call a different regime? If you can't articulate what would change your mind, you may be anchored rather than analytical. The burden of proof applies symmetrically — it's on the change when data is noisy, and it's on continuity when the regime has been stale for months and the underlying data is shifting.

**Why this matters:** The weekly system runs 52 times a year. If the regime changes every 2-3 weeks, the Monday briefing whipsaws between contradictory positioning recommendations, and thesis time horizons become meaningless. A regime call should be stable enough to act on for at least a quarter. If it isn't, either the regime genuinely shifted (report it with high conviction) or the data is noisy (hold the current regime and note the uncertainty).

When the current regime has held for multiple weeks, say so: "Disinflationary Slowdown for the 8th consecutive week." That's useful information — it tells the reader the macro picture is stable.

Then: work out the asset implications for this specific instance of the regime. Each instance has its own characteristics — credit conditions, positioning, policy stance, valuations — that shape how the regime plays out in practice. Two different Overheating regimes can look different depending on whether credit is loose or tight, whether valuations are stretched or reasonable.

State what the data says and why it leads to your conclusions. When the data shows something unexpected within the regime — for example, a Goldilocks regime where credit is unusually tight — report that as a noteworthy observation and explain what it means for positioning. The framework stays. The data fills in the detail.

## Inputs

Read the following files from the current week's output directory. The file naming convention is `YYYY-Www-[skill-name].md` (e.g., `2026-W12-central-bank-watch.md`).

1. Central Bank Watch output (Skill 1)
2. Liquidity & Credit Monitor output (Skill 2)
3. Macro Data Tracker output (Skill 3)
4. Geopolitical & Policy Scanner output (Skill 4)
5. Market Positioning & Sentiment output (Skill 5)

Also read the **prior week's** synthesis output (if it exists) for trend context and prior regime assessment. "Prior week" means the most recent synthesis file from a **previous ISO week number** — i.e., the highest `YYYY-Www` where Www is strictly less than the current week. If the current week is W12, the prior synthesis is the W11 file (or W10, W09, etc.). **Never treat the current week's own file as "prior."** Same-week reruns are updates to the current week's assessment, not a new week of data.

**Note: Skill 13 (Structural Scanner) output is NOT read here.** The synthesis is a cyclical regime assessment — it answers "where are we in the cycle right now?" Structural imbalances (multi-year supply-demand gaps, capex underinvestment, demographic shifts) enter the system through a separate pipeline: Skill 13 → Skill 11 → Skill 7. This separation is intentional. The regime assessment should reflect current-cycle data, not be anchored by structural findings that operate on a different timescale. If a structural finding (e.g., energy supply tightness) is also showing up in the cyclical data (e.g., rising energy prices affecting the inflation axis), the synthesis will pick it up through the normal data flow from Skills 1-5 — it doesn't need the scanner's framing to do so.

## Execution Steps

1. Read all five collection skill outputs for the current week
2. Read prior week's synthesis (if available) for continuity — "prior week" means the most recent `YYYY-Www` synthesis where Www < current week. Never read the current week's own file as prior.
3. Extract the key signal from each skill:
   - Skill 1: Policy direction and liquidity regime implication
   - Skill 2: Liquidity regime classification (the most important input)
   - Skill 3: Growth regime classification and surprise direction
   - Skill 4: Any regime-change risk from policy actions
   - Skill 5: Positioning extremes and contrarian setups
4. Determine the current regime quadrant based on growth + inflation direction
5. Assess direction of travel — are we moving between quadrants?
6. Derive cross-asset implications from the regime
7. Identify what changed this week vs. last week
8. Separate signal from noise
9. Compile into output format

## Synthesis Logic

The regime assessment follows this priority hierarchy:
1. **Liquidity (Skill 2)** is the primary driver — if liquidity is expanding, the base case favors risk assets regardless of growth picture
2. **Growth direction (Skill 3)** determines which risk assets — cyclicals vs. defensives, EM vs. DM
3. **Inflation direction (Skill 3)** determines duration and real asset positioning
4. **Policy (Skills 1, 4)** can override the base case when regime-shifting
5. **Positioning (Skill 5)** modifies conviction in both directions — extreme positioning against the macro trend = higher conviction contrarian, but extreme positioning *with* the trend = a warning sign. When everyone is positioned for the current regime to continue, the risk/reward of staying is worse even if the macro data still supports it. Crowded consensus is when regime reversals do the most damage.

When inputs conflict (e.g., liquidity expanding but growth decelerating), flag the conflict explicitly and state which signal you're prioritizing and why.

## Output Format

```markdown
## Weekly Macro Synthesis — Week of [Date]

### Regime Assessment
**Current Quadrant:** [Goldilocks / Overheating / Disinflationary Slowdown / Stagflation]
**Weeks in current regime:** [N — USE THE REGIME STREAK SCRIPT OUTPUT. Before this skill runs, the orchestration executes `regime_week_count.py` which reads `regime-history.json` (one entry per ISO week, deduplicated) and counts the trailing streak of same-regime weeks. Rules:
- If this week's regime matches the script's reported regime → N = script_streak + 1.
- If this week's regime is DIFFERENT → N = 1.
- If the script returned streak=0 (first run, no history) → estimate from 6-month data trends, do NOT default to 1.
Do NOT compute this from prior synthesis files. Do NOT carry forward a number from a prior run. The script is the single source of truth — it cannot be inflated by same-week reruns because regime-history.json stores one entry per ISO week.]
**Direction:** [Stable / Moving toward ___]
**Confidence:** [High / Medium / Low]
**Change from last week:** [No change / Shifted from ___ to ___]

**Regime coordinates (for dashboard visualization):**
- Growth score: [continuous value from -1.0 to +1.0, derived from the growth data. Map from the underlying indicators: ISM manufacturing (weight 0.3), unemployment direction (0.2), NFP trend (0.2), retail sales trend (0.15), GDP tracking (0.15). Normalize: +1.0 = all indicators strongly improving, -1.0 = all indicators strongly deteriorating, 0 = mixed/flat. This is NOT a binary quadrant assignment — it's a continuous measure of where within the quadrant the economy sits.]
- Inflation score: [continuous value from -1.0 to +1.0, derived from the inflation data. Map from: core PCE direction (weight 0.3), PPI direction (0.2), breakeven inflation trend (0.2), wage growth trend (0.15), commodity price direction (0.15). Normalize: +1.0 = inflation clearly accelerating, -1.0 = inflation clearly decelerating, 0 = stable/ambiguous.]

**Coordinate-label consistency check (mandatory):** After assigning both scores, verify that the sign of each score matches the regime label. The mapping is: Goldilocks = growth positive, inflation negative. Overheating = growth positive, inflation positive. Stagflation = growth negative, inflation positive. Disinflationary Slowdown = growth negative, inflation negative. If your scores land in a different quadrant than your label, you must do one of two things: (1) revise the scores to reflect the data more accurately, explaining what you got wrong on the first pass, or (2) revise the regime label, explaining why the data actually points to the other quadrant. You may NOT leave them contradicting silently. A score near zero (between -0.15 and +0.15) on either axis is exempt from this check — it means the signal is genuinely ambiguous on that dimension, which is useful information. Report the exemption explicitly: "Growth score near zero — signal ambiguous, consistent with either [X] or [Y] regime."

[2-3 sentence narrative explanation of the regime classification. Why this quadrant? What's the dominant signal?]

### Liquidity Picture
[2-3 sentences synthesized from Skill 2. Regime classification, key data points, direction of change.]

### Growth Picture
[2-3 sentences synthesized from Skill 3. Growth regime, surprise direction, key indicators.]

### Policy Picture
[2-3 sentences synthesized from Skills 1 and 4. What central banks are doing, any policy shifts, regime-change risks from geopolitics.]

### Positioning Picture
[2-3 sentences synthesized from Skill 5. Where is the crowd, any extremes, what's the vulnerability.]

### Cross-Asset Implications (ETF-Focused)
Express all allocation views using specific ETFs. The reader trades ETFs on Monday morning.

| Asset Class | Stance | ETF Expression | Rationale | Timing |
|-------------|--------|---------------|-----------|--------|
| US Equities | [Bull/Neutral/Bear] | [SPY/QQQ/IWM/VTV — be specific] | [one sentence] | [tactical (weeks) / structural (months) + reassessment trigger] |
| Int'l Developed | [stance] | [EFA/VEA] | [one sentence] | [timing + trigger] |
| Emerging Markets | [stance] | [EEM/VWO] | [one sentence] | [timing + trigger] |
| Duration | [Long/Neutral/Short] | [TLT vs. SHV/BIL/SGOV] | [one sentence] | [timing + trigger] |
| Credit | [OW/N/UW] | [HYG/LQD or avoid] | [one sentence] | [timing + trigger] |
| Gold | [stance] | [GLD/IAU] | [one sentence] | [timing + trigger] |
| Commodities | [stance] | [USO/DJP/GSG] | [one sentence] | [timing + trigger] |
| Cash | [% allocation] | [SGOV/BIL] | [one sentence] | [timing + trigger] |

### Sector View

Provide a complete sector assessment covering all 11 GICS sectors. For each sector: direction (favor/neutral/avoid), the reasoning from the current regime and data, and whether the position is tactical (weeks, tied to a catalyst) or structural (months, tied to the regime).

Also flag any thematic sub-sectors made relevant by active theses or current events (e.g., defense, semiconductors, drones, uranium). These go in addition to the 11 standard sectors.

### Regime Forecast — 6 and 12 Months

Based on the current data, policy trajectory, and thesis logic, project where the regime is likely to be in 6 months and 12 months. This is not a linear extrapolation — it's a reasoned assessment derived from the analysis above.

For each horizon:
- **Most likely regime:** [quadrant] — [why, based on what the data and policy trajectory point to]
- **Key assumption:** [what has to hold true for this forecast to play out]
- **What would change it:** [the specific development that would shift the trajectory to a different quadrant]
- **Confidence:** [High/Medium/Low — and why]

The 6-month forecast should be grounded in visible policy paths and data trends (Fed rate trajectory, credit cycle direction, oil supply dynamics). The 12-month forecast is inherently less certain — acknowledge that. If the 12-month view is genuinely unclear, say so rather than forcing a prediction.

These forecasts feed into the regime map visualization in the dashboard. They appear as projected dots on the chart, clearly labelled as projections with stated assumptions — not predictions.

### External Analyst Check
Read the analyst monitor output from Skill 10 (`outputs/collection/YYYY-Www-analyst-monitor.md`). Summarize the key cross-reference points here:

**Steno:** [What is he focused on? Does it confirm or challenge our regime view?]
**Alpine Macro:** [What are they publishing? Does it confirm or challenge?]
**Alignment:** [Confirms / Diverges / Different topic — explain]
[If both confirm: are we consensus? If either diverges: what might we be missing?]

Note: Analyst views are a contrarian/confirmation check, not a regime model input. If the analyst monitor wasn't available this week, note that and skip this section.

### What Changed This Week
[The 1-3 things that actually matter. Not a summary of all data — just the signal. What moved the needle on the regime assessment or cross-asset view?]

### What to Watch Next Week
[Specific events, data releases, or thresholds that could change the picture. Include dates.]

### Signal vs. Noise
[Explicitly name 1-2 things that dominated headlines this week but don't change the macro picture. Why are they noise?]
```

## Quality Standards

- The regime assessment must be internally consistent — if you say "Goldilocks" but the data shows rising inflation, you have a contradiction
- Cross-asset implications must follow logically from the regime — don't say "bullish equities" in a stagflation regime without explanation
- "What Changed" should be genuinely new information, not restating the regime
- Every section must add synthesis value — if it's just repeating what the collection skill said, rewrite it to show the cross-connection
- When inputs conflict, name the conflict. Don't resolve it by ignoring one input.
- Prior week comparison is mandatory when prior synthesis exists

## Meta Block

```yaml
---
meta:
  skill: weekly-macro-synthesis
  skill_version: "1.2"
  run_date: "[ISO date]"
  inputs_read:
    central_bank_watch: [true/false — was this week's output available?]
    liquidity_credit: [true/false]
    macro_data: [true/false]
    geopolitical: [true/false]
    positioning: [true/false]
    prior_synthesis: [true/false]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
    inputs_available: [number out of 5]
    regime_changed: [true/false]
    regime_weeks_held: [number — from regime_week_count.py script output. Do NOT compute this yourself.]
    growth_score: [number, -1.0 to 1.0]
    inflation_score: [number, -1.0 to 1.0]
  notes: "[any issues — e.g., 'positioning data unavailable, synthesis based on 4 of 5 inputs']"
---
```
