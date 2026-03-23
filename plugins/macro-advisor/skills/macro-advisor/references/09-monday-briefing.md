# Monday Morning Briefing — Macro Memo

## Objective

Write a weekly macro memo. Not a data dump — a narrative. The reader opens the Briefing tab to understand what happened, why it matters, and what to do about it. All structured data (cross-asset tables, sector views, thesis details, system health) lives in other dashboard tabs. The memo's job is to connect the dots between them.

**Voice:** Write as if you're Lyn Alden explaining the week to a smart friend over coffee who invests through ETFs but doesn't work in finance. Long-form prose. Thematic sections. Data woven into sentences, not presented in tables. No jargon without explanation. No acronyms without defining them. If you catch yourself writing something your friend would need to Google, rewrite it.

**Data rule:** Read `skills/RULES.md` first. Every number must come from the data snapshot or a sourced web search. Never invent numbers.

## Inputs

- Weekly Synthesis output (Skill 6)
- Thesis Monitor output (Skill 7)
- Actual thesis files in `outputs/theses/active/` — **list the directory and read every file.** The filenames are the source of truth for thesis status (ACTIVE- prefix = active, DRAFT- prefix = draft), not the thesis monitor summary.
- Thesis presentation briefing cards (Skill 12) — read from `outputs/theses/presentations/`. Skill 12 runs before Skill 9 in the chain and should always produce these. If Skill 12 output is missing (error recovery only), generate cards directly from thesis files using the same format.
- **Reconciliation:** Compare the Skill 12 briefing cards against the actual files in `outputs/theses/active/`. If any thesis file exists on disk that does NOT have a corresponding Skill 12 card, generate a briefing card directly from the thesis file. This catches theses created mid-cycle by `/investigate-theme` or `/structural-scan` that may have been missed by earlier skills. Every thesis on disk must appear in the briefing — referenced naturally in prose, not forced into a table.
- Improvement Loop summary (Skill 8 — system health only)
- **Prior week's briefing** (if it exists in `outputs/briefings/`) — read the most recent briefing from a **previous ISO week** (Www strictly less than current week) to check whether last week's calls played out. On a same-week rerun, the current week's own briefing is not "prior." This is the accountability loop.
- External analyst monitor output (Skill 10) — for surfacing views that challenge ours

## Dashboard Data JSON (mandatory)

After compiling the briefing memo, write a structured JSON file alongside it:

**Path:** `outputs/briefings/{week}-briefing-data.json`

This file provides the dashboard with all structured data it needs. The dashboard's Overview tab reads cross-asset and sector positioning from this JSON. The Theses tab reads thesis data from the thesis files directly. The memo does NOT contain tables — the JSON carries the structured data, the memo carries the narrative.

```json
{
  "theses": {
    "short-duration-capital-preservation": {
      "conviction": "High",
      "recommendation": "Hold"
    },
    "energy-oil-shock-beneficiary": {
      "conviction": "Medium",
      "recommendation": "Watch"
    }
  },
  "cross_asset": [
    {
      "what": "US Stocks (broad)",
      "direction": "Underweight",
      "etfs": "CSSPX.SW (SPY)",
      "why": "Stagflation squeezes profits from both sides.",
      "timing": "Avoid until regime shifts"
    }
  ],
  "sector_view": [
    {
      "sector": "Energy",
      "direction": "Strong Favor",
      "etfs": "IUES.SW (XLE)",
      "why": "Oil at $98 means windfall profits.",
      "timing": "Tactical — reassess on Hormuz resolution or oil below $85"
    }
  ]
}
```

**Rules:**

`theses` object:
- Keys are thesis slugs: lowercase, hyphens for spaces, no colons or special characters. Must match the thesis filename minus the `ACTIVE-`/`DRAFT-` prefix and `.md` extension.
- `conviction`: "High", "Medium", or "Low". Required for every thesis.
- `recommendation`: The single action word — "Hold", "Add", "Reduce", "Close" (active) or "Activate", "Watch", "Discard" (draft). One word only, capitalized.
- Every thesis on disk must appear.

`cross_asset` array:
- One object per asset class row.
- `what`: asset class name (e.g. "US Stocks (broad)", "Gold", "Oil/Commodities").
- `direction`: the stance word exactly as used in the memo's reasoning (e.g. "Favor", "Underweight", "Avoid", "Tactical Favor", "Neutral/Avoid").
- `etfs`: ticker string (e.g. "ZGLD.SW (GLD)").
- `why`: one-sentence rationale.
- `timing`: when to act or reassess.

`sector_view` array:
- One object per sector row.
- Same fields as `cross_asset` but with `sector` instead of `what`.

This JSON is the **single source of truth** for the dashboard's structured tables. The memo references these views in prose — the JSON renders them as tables in the Overview tab. Both are generated from the same reasoning pass — they cannot contradict.

---

## Weekly Delivery

After compiling the briefing markdown and the dashboard data JSON, generate the HTML dashboard that presents everything in one file:

```bash
python scripts/generate_dashboard.py \
  --week YYYY-Www \
  --output-dir outputs/ \
  --out outputs/briefings/YYYY-Www-dashboard.html
```

The dashboard combines:
1. **Monday Briefing** — the memo (Briefing tab)
2. **Regime Map** — visual four-quadrant chart (Regime Map tab)
3. **Overview** — cross-asset and sector tables from the JSON (Overview tab)
4. **All thesis documents** — tabbed view of active and draft theses with full detail (Theses tab)
5. **Improvement report** — system health and amendment proposals (System Health tab)

Deliver the HTML dashboard as the primary output. The user opens one file, sees everything.

The raw markdown files still get saved (for the improvement loop to read and for archival), but the user-facing deliverable is the dashboard.

---

## Memo Structure

The memo has **three anchors** (always present, fixed position) and a **narrative body** (dynamic headlines, flexible length). No tables in the memo — ever. Data is woven into prose.

### ANCHOR 1: Opening (no headline — always first)

The memo opens cold. No header, no "Big Picture" label. Just the most important thing this week in 2-4 sentences.

The regime state is woven into the narrative, not presented as a badge. Don't write "Regime: Goldilocks → Stable." Write: "Goldilocks extended into its sixth week, but the floor is creaking. Core PCE came in at 2.4% — still declining — but ISM new orders dropped below 50 for the first time since October."

This is the "if you read nothing else" paragraph. A reader who stops here should know: what regime we're in, whether it changed, and what the single most important development is this week.

### ANCHOR 2: Checking Our Work (fixed headline — always second)

Always present. Always runs before the narrative body. This is the structural anti-confirmation-bias mechanism — the system cannot build a story without first confronting its misses.

## Checking Our Work

Read the prior week's briefing from `outputs/briefings/`. For each claim we made:
- **Regime call:** Was it right? If the regime held, say so. If we called a shift that didn't happen, own it.
- **Specific calls:** Did the data moves we flagged play out? Were our directional views correct?
- **Misses:** Did something important happen that we didn't flag? Did noise we dismissed turn out to matter?

Write this in prose, not bullets. 3-5 sentences. Honest. No hedging.

*Example: "Last week we called energy a tactical overweight expecting Brent to hold above $85. It didn't — OPEC signaled production increases and Brent closed at $82. The direction was right (energy outperformed broad equities by 1.2%) but the specific level was wrong. Our Goldilocks regime call held — sixth consecutive week. The one thing we missed: credit spreads widened 15bp on Thursday, which we'd dismissed as noise but may be an early signal worth watching."*

Skip this section entirely on the first week (no prior briefing exists). On weeks where everything played out as expected, keep it to 2 sentences: "We called X, X happened. No misses worth flagging."

### NARRATIVE BODY: Dynamic Headlines (1-3 sections, between anchors 2 and 3)

This is the core of the memo. The headlines are **thematic and specific to the week**, not templated. The number of sections depends on how much actually matters.

**How to choose headlines:** Ask: "What would a sharp macro analyst title this week's note?" Not "What Changed This Week" — that's a filing label, not a headline. Think:
- "The ISM Crack" (a specific data point that shifts the picture)
- "Why the Rate Cut Got Priced Out" (explaining a market move through the macro lens)
- "Quiet Week, Louder Signals" (when nothing dramatic happened but underlying trends matter)
- "Copper Is Telling a Different Story" (when one data point contradicts the regime narrative)
- "What Lyn Alden Sees That We Don't" (when external analysts challenge our view)

**Quiet weeks (1 section):** If the regime is stable and no data point changed the picture, write one section. Go deeper on something — stress-test a thesis assumption, examine why a normally noisy indicator might be signaling something, or trace through a second-order effect that hasn't played out yet.

**Active weeks (2-3 sections):** Multiple themes. Maybe the Fed spoke AND a thesis hit its activation trigger AND an external analyst raised a challenge. Each gets its own section with its own headline.

**Required elements woven into the narrative body** (not their own sections — integrated naturally):

1. **The weakest link.** For every causal chain you build, name the assumption most likely to break. Not a disclaimer at the end — inline: "This depends on credit spreads staying below 400bp, which is the most fragile assumption right now because high yield issuance has been running 30% above the 5-year average."

2. **What would change the view.** What data point or event would force a regime reassessment or a thesis kill switch. Woven into the relevant section, not listed separately.

3. **Thesis references.** Mention active theses in context when the week's data is relevant to them. "The copper supply deficit thesis (see Theses tab) moved closer to its first activation trigger this week — LME inventories dropped below 150k tonnes." Don't list all theses. Only mention the ones where something happened.

4. **External analyst challenge.** At least one view from the analyst monitor (Skill 10) that contradicts or complicates our current positioning. Not quarantined in its own section — brought into the narrative where it's relevant. "Lyn Alden's latest note argues the liquidity picture is tighter than we think, pointing to reverse repo drawdowns that our model weights at tier 2."

5. **Signal vs. noise.** If a headline dominated the news but doesn't change the investment picture, call it out in a sentence: "The [headline] grabbed attention but doesn't change the regime math — here's why." Don't create a separate section for this.

### ANCHOR 3: Looking Ahead (fixed headline — always last)

## Looking Ahead

3-5 sentences. What matters next week, what outcome would change the current view, and what to watch.

Not a bullet list of economic releases. A narrative about what's coming and why it matters for the current positioning.

*Example: "Next week's NFP print on Friday is the one to watch. If payrolls come in below 120k, the ISM crack we flagged becomes a pattern rather than a blip, and Goldilocks starts looking like it has an expiration date. Above 180k and the regime extends comfortably. The Fed speaks Tuesday — tone matters more than substance at this point, specifically whether Powell acknowledges the manufacturing weakness or talks past it."*

---

## What Is NOT in the Memo

These all live in other dashboard tabs. The memo can reference them ("see the Theses tab for full detail") but does not reproduce them:

- **Cross-Asset View table** → Overview tab (from JSON)
- **Sector View table** → Overview tab (from JSON)
- **Active Theses table** → Theses tab
- **Draft Candidates table** → Theses tab
- **System Health metrics** → System Health tab
- **Reference: The Four Regimes** → Regime Map tab (static content)

---

## Anti-Confirmation-Bias Rules

These rules are mandatory. They apply to the memo narrative, thesis references, and the JSON data equally.

### Structural Mechanisms

1. **Checking Our Work runs before the narrative.** The system cannot build this week's story without first accounting for last week's accuracy. This prevents narrative momentum from overriding evidence.

2. **Weakest-link rule.** Every causal chain in the memo must name its most fragile assumption. If you write "Goldilocks continues because growth is strong and inflation is falling," you must also write which of those legs is weaker and what would break it.

3. **External challenge rule.** At least one external analyst view must appear in the memo that complicates or contradicts our positioning. If no analyst disagrees with us this week, that itself is a signal worth noting — consensus alignment is when surprises do the most damage.

4. **Kill switch proximity rule.** Any thesis within 20% of its kill switch threshold must be mentioned in the memo, even if the narrative is broadly positive. The reader needs to know what's close to triggering.

### Recommendation Discipline (for JSON data)

These apply when generating the `theses` object in the JSON:

5. **Never recommend "activate" primarily because the thesis is exciting.** Conviction comes from data support and mechanism clarity, not from how dramatic the potential payoff is.

6. **"Watch" is not a hedge against making a call.** If the honest assessment is "discard," say discard. Recommending "watch" on a weak thesis to avoid the discomfort of killing it is bias, not caution. Check: would you still recommend "watch" if the thesis narrative were boring? If the answer is no, the narrative is doing the work, not the data.

7. **Count the ratio.** If more than half of draft theses are recommended "activate" in a given week, step back and ask whether the bar was applied consistently. High-conviction opportunities don't arrive in bulk. Similarly, if zero theses are recommended "discard" over a 4-week stretch, the discard bar may be too high.

8. **A thesis can have High conviction and still be "watch."** If the trigger hasn't fired, the timing isn't there. Conviction measures the quality of the idea. Activation measures readiness to act.

9. **The 3-week staleness rule is not optional.** After 3 weeks in Watch without a trigger firing, the only options are activate or discard. Do not reset the counter by minor rewording or by redefining the trigger.

### Narrative Discipline

10. **Don't build a narrative and then cherry-pick data to support it.** Build the narrative from the data. If you find yourself hunting for a confirming data point, stop and ask what the data actually says.

11. **When the data is mixed, say it's mixed.** Don't resolve ambiguity by choosing the more interesting narrative. "The data is genuinely conflicted this week" is a valid assessment that serves the reader better than false clarity.

12. **Regime continuity is not the default.** The regime stability principle (Skill 6) guards against whipsawing. But the memo must not treat continuity as inherently more likely than change. If the data is shifting, describe the shift honestly even if it hasn't crossed the 2-week confirmation threshold yet. "The data is moving toward Overheating but hasn't confirmed — here's what confirmation would look like."

13. **Past accuracy doesn't earn narrative credit.** If our regime call has been right for 8 weeks, that's useful context — but it doesn't make week 9's call more likely to be right. Each week's assessment stands on its own data.

---

## Language Standards — Enforced

The language quality is the single most important quality standard for this document. If the memo reads like a research report, it failed. If it reads like a newsletter from a sharp analyst who explains things clearly, it succeeded.

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
- No section longer than 3-4 paragraphs
- Data woven into prose — never in tables, never in bullet lists
- Every directional view includes specific ETF ticker(s) and a one-sentence justification, embedded in the narrative
- Thesis references connect to the week's data — don't mention a thesis just to check a box
- If the regime hasn't changed, say so conversationally — "Goldilocks for the sixth straight week" woven into the opening, not as a standalone badge
- Every number sourced — never invented
- Dynamic headlines that reflect this specific week — never generic template labels
