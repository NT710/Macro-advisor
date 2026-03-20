# Skill 1: Central Bank Watch

## Objective

Track monetary policy decisions, forward guidance, and balance sheet operations across the five central banks that drive global liquidity. Produce a concise assessment of what changed, what didn't, and what it means for the liquidity regime.

## Central Banks to Cover

1. **Federal Reserve (Fed)** — rates, dot plot, QT pace, RRP facility, TGA balance
2. **European Central Bank (ECB)** — rates, APP/PEPP reinvestments, TLTROs
3. **Swiss National Bank (SNB)** — rates, FX intervention signals
4. **Bank of Japan (BoJ)** — YCC adjustments, rate normalization path
5. **People's Bank of China (PBoC)** — MLF/LPR rates, RRR cuts, FX policy

## Execution Steps

1. Search for official central bank statements, press conferences, and policy decisions from the past 7 days
2. Search for FOMC minutes, ECB accounts if released this week
3. Search for Fed and ECB balance sheet data (weekly releases)
4. Search for market pricing of future rate moves — Fed funds futures, ESTR forwards, OIS curves
5. Search for analyst commentary on any policy shifts or surprises
6. Synthesize findings into the output format below

## Search Strategy

Use these search patterns (replace [YEAR] with current year). Sources are tiered by rate-limit resilience.

### Tier 1: High-confidence, rate-limit friendly (search directly)
- "Federal Reserve FOMC [month] [YEAR] decision statement"
- "FOMC minutes [month] [YEAR]"
- "Fed balance sheet weekly [YEAR]" (cross-check with data snapshot: fed_total_assets_T)
- "Fed funds futures rate expectations [month] [YEAR]"
- "ECB interest rate decision [month] [YEAR] Lagarde"
- "ECB reinvestment policy [YEAR]"
- "SNB monetary policy assessment [month] [YEAR]"

### Tier 2: Rate-limit prone — use fallback strategy
**Bank of Japan:**
1. Primary: Search "Reuters Bank of Japan policy [month] [YEAR]" (Reuters Japan desk, not BoJ.or.jp directly)
2. Fallback: Search "Bloomberg Bank of Japan rate decision [YEAR]"
3. If both rate-limited: Document last known policy settings and mark as stale:
   "[Last known BoJ policy: [rate/YCC target/guidance], updated [date]. Real-time update unavailable due to search constraints. Manual check of boj.or.jp recommended.]"

**People's Bank of China:**
1. Primary: Search "China central bank MLF LPR rate [month] [YEAR] chinadaily OR xinhua" (English-language aggregators, not pbc.gov.cn directly)
2. Fallback: Search "PBOC monetary policy [month] [YEAR] Reuters"
3. If both rate-limited: Document last known settings:
   "[Last known PBoC policy: MLF [rate], 1Y LPR [rate], 5Y LPR [rate], updated [date]. Real-time update unavailable. Manual check of pbc.gov.cn recommended.]"

### General rules
- Prioritize: Reuters, Financial Times, WSJ, Bloomberg summaries. These are well-indexed and less prone to rate-limiting than official central bank domains.
- Discard opinion pieces unless they contain specific data.
- For BoJ and PBoC: a 1-3 day old Reuters summary is better than a gap. Accept the freshness trade-off.

### Amendment log
- v1.1 (2026-W12, A-2026W12-001): Added tiered search strategy with fallback sources for BoJ and PBoC. Root cause: web search rate-limiting on Asian central bank domains dropped search effectiveness to 0.42. Expected impact: ratio from 0.42 → 0.75+.

## Output Format

```markdown
## Central Bank Watch — [Date]

### What Changed
[Bullet list of actual policy actions or guidance shifts this period. If nothing changed, state that explicitly.]

### What Didn't Change But Was Expected To
[Market expectations that were not met. Sometimes the non-event is the signal. If nothing expected, state "No unmet expectations this period."]

### Market Pricing vs. Reality
[Current implied rate paths vs. stated guidance. Where is the gap? Include specific numbers where available — e.g., "Fed funds futures imply 75bp of cuts by Dec, vs. dot plot median of 50bp."]

### Forward Signal
[What to watch for at the next meeting / in the next 2 weeks. Specific dates and events.]

### Regime Implication
[One sentence: does this reinforce or challenge the current liquidity regime assessment?]
```

## Quality Standards

- Every claim about policy action must reference a specific date and source
- Market pricing must include actual numbers, not vague descriptions
- If a central bank had no news this period, say so in one line — don't pad with stale information
- The "Regime Implication" must take a position, not hedge

## Meta Block

Append this YAML block at the end of every output:

```yaml
---
meta:
  skill: central-bank-watch
  skill_version: "1.1"
  run_date: "[ISO date]"
  execution:
    searches_attempted: [number]
    searches_with_useful_results: [number]
    data_points_extracted: [number]
    data_points_expected: 18
  gaps:
    - "[list each data point you looked for but couldn't find fresh data on]"
  quality:
    self_score: [0.0-1.0, where 1.0 = all expected data found and fresh]
    confidence: [high/medium/low]
    freshest_source_date: "[date]"
    oldest_source_used: "[date]"
  notes: "[any issues encountered, e.g., 'BoJ English-language coverage sparse this week']"
---
```
