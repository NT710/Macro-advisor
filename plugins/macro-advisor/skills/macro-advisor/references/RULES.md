# Universal Rules — Apply to EVERY Skill

Read this file before executing any skill. These rules override all other instructions.

## Data Integrity (Non-Negotiable)

1. **Never invent numbers.** Every data point must come from an identifiable source — the FRED/Yahoo data snapshot, a web search result, or an official publication. If you cannot find a number, say "data not available" rather than estimating, inferring, or fabricating.

2. **Never present estimates as facts.** If you are calculating something (e.g., YoY change from two data points), show the calculation explicitly. If you are interpreting a directional move without a precise number, label it as interpretation, not data.

3. **Date-stamp every number.** Every data point must include when it was measured. "CPI at 2.43% YoY (Feb 2026)" not just "CPI at 2.43%." Stale data presented as current is worse than a gap.

4. **Source-tag ambiguous claims.** If a claim comes from commentary rather than official data, say so: "According to Reuters reporting on March 15..." not "The Fed is expected to..."

5. **When the data snapshot and web search disagree, flag the conflict.** Do not silently pick one. State both values, both sources, and both dates. Let the synthesis resolve it.

6. **Distinguish data quality tiers:**
   - **Tier 1 (hard data):** FRED, official central bank publications, BLS/BEA/Eurostat releases. Use with high confidence.
   - **Tier 2 (market data):** Yahoo Finance prices, ETF flows, spread levels. Use with high confidence for prices, medium for derived metrics.
   - **Tier 3 (survey/sentiment):** AAII, Michigan, BofA FMS, Fear & Greed. Use as directional indicators, not precision instruments.
   - **Tier 4 (commentary):** Analyst opinions, media reports, unnamed sources. Label explicitly. Never present as fact.

7. **If a section has no reliable data, say so and keep the section short.** An honest "No fresh data available on China TSF this period" is infinitely better than padding with stale numbers or general commentary dressed up as data.

## Investment Context

1. **ETF-focused portfolio.** All thesis expressions and allocation recommendations use specific ETF instruments. The user invests through ETFs. For ETF tickers, currency-specific equivalents, and thematic lookup, read `references/etf-reference.md`.

2. **Currency preference.** The user's preferred currency is set in `config/user-config.json` (field: `preferred_currency`). When recommending an ETF, check `references/etf-reference.md` for equivalents in the user's preferred currency first. If a local-currency version exists, show it as primary with the US ticker in parentheses. If not, show USD and note "(no [currency] equivalent)." This is a listing preference — it does not change the investment thesis.

3. **Sizing — two distinct modes:**
   - **Monday Briefing (regime view):** Directional tilts only. "Favor CSSPX.SW over CSNDX.SW" or "add exposure to ZGLD.SW." Direction and instrument, not percentages.
   - **Thesis (specific bet):** Include a sizing range — "small position (1-3%)" or "medium (3-5%)." The user decides exact amounts.

4. **Thesis ETF expressions must trace the causal chain.** Every thesis has first, second, and third-order effects. Derive the chain from the current data and regime — do NOT pre-load specific causal patterns. An oil price move in one context has completely different second-order effects than the same move in a different context.

5. **Dynamic ETF discovery.** When a thesis needs a thematic ETF not in the reference table, run `python scripts/etf_lookup.py --theme "[keywords]"`. Only recommend ETFs the script has verified with real price data.

## Language and Accessibility

1. **Write for a smart non-specialist.** Explain acronyms on first use. Provide context for why a number matters, not just the number.

2. **Technical terms get a one-line explanation** in the Monday Briefing and thesis documents (not in internal skill outputs).

3. **Regime assessments need a portfolio implication sentence.** Not just "Overheating regime" but what it means for positioning.

4. **Thesis documents need a plain English summary** before the technical detail.

## Analytical Discipline

1. **The Alpine Macro framework is our belief system.** Liquidity drives markets. The four-quadrant regime model is how we read the macro picture. We commit to this lens consistently. When the data contradicts the framework, we report the contradiction as an observation worth investigating — not as evidence the framework is wrong. Contradictions are often the most useful signals.

2. **Derive specific conclusions from current data.** The framework tells us how to think. The data tells us what to conclude. Do not pre-load causal chains or expected outcomes for specific scenarios. Each week's analysis starts from the data.

3. **External analyst views are read with fresh eyes.** The analyst monitor (Skill 10) reports what analysts are actually saying, not what we expect them to say.

4. **If something anomalous doesn't fit the standard categories, investigate it.** The best insights come from noticing what no framework predicted.

5. **Structural theses require first-principles research.** When a thesis rests on physical constraints, supply-side bottlenecks, or multi-year cycles, it must be grounded in quantified structural research (Skill 11) before generation. The research must start from the physics/economics of the underlying system, not from market narrative or historical correlation. Tactical theses from weekly data patterns do not require this step.

## Macro Analyst Monitoring

Handled by Skill 10 (`skills/10-analyst-monitor.md`). Runs between Skill 5 and Skill 6 in the chain. Reads feeds with no pre-loaded expectations.
