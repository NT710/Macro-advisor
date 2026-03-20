# Skill 4: Geopolitical & Policy Scanner

## Objective

Track political and policy developments that create regime-change risk. Narrowed to policy actions with identifiable market transmission mechanisms. This is not a geopolitical news aggregator — it's a filter for policy changes that move asset prices.

## Core Principle

Most geopolitical noise doesn't change the macro regime. This skill exists to catch the exceptions: fiscal policy shifts, trade actions, regulatory changes, and political transitions that have direct, traceable effects on growth, inflation, or capital flows. If a development doesn't have a clear transmission mechanism to asset prices, it doesn't belong in the output.

## Coverage Areas

### Trade & Tariff Policy
- US tariff actions, executive orders on trade
- EU trade measures, anti-dumping duties
- China trade retaliation, export controls
- WTO disputes with economic significance

### Fiscal Policy
- US: budget negotiations, debt ceiling, spending bills, tax legislation
- EU: fiscal rules (Stability and Growth Pact), joint debt issuance
- China: stimulus packages, local government debt, property sector intervention
- Major fiscal expansions or contractions in G7

### Regulatory & Industrial Policy
- US: executive orders affecting industries, antitrust actions with market impact
- EU: competition policy, digital markets regulation, energy policy
- Technology regulation: AI regulation, semiconductor export controls, data governance

### Political Transitions & Elections
- Upcoming elections in major economies with policy implications
- Government formation, coalition changes, leadership transitions
- Political events that shift fiscal or monetary policy expectations

### Energy & Commodity Policy
- OPEC+ decisions and compliance
- Sanctions affecting energy supply (Russia, Iran, Venezuela)
- Strategic reserve releases or builds
- Energy transition policy (subsidies, mandates, carbon pricing)

### Swiss-Specific
- Bilateral agreements with EU (framework negotiations)
- SNB policy signals (FX intervention stance)
- Swiss tax policy changes
- Swiss financial regulation changes

## Execution Steps

1. Search for trade policy actions and tariff developments in the past 7 days
2. Search for fiscal policy developments (US, EU, China)
3. Search for regulatory actions with market impact
4. Search for geopolitical flashpoints affecting energy or trade flows
5. Search for upcoming elections or political transitions
6. Search for Swiss-specific policy developments
7. Filter: only include items with identifiable market transmission mechanisms
8. Synthesize into output format

## Search Strategy

### Tier 1: High-priority, high-confidence (search directly)
- "US tariff trade policy [month] [YEAR]"
- "US executive order economic [YEAR]"
- "US debt ceiling budget [YEAR]"
- "China stimulus property policy [YEAR]"
- "semiconductor export controls [YEAR]"
- "Switzerland EU bilateral [YEAR]"

### Tier 2: Rate-limit prone — use fallback strategy

**OPEC+ Production Decisions:**
1. Primary: Search "OPEC production decision [month] [YEAR]"
2. Fallback (if rate-limited): Infer from oil price action in the data snapshot. Oil price momentum (+/- week and month change) is a reliable proxy for whether OPEC+ surprised the market.
3. Document: "[OPEC+ decision specifics unavailable via search. Oil at $[price], [week_change]% WoW. Market pricing suggests [production support / demand shock / no surprise]. Last known decision: [date, output level]. Manual check of opec.org recommended.]"
4. Accept that specific OPEC+ guidance may be inferred from market behavior rather than sourced directly.

**EU Regulation Rollout:**
1. Primary: Search "EU DG Trade policy [month] [YEAR]" OR "EU regulation economic [month] [YEAR]"
2. Fallback (if rate-limited): Document as "[EU regulatory specifics unavailable. Recommend manual check of EU parliament calendar for [month] regulatory announcements.]"
3. De-prioritize to Medium severity. Tariff escalation risk (primary transmission mechanism) is captured via US trade policy searches. EU regulatory specifics are secondary.

**Sanctions:**
- Search "sanctions Russia Iran energy [YEAR]" once. If rate-limited, note: "[Sanctions status: no update available. Prior sanctions regime assumed unchanged unless oil/energy price action suggests otherwise.]"

### Tier 3: Lower priority (search if quota allows)
- "geopolitical risk markets [YEAR]"
- "elections [YEAR] economic policy"
- "fiscal policy G7 [YEAR]"

### General rules
Prioritize: government announcements, Reuters, FT, Politico (for EU), South China Morning Post (for China), Swiss info sources. For rate-limited searches, market price action from the data snapshot is an acceptable proxy for inferring whether a policy action surprised the market.

### Amendment log
- v1.1 (2026-W12, A-2026W12-003): Added tiered search with fallback for OPEC+, EU regulation, and sanctions. Root cause: 7 search failures from rate-limiting. Expected impact: eliminate 3 impossible searches, use market-inferred signals as proxy.

## Output Format

```markdown
## Geopolitical & Policy Scanner — [Date]

### Policy Actions With Market Impact
[Only include items with clear, identifiable transmission to asset prices. For each item:]
- **What happened:** [Specific action, date, who enacted it]
- **Transmission mechanism:** [How this affects growth, inflation, or capital flows]
- **Asset class most affected:** [Be specific — not "markets" but "European industrials" or "USD/CNH"]

[If nothing actionable this period, state: "No policy actions with direct market transmission this period."]

### Developments to Watch
[Policy directions that haven't hit markets yet but could within 2-4 weeks. Include probability assessment — likely, possible, unlikely but high-impact.]

### Regime Change Risk
[Is there anything here that could shift the macro regime? If yes, explain the mechanism. If not, state explicitly: "No regime-change risk identified this period."]

### Swiss-Specific
[Anything relevant to Swiss-domiciled portfolio or CHF exposure. If nothing, state: "No Swiss-specific developments."]
```

## Quality Standards

- Every item must include a specific transmission mechanism — "tensions rise" without an asset price channel is noise and gets excluded
- Date and source for every policy action
- Probability assessments for "developments to watch" must be explicit, not vague
- The regime change risk section must take a definitive position — yes or no, with reasoning
- Err on the side of a shorter, emptier output rather than padding with irrelevant geopolitical noise

## Meta Block

```yaml
---
meta:
  skill: geopolitical-policy-scanner
  skill_version: "1.1"
  run_date: "[ISO date]"
  execution:
    searches_attempted: [number]
    searches_with_useful_results: [number]
    policy_actions_identified: [number]
    items_filtered_as_noise: [number]
  gaps:
    - "[any known policy area not covered]"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
    freshest_source_date: "[date]"
    oldest_source_used: "[date]"
  notes: "[any issues]"
---
```
