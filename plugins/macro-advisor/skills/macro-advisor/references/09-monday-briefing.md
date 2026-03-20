# Monday Morning Briefing — Output Template

## Objective

Compile the final human-readable output from the entire weekly chain. One document to read Monday morning. Everything you need to know, nothing you don't.

**Language rule:** Write as if you're explaining to a smart friend over coffee who invests through ETFs but doesn't work in finance. No jargon without explanation. No acronyms without defining them. If you catch yourself writing something your friend would need to Google, rewrite it.

**Data rule:** Read `skills/RULES.md` first. Every number must come from the data snapshot or a sourced web search. Never invent numbers.

## Inputs

- Weekly Synthesis output (Skill 6)
- Thesis Monitor output (Skill 7)
- Actual thesis files in `outputs/theses/active/` — read the filenames to determine status (ACTIVE- prefix = active, DRAFT- prefix = draft). The filenames are the source of truth for thesis status, not the thesis monitor summary.
- Thesis presentation briefing cards (Skill 12) — read from `outputs/theses/presentations/`. Skill 12 runs before Skill 9 in the chain and should always produce these. If Skill 12 output is missing (error recovery only), generate cards directly from thesis files using the same format.
- Improvement Loop summary (Skill 8 — system health only)
- **Prior week's briefing** (if it exists in `outputs/briefings/`) — read the previous week's briefing to check whether last week's calls played out. This is the accountability loop.

## Weekly Delivery

After compiling the briefing markdown, generate the HTML dashboard that presents everything in one file:

```bash
python scripts/generate_dashboard.py \
  --week YYYY-Www \
  --output-dir outputs/ \
  --out outputs/briefings/YYYY-Www-dashboard.html
```

The dashboard combines:
1. **Monday Briefing** — the formatted summary (Briefing tab)
2. **Regime Map** — visual four-quadrant chart showing current position (Regime Map tab)
3. **All thesis documents** — tabbed view of active and draft theses with full detail (Theses tab)
4. **Improvement report** — system health and amendment proposals (System Health tab)

Deliver the HTML dashboard as the primary output. The user opens one file, sees everything.

The raw markdown files still get saved (for the improvement loop to read and for archival), but the user-facing deliverable is the dashboard.

## Output Format

```markdown
# Macro Briefing — Week of [Date]

## The Big Picture
**Regime:** [Quadrant] → [Direction]
**Confidence:** [High/Medium/Low]
**Changed from last week:** [Yes/No — if yes, from what to what]

[3-4 sentences a non-finance person would understand. What's happening in the economy, where are we heading, and what's the one thing that matters most this week. Define every concept you use.]

---

## Last Week's Scorecard
Read the prior week's briefing from `outputs/briefings/`. Check what we said and whether it played out. This builds accountability and calibrates trust.

- **Regime call:** [What did we say last week? Was it right?]
- **Key events we flagged:** [Did they happen? Did they matter as we said?]
- **Asset/sector tilts:** [Were they directionally correct?]
- **Signal vs. noise:** [Did the noise stay noise? Did we miss anything?]

Keep it to 3-4 lines. Not a retrospective — just "we said X, Y happened." Skip this section on the first week (no prior briefing).

---

## What Changed This Week
[1-3 bullet points. For each: what happened, and why it matters for your money. Plain language.]

---

## Active Theses

Read the actual files in `outputs/theses/active/`. Files prefixed with ACTIVE- are active positions being monitored. Files prefixed with DRAFT- are candidates awaiting review.

**Active positions:**
| Thesis | What's Happening | What To Do |
|--------|-----------------|-----------|
| [name from ACTIVE- file] | [plain English: what changed this week] | [hold/add/reduce/close] |

**Draft candidates (awaiting your decision):**
| Thesis | One-Line Summary | Recommendation |
|--------|-----------------|---------------|
| [name from DRAFT- file] | [what's the bet, in one sentence a friend would understand] | [activate/watch/discard] |

---

## Cross-Asset View

What to own, what to avoid, and why. ETFs in the user's preferred currency where available (US ticker in parentheses for reference). Read `skills/references/etf-reference.md` for currency-specific equivalents and `config/user-config.json` for the user's `preferred_currency`.

| What | Direction | ETFs | Why (plain language) |
|------|-----------|------|---------------------|
| US Stocks (broad) | [Buy/Hold/Reduce] | [preferred currency ticker or US ticker] | [one sentence your friend would understand] |
| International Stocks | [direction] | [tickers] | [one sentence] |
| Long-Term Bonds | [direction] | [tickers] | [one sentence] |
| Short-Term Bonds/Cash | [direction] | [tickers] | [one sentence] |
| Corporate Bonds | [direction] | [tickers] | [one sentence] |
| Gold | [direction] | [tickers] | [one sentence] |
| Oil/Commodities | [direction] | [tickers] | [one sentence] |

### Within Stocks — Full Sector View

Cover all major sectors. For each: what to do, how long, and when to reassess. The reader needs the complete picture, not just the highlights.

| Sector | Direction | ETFs | Why (plain language) | Timing |
|--------|-----------|------|---------------------|--------|
| Energy | [favor/neutral/avoid] | [XLE/IUES.SW] | [one sentence] | [tactical (weeks) / structural (months) + specific reassessment trigger] |
| Technology | [direction] | [QQQ/CSNDX.SW] | [one sentence] | [timing + trigger] |
| Financials | [direction] | [XLF/IUFS.SW] | [one sentence] | [timing + trigger] |
| Healthcare | [direction] | [XLV/IUHC.SW] | [one sentence] | [timing + trigger] |
| Industrials | [direction] | [XLI] | [one sentence] | [timing + trigger] |
| Consumer Discretionary | [direction] | [XLY] | [one sentence] | [timing + trigger] |
| Consumer Staples | [direction] | [XLP] | [one sentence] | [timing + trigger] |
| Utilities | [direction] | [XLU] | [one sentence] | [timing + trigger] |
| Materials | [direction] | [XLB] | [one sentence] | [timing + trigger] |
| Communication Services | [direction] | [XLC] | [one sentence] | [timing + trigger] |
| Real Estate | [direction] | [VNQ] | [one sentence] | [timing + trigger] |

If any active thesis or current event makes a thematic sub-sector relevant this week (e.g., defense, semiconductors, drones, uranium), add it below the table with the same format.

**Timing guidance:**
Don't use pre-set time categories. Derive the timing from the specific reason you hold the view:
- **What's the catalyst or condition that drives this view?** Name it.
- **When does that catalyst resolve or that condition change?** That's your reassessment point.
- **What would make you change your mind before then?** That's your exit signal.

Example: "Favor energy — oil supply disruption keeps prices elevated. Reassess when Iran situation resolves or oil drops below $85. Exit if OPEC announces production increase." The timing is built into the logic, not bolted on as a category.

---

## External Analyst Check
[One paragraph: what are Steno and Alpine Macro saying this week? Does it confirm or challenge our view? Write it conversationally.]

---

## Key Events Next Week
[Max 5 items with dates. For each, explain what outcome would matter and what it means — not just the event name.]

---

## Signal vs. Noise
[1-2 headlines that dominated the news but don't change the investment picture. One sentence each on why they don't matter.]

---

## System Health
**Overall score:** [from improvement loop]
**Skills at risk:** [any, or "All systems healthy"]
**Amendments pending review:** [count, or "None"]
**Track record** (from `outputs/improvement/accuracy-tracker.md`, show after 4+ weeks of data):
[Regime call accuracy: X%. Asset tilt accuracy: X%. Thesis accuracy: X%. One sentence: "This system is strongest at [X] and weakest at [Y]."]

---

## Reference: The Four Regimes

This section stays the same every week. It's here so you always have context for what the alternatives are and what would cause a shift.

**Goldilocks** (growth rising, inflation falling): The sweet spot. The economy is growing but prices aren't running away. Companies earn more, borrowing is cheap, and investors take risk. Stocks tend to do well — especially growth companies and emerging markets. Bonds are fine too because inflation isn't a threat.

**Overheating** (growth rising, inflation rising): The economy is strong but prices are rising too fast. Central banks start worrying about inflation and hold rates higher. This favors real things — oil, gold, commodities, value companies — over growth stocks and long-term bonds. Think of it as "making money but everything costs more."

**Disinflationary Slowdown** (growth falling, inflation falling): The economy is cooling and prices are easing. Central banks start thinking about cutting rates. Bonds do well (especially long-term ones) because falling rates push bond prices up. Defensive stocks (healthcare, utilities) hold up better than cyclicals. Cash and quality matter.

**Stagflation** (growth falling, inflation rising): The worst combination. The economy is weakening but prices keep rising — often because of a supply shock like an oil spike. Central banks are stuck: they can't cut rates without fueling inflation, can't raise rates without crushing growth. Nothing works well. Gold, cash, and real assets are the least bad options. The goal is to preserve capital, not grow it.

**What causes regime shifts:** Central bank policy changes, oil/commodity shocks, credit cycles turning, labor market inflections, and fiscal policy shifts. The weekly synthesis tracks all of these. When we say "moving toward Stagflation," we mean the data is starting to show the combination of slowing growth and sticky/rising inflation — the regime hasn't fully shifted yet, but the direction is clear.
```

## Language Standards — Enforced

The language quality is the single most important quality standard for this document. If the briefing reads like a research report, it failed.

**BAD (do not write like this):**
"HY spreads 322bp (97th %ile tight)—minimal cushion for defaults. IG 92bp similarly tight. Rotate defensively toward government bonds."

**GOOD (write like this):**
"Corporate bonds are paying very little extra yield for the risk you're taking — the gap between corporate bond yields and safe government bonds is near its smallest in years. If the economy slows, these bonds could lose value quickly. Favor government bonds (CSBGC3.SW) over corporate (IHYG.SW) until spreads widen."

**BAD:**
"Real 10Y rates neutral (1.86%); inflation expectations drifting higher (breakeven 5Y 2.62%)."

**GOOD:**
"After adjusting for inflation, the return on 10-year government bonds is about 1.9% — not especially high or low. But the market is starting to price in higher inflation ahead (inflation expectations have been creeping up), which makes long-term bonds riskier to hold."

**The test:** Read every sentence aloud. Would your friend who invests in ETFs but doesn't read the Financial Times understand it without asking a follow-up question? If not, rewrite it.

## Other Quality Standards

- Readable in under 5 minutes
- No section longer than 4-5 sentences
- Every stance includes specific ETF ticker(s) and a one-sentence justification
- Thesis table status comes from actual filenames (ACTIVE- vs DRAFT-), not from the thesis monitor summary
- If the regime hasn't changed, say so — "Same regime for 4th week" is valid
- Every number sourced — never invented
- Equity sector view only includes sectors where there's an active directional view — don't force all rows
