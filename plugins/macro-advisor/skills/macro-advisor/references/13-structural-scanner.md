# Skill 13: Structural Scanner

## Objective

Proactively find structural macro imbalances — multi-year supply-demand gaps, capex underinvestment cycles, demographic shifts, fiscal trajectories — that won't surface in the weekly data flow. The weekly chain (Skills 1-7) is reactive: it reads this week's data and finds patterns. This skill is proactive: it asks "what's quietly wrong and getting worse?" across the entire economy, without pre-selecting where to look.

This skill does NOT start from categories. It starts from quantitative tension signals and follows the data to whatever domain is stressed. The scanner finds the domains; it doesn't have them pre-assigned.

---

## When to Run

**Bi-weekly, as part of the Sunday chain.** At the start of the run, check `outputs/structural/last-scan.json` for the `last_run_date` field. If the last run was fewer than 12 days ago, skip entirely and note: "Structural scanner: last ran [date], skipping this cycle." If the file doesn't exist or `last_run_date` is missing, this is the first run — proceed.

**First setup run:** Always runs. Performs a full initial sweep (Phase 1 uses broader search). This establishes the baseline.

**Manual invocation:** Can be triggered via `/macro-advisor:structural-scan` at any time.

Chain position: runs after Skill 0 (data collection) but before Skill 6 (synthesis). Outputs are available for Skill 7 to consume as thesis candidates.

---

## Data Access

Skill 13 has access to the full toolkit. The structural scanner is a research skill — it should use whatever data source answers the question.

### 1. Existing weekly snapshot (read first — always)
Read `outputs/data/latest-snapshot.json` and `outputs/data/latest-data-full.json`. The snapshot contains 90+ series with up to 5 years of history. **Check here BEFORE web-searching or pulling additional data.** Do not web-search for data that's already in the snapshot.

**Structural-relevant series already in the weekly snapshot:**
- `INDPRO` — Industrial Production Index (growth proxy, cross-ref with capacity utilization)
- `BUSLOANS` — Commercial & Industrial Loans Outstanding (credit availability for capex)
- `PERMIT` — Building Permits (construction pipeline lead indicator)
- `HOUST` — Housing Starts (real activity, construction sector health)
- `MANEMP` — Manufacturing Employment (structural vs cyclical workforce shifts)
- `JTSJOL` — JOLTS Job Openings (labor market tightness by sector)
- `JTSQUR` — JOLTS Quits Rate (labor confidence indicator)
- Commodity prices: `GC=F` (gold), `CL=F` (crude oil WTI), `HG=F` (copper)
- Commodity futures curve shape: `snapshot.commodities.term_structure` (contango/backwardation — see section 2b)
- Inventory-to-sales ratios: `RETAILIRSA`, `MNFCTRIRSA`, `WHLSLRIRSA` (supply chain tightness)
- COT positioning data: net speculative positioning for gold, crude oil, copper, S&P 500, 10Y Treasury, EUR, JPY, GBP, CHF

### 2a. On-demand FRED pulls (for series not in the weekly collection)
The structural scanner can pull any FRED series that the weekly collection doesn't cover. Use the targeted mode:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/research-temp/ --series "SERIES1,SERIES2" --mode historical
```

**Structural series available on demand (NOT in weekly snapshot):**

*Capacity & Industrial:*
- `TCU` — Total capacity utilization (all industry, %)
- `CAPUTLB50001SQ` — Capacity utilization: manufacturing (%)
- `IPMINE` — Mining industrial production (extractive sector capacity)
- `AWHMAN` — Average weekly hours, manufacturing (labor utilization before hiring — when hours hit ceiling, capacity is maxed)

*Investment & Capex:*
- `PNRESCONS` — Private nonresidential fixed investment (capex proxy)
- `BOGZ1FL893065005Q` — Corporate business: capital expenditures
- `DGORDER` — Durable goods orders (forward capex indicator)
- `A679RC1Q027SBEA` — Private fixed investment: nonresidential structures (physical capex, not IP)

*Fiscal:*
- `FYFSD` — Federal surplus or deficit
- `FGEXPND` — Federal government expenditure
- `A091RC1Q027SBEA` — Federal government interest payments
- `GFDEBTN` — Federal debt: total public debt
- `FDHBFIN` — Federal debt held by foreign investors (external funding dependency)

*Demographics & Labor Structure:*
- `LFWA64TTUSM647S` — Working age population (15-64)
- `LNS11300060` — Labor force participation rate (25-54, prime-age — strips retirement noise)
- `CES0500000017` — Real average hourly earnings (wage vs inflation pressure)

*Price Signals for Bottlenecks (illustrative — not exhaustive):*
- `PCU3336133361` — PPI: Turbine and power transmission equipment (grid/energy bottleneck pricing)
- `WPU0561` — PPI: Industrial electric power (grid stress pricing)
- `PCU2122212122` — PPI: Copper ore mining (upstream extraction cost)

This list covers energy/grid/mining bottlenecks. If Phase 1 flags a different sector, search FRED for relevant PPIs: "[sector] producer price index FRED". The scanner should pull PPI series relevant to whatever domain is flagged, not only the pre-listed ones.

Log every additional series pulled in the output meta block.

### 2b. Commodity Futures Curve Shape (derived from weekly data)
The data collector computes contango/backwardation signals for key commodities from front-month vs. deferred futures prices. Available in the snapshot at `snapshot.commodities.term_structure.[commodity]`:
- `term_structure`: "backwardation" (near > far, supply tight) or "contango" (far > near, supply adequate)
- `spread_pct`: magnitude of the curve shape
- `trend_4w`: direction of curve shape change over 4 weeks

**Interpretation for structural scanning:**
- Persistent backwardation (4+ weeks) = market pricing current physical tightness
- Deepening backwardation = tightness worsening, inventories likely drawing
- Contango → backwardation flip = structural shift in supply adequacy
- Use as quantitative backbone for Signal 3 BEFORE web-searching for inventory data

### 3. EIA Petroleum & Energy Data
The data collector fetches key EIA series for energy structural analysis. Available in the snapshot at `snapshot.energy`:
- `crude_inventory_mbbls` — US commercial crude oil inventories (million barrels)
- `spr_inventory_mbbls` — Strategic Petroleum Reserve level (million barrels)
- `refinery_utilization_pct` — US refinery capacity utilization
- `days_of_supply` — US crude oil days of supply (inventory / daily consumption)

**Interpretation for structural scanning** (thresholds calibrated 2025-03, based on 2022-2025 ranges — Skill 8 should revisit if macro regime shifts):
- SPR below 400M barrels = reduced strategic buffer (pre-2022 baseline ~600M; post-drawdown range ~350-400M)
- Days of supply below 25 = tight market (DOE typical range: 20-30 days; sub-20 is historically rare)
- Refinery utilization above 93% = approaching physical ceiling (nameplate max ~97%; sustained >95% is unusual)

### 4. BIS Credit Data (international structural context)
The data collector fetches BIS credit-to-GDP gap data for cross-country structural comparison. Available in the snapshot at `snapshot.international_structural`:
- `credit_gap_us` / `credit_gap_xm` / `credit_gap_cn` / `credit_gap_jp` / `credit_gap_gb` — BIS credit-to-GDP gap (deviation from long-term trend, percentage points)
- Each entry includes: `credit_gap_pp`, `signal`, `direction` (widening/narrowing/stable), `date`

**Interpretation for structural scanning:**
- Credit gap > +10pp = overheating credit cycle, eventual deleveraging risk
- Credit gap < -10pp = depressed lending, structural demand gap
- Widening gap for 2+ consecutive quarters = trajectory accelerating

**Note:** IMF fiscal data (debt-to-GDP, fiscal balance) is not yet available as structured data. Use FRED fiscal series for US data and web search for international fiscal comparisons. The BIS credit gap partially covers the international structural picture.

### 5. ECB and Eurostat endpoints
Available via the data collector for European structural data. Same access as Skills 1-5.

### 6. ETF and price data
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/etf_lookup.py --theme "[keywords]"
```

### 7. Web search (supplementary, not primary)
Industry reports, government statistical publications (EIA, USGS, IEA, IMF, OECD), company filings, geological surveys, demographic databases, engineering assessments.

**IMPORTANT: Web search is now supplementary, not primary.** The scanner should exhaust quantitative data sources (sections 1-6) before web-searching. Web search is for context, color, and domains not covered by structured data. The hierarchy is: snapshot data → on-demand FRED → EIA/BIS/IMF → web search. This prevents media narratives from substituting for actual data.

---

## Phase 1: Tension Signal Detection

**The core question: "Where in the global economy is there a measurable gap between supply and demand, investment and requirement, or policy and reality — that would take more than 12 months to close?"**

This phase does NOT start from a domain list. It starts from quantitative signals that are domain-agnostic. Run each signal detector below and see what comes back. The output of Phase 1 is a list of flagged domains — NOT a list of theses.

### Signal 1: Capacity Utilization Stress
Pull `TCU` (total capacity utilization) and `CAPUTLB50001SQ` (manufacturing) from FRED.
- If utilization is above 80% AND trending up over 8 weeks → flag the sector
- Cross-reference with the snapshot's industrial production data (INDPRO)
- Web search for sector-level capacity constraints where aggregate utilization is high

**What this catches:** Industries running hot with no new capacity in the pipeline. When utilization is above 80%, supply constraints start binding and price pressures build.

### Signal 2: Capex/Revenue Divergence
Web search (pass 1 — broad): "capital expenditure decline [current year]", "infrastructure investment gap", "capex underinvestment [current year]"
Web search (pass 2 — narrative exclusion): Repeat the search but exclude the top 2-3 narratives from pass 1. E.g., if pass 1 returns mostly AI infrastructure and energy transition results, search: "capex underinvestment [current year] -AI -energy -semiconductor" to surface less-discussed sectors. This counters the tendency for web search to return whatever the financial media is currently amplifying.
- Look for industries where capex is declining relative to revenue or demand growth
- Look for government infrastructure reports identifying investment gaps
- Look for industries where replacement capex has been deferred

**What this catches:** The generic signature of underinvestment. A sector spending less on capacity while demand grows is building a future supply deficit.

### Signal 3: Commodity Inventory Depletion (data-first)

**Step 1 — Quantitative scan (no web search yet):**
Read from the snapshot in this order:
1. `snapshot.energy.days_of_supply` — if below 25, flag crude oil
2. `snapshot.energy.spr_inventory_mbbls` — if below 400M barrels, flag strategic buffer depletion
3. `snapshot.energy.refinery_utilization_pct` — if above 93%, flag refinery capacity ceiling
4. `snapshot.commodities.momentum.[commodity]` — any commodity in `strong_uptrend` with `pct_above_26w_ma > 15%` → flag as demand-pull or supply-constrained
5. `snapshot.commodities.term_structure` — any commodity in persistent backwardation → flag as physically tight
6. `snapshot.commodities.inventory_to_sales` — any sector with `signal: "drawing"` (8-week contraction bias) → flag supply chain tightness
7. COT positioning: `snapshot.positioning.[commodity]` — extreme net long speculative + rising price = crowded supply-tightness trade

**Ambiguity band rule:** If any metric in items 1-4 is within 10% of its trigger threshold, treat the signal as ambiguous rather than confirmed. Specifically: days-of-supply between 22.5 and 27.5, SPR between 360M and 440M, refinery utilization between 83.7% and 93%, or `pct_above_26w_ma` between 13.5% and 16.5%. For ambiguous signals, proceed to Step 2 but weight the challenge search equally with the confirming search — do not enter Step 2 with a directional view. Note "AMBIGUOUS — near threshold" in the Phase 1 output. (Calibration: thresholds set 2025-03, based on 2022-2025 ranges. Skill 8 should revisit if macro regime shifts materially.)

**Step 2 — Context and challenge search (only for flagged commodities):**
For each commodity or sector flagged by the quantitative scan above:
Web search (confirming): "[commodity] inventory levels [current year]", "[commodity] days of supply", "USGS mineral commodity summaries [commodity]"
Web search (challenging): "[commodity] oversupplied [current year]", "[commodity] demand declining [current year]", "[commodity] bear case"
- The purpose of Step 2 is to contextualize AND challenge the quantitative signal, not to confirm it
- Confirm whether the quantitative signal reflects a real inventory drawdown or a technical artifact
- Look for the *physical* inventory data that the price/momentum signals are pointing to
- Cross-reference: if price is flat but quantitative signals show tightness → market isn't pricing the depletion (highest value finding)

**Note:** EIA energy data (Step 1, items 1-3) covers US inventories only. For global oil supply assessments, web search for IEA global inventory data and OECD commercial stocks. A US-tight / global-comfortable reading changes the thesis materially.

**Step 3 — Non-energy commodities without snapshot data:**
For commodities not covered by EIA or Yahoo (lithium, rare earths, uranium, agricultural commodities):
Web search: "strategic reserves depletion [current year]", "[commodity] supply deficit", "USGS mineral commodity summaries [current year]"
- These rely on web search because no structured data feed exists. Note the lower confidence level in the output.

**What this catches:** Supply-demand gaps that haven't hit price yet. Inventories buffer the gap temporarily, but when they're gone, price adjusts violently. The data-first approach prevents media narratives from substituting for actual inventory data.

### Signal 4: Demographic Trajectory Breaks
Pull `LFWA64TTUSM647S` (working age population) from FRED if available.
Web search: "working age population decline [current year]", "dependency ratio [major economies]", "labor shortage structural [current year]"
- Look for economies where working-age population is declining faster than productivity growth
- Look for dependency ratio thresholds being crossed
- Look for immigration policy shifts that affect labor supply

**What this catches:** Demographic constraints that take decades to resolve. When a country's working-age population shrinks, no policy response short of mass immigration or automation reverses it within a decade.

**Staleness rule:** Demographics move slowly. If the FRED data has not materially changed since the last scan AND no new policy development (immigration reform, automation acceleration, retirement age change) was found in web search, record: "Signal 4: No NEW structural tension detected — prior finding still valid, data unchanged." This counts as empty for the emptiness ratio. Repeating the same finding with the same numbers is not a new detection.

### Signal 5: Fiscal Trajectory Stress
**Step 1 — Quantitative scan:**
Pull fiscal series from FRED: `FYFSD` (deficit), `FGEXPND` (expenditure), `A091RC1Q027SBEA` (interest payments), `GFDEBTN` (total debt).
Read BIS credit gap data from snapshot: `snapshot.international_structural.credit_gap_[country]`
- If any country's credit gap is >+10pp ("overheating") or <-10pp ("depressed"), flag it
- If credit gap direction is "widening" for 2+ consecutive quarters, flag the trajectory

**Step 2 — Context search:**
Web search: "sovereign debt maturity wall [current year]", "government interest expense percent revenue", "fiscal sustainability [major economies]"
- Calculate interest payments as % of revenue (from FRED data)
- Look for economies where interest expense is growing faster than revenue
- Look for refinancing walls — large volumes of debt maturing in compressed windows

**What this catches:** Fiscal dynamics that compound over years. A government spending 15% of revenue on interest at 4% rates faces a very different fiscal reality than at 2% rates, and the maturity structure determines when reality bites.

**Staleness rule:** Fiscal trajectories shift quarterly, not weekly. If the FRED fiscal series are unchanged since the last scan AND no new fiscal policy, debt issuance event, or rating action was found in web search, record: "Signal 5: No NEW structural tension detected — prior finding still valid, data unchanged." This counts as empty for the emptiness ratio.

### Signal 6: Lead Time and Bottleneck Extension
Web search: "permitting timeline increase [current year]", "construction lead time [current year]", "supply chain bottleneck [current year]", "interconnection queue backlog"
- Look for industries where project timelines are extending
- Look for regulatory or physical bottlenecks that add years to development cycles
- Look for any sector where the gap between "demand signal" and "supply response" has widened due to permitting, construction, or approval timelines

**What this catches:** The invisible constraint. When it takes 5 years to get a permit that used to take 2, the supply response to price signals is 3 years slower than the market assumes.

### Signal 7: Technology Displacement

This signal is the mirror image of Signals 1-6. Those detect supply constraints — things running out. This detects demand destruction — things being made obsolete. The question: "Where is a technology crossing an adoption or cost threshold that will structurally destroy demand for an incumbent industry within the next decade?"

**Why this matters for macro positioning:** Technology displacement creates simultaneous long and short opportunities. The adopting sector faces supply constraints (which Signals 1-6 may catch). The displaced sector faces demand destruction (which nothing else in the scanner detects). The market typically prices the adoption side early and the displacement side late — because incumbents have revenue today and nobody wants to call the timing on decline.

**Step 1 — Adoption curve quantitative scan:**
Web search: "technology adoption rate [current year]", "S-curve adoption inflection [current year]", "market penetration rate by technology"
- Identify technologies between 10-30% adoption — this is the S-curve inflection zone where adoption accelerates non-linearly
- Pull adoption percentage AND growth rate. A technology at 20% adoption growing at 40% CAGR has different structural implications than one at 20% growing at 5%
- Focus on technologies with physical-world implications (energy, transport, manufacturing, infrastructure) — not pure software cycles, which resolve too fast to be structural

**Adoption data discipline:** Adoption percentages must come from institutional or industry sources (IEA, BloombergNEF, IDC, government statistics), not from technology vendors or advocacy organizations. When two credible sources disagree on adoption rate by >5 percentage points, report both figures and use the lower one for threshold decisions. "Adoption" means installed base or active use, not units shipped or orders placed — distinguish these explicitly.

**Quantitative thresholds:**
- Adoption rate 10-30% AND CAGR >20% → flag for displacement analysis
- Cost parity crossover within past 24 months (new technology now cheaper per unit than incumbent) → flag
- Regulatory forcing function with binding timeline (e.g., ICE vehicle bans, emissions standards, building codes) → flag the displaced sector

**Expected signal frequency:** Structural technology displacements at the S-curve inflection point are rare — perhaps 2-3 per decade reach macro-relevant scale. If Signal 7 flags a new displacement every cycle, the thresholds are too loose or the analyst is being drawn to technology narratives. A healthy pattern is Signal 7 returning empty most cycles, with periodic updates on previously flagged displacements when new adoption data arrives.

**Step 2 — Incumbent resilience check FIRST (mandatory — prevents narrative-driven displacement calls):**
Run this BEFORE mapping the displacement chain. The purpose is to prevent investing analytical effort into a compelling narrative that the data doesn't support. If the incumbent is thriving, the displacement hasn't started — regardless of how impressive the adoption curve looks.

**Step 2 reasoning:** An LLM will find displacement chain mapping intellectually engaging. By the time you've traced three orders of displacement, you're psychologically invested in the finding. Checking resilience first — before the chain is mapped — keeps the analyst honest. If Step 2 returns DEFER or DISMISS, skip Step 3 entirely.

Web search: "[incumbent industry] resilience", "[incumbent] demand growing [current year]", "[technology] adoption slower than expected"
- Check whether the incumbent's demand is actually declining, flat, or still growing
- Check whether the technology's cost advantage holds at scale or only in specific use cases
- Check for substitution limits — technical constraints that prevent the new technology from fully replacing the incumbent (e.g., battery energy density limits for long-haul aviation, intermittency limits for baseload power)

**Step 2 decision gate:**
- Incumbent demand flat or declining AND cost parity crossed → PROCEED to Step 3
- Incumbent demand still growing → note as EMERGING. Do not proceed. Re-check next cycle
- Strong substitution limits found → DEFER with specific note on what limits displacement. Skip Step 3

**Step 3 — Displacement chain mapping (only for technologies that passed Step 2):**
For each technology where the incumbent resilience check confirmed actual demand impact, trace the displacement chain:

1. **Direct displacement** (first-order): What product, service, or commodity does this technology directly replace? Quantify the addressable market of the incumbent. Web search: "[incumbent industry] market size", "[technology] vs [incumbent] total cost of ownership"
2. **Supply chain displacement** (second-order): What industries exist primarily to serve the incumbent? (e.g., auto parts for ICE vehicles, coal logistics for coal power, commercial real estate for office-based work). Quantify the revenue at risk. Web search: "[incumbent] supply chain", "[incumbent] adjacent industries revenue"
3. **Behavioral displacement** (third-order): What patterns of economic activity change when adoption reaches majority? (e.g., if remote work reaches 40%, what happens to business travel, urban commercial real estate, commuter rail?) These are the hardest to quantify but often the largest macro effects.

**Output decision:**
- Adoption in inflection zone AND Step 2 confirmed decline AND chain identifies macro-relevant sectors → flag as structural displacement candidate
- Chain reveals displacement confined to single niche → DEFER. Not yet macro-relevant

**What this catches:** The demand destruction side of structural shifts. Signals 1-6 find "what's running out." Signal 7 finds "what's being made unnecessary." Together they see both sides of the same structural transitions — the scanner can flag copper supply constraints (Signal 3) AND ICE vehicle demand destruction (Signal 7) as parts of the same electrification mega-force, rather than only seeing the supply side.

**What this does NOT do:** Signal 7 does not generate theses about technology winners. "AI will be huge" is not a structural scanner finding. The scanner's job is to find measurable imbalances with >12-month resolution timelines. Signal 7 finds the *losers* — the incumbent industries facing structural demand decline. The *winners* get captured by Signals 1-6 (the supply constraints created by new demand) or by the Decade Horizon Map (Skill 14), which provides the strategic context for why these shifts are happening.

**Staleness rule:** Technology adoption data updates quarterly at fastest. If the adoption percentages and cost curves have not materially changed since the last scan AND no new regulatory forcing function was announced, record: "Signal 7: No NEW displacement threshold crossed — prior findings still valid, data unchanged." This counts as empty for the emptiness ratio.

### Phase 1 Output

For each signal detector that returns a hit, write a brief flag:

```
TENSION SIGNAL DETECTED
Signal type: [which detector]
Domain: [what sector/theme the signal points to]
Quantified gap: [the number — not "large" or "significant" but the actual measurement]
Data source: [where the number came from]
Why >12 months: [what makes this structural, not cyclical]
```

**CRITICAL: The "nothing found" outcome is valid and expected.** If a signal detector returns no hits, write: "Signal [N]: No structural tension detected this cycle." Move on. Do NOT force a finding. At least 2 of the 7 detectors should return no finding on any given cycle — if all 7 fire every time, the detection thresholds are too loose.

**CONVERGENT SIGNALS:** If two or more detectors flag the same domain (e.g., Signal 1 finds copper capacity utilization at 87% AND Signal 3 finds copper inventory drawdown), count them as convergent evidence on ONE domain, not as separate findings. Convergence strengthens the candidate but does not inflate the signal hit rate. For the emptiness ratio, convergent signals count as one hit across however many detectors fired.

**DISPLACEMENT-SUPPLY CONVERGENCE:** Signal 7 may flag the same underlying structural force as Signals 1-6 but from the opposite side (e.g., Signal 3 flags copper supply constraints while Signal 7 flags ICE vehicle displacement — both driven by electrification). When this happens, note the convergence explicitly. These are high-value findings because they identify structural transitions where both the long side (supply-constrained adopter) and the short side (demand-destroyed incumbent) are investable. Route both sides to the same Skill 11 investigation rather than splitting into separate research briefs.

---

## Phase 2: Screening (only for flagged domains)

For each domain flagged in Phase 1, run three screening questions. The purpose is to filter out false positives before committing to deep research.

**Execution model:** Screens 1 and 3 run inline (quick web searches). Screen 2 is delegated to a dedicated subagent for each domain that passes Screen 1 — this is the most research-intensive screen and benefits from focused depth.

### Screen 1: The Equilibrium Question (inline)
"What market or policy mechanism is already working to resolve this gap, and how fast is it moving?"

Web search: "[domain] new supply coming online [current year]", "[domain] policy response [current year]"

If the answer is "prices have already risen enough to incentivize new supply and new supply is being built" or "policy has already shifted to address this" — the market may already be pricing the resolution. Note it and downgrade the signal.

If the answer is "nothing effective" or "the resolution mechanism takes longer than the gap timeline" — the signal is real. Proceed to Screen 2.

**Gate:** If Screen 1 downgrades the signal, skip Screen 2 (no subagent needed). Go directly to Screen 3 for consensus classification, then mark the domain as DEFER or DISMISS.

### Screen 2: The Base Rate Question (subagent — deep research)
"How many times in the last 30 years has this type of imbalance actually produced an investable multi-year move?"

**This screen is delegated to a subagent for research depth.** For each domain that passes Screen 1, launch an Agent with:
```
Agent tool call:
  subagent_type: "general-purpose"
  description: "Base rate research: [domain]"
  prompt: |
    Research the historical base rate for this type of structural imbalance:

    DOMAIN: [domain from Phase 1]
    IMBALANCE TYPE: [description of the gap — e.g., "capacity utilization above 80% in mining sector with declining capex"]
    QUANTIFIED GAP: [the number from Phase 1]

    Your task:
    1. Search for ALL historical episodes (last 30 years) where a similar imbalance existed — same type of gap, same order of magnitude. Include BOTH episodes that produced sustained price moves AND episodes where the gap resolved without a major move (demand destruction, substitution, unexpected supply, policy intervention). Non-events are equally important — they establish the true base rate. Aim for 3-5 episodes total across both categories. Use web search extensively.
    2. For each episode found (both hits and non-events), document:
       - What year and what sector/economy
       - How large the gap was at detection
       - How long it took to resolve (months/years)
       - Whether it produced an investable multi-year price move (>20% in the direction implied by the imbalance — e.g., upward for supply deficits, not just any 20% move)
       - What resolved it (market forces, policy, technology, demand destruction)
    3. If fewer than 2 historical episodes can be found (hits + non-events combined), state: "Insufficient historical precedent — base rate cannot be established."
    4. Calculate the base rate: of ALL episodes found (hits AND non-events), what percentage produced a directional multi-year investable move?
    5. Classify the resolution timeline:
       - Typically resolves in <2 years → likely CYCLICAL, not structural
       - Typically resolves in 2-5 years → STRUCTURAL but with known resolution path
       - Typically resolves in 5+ years or has never fully resolved → DEEP STRUCTURAL

    Return a structured summary with ALL episodes (hits and non-events), base rate percentage, timeline classification, and your confidence level (high/medium/low based on how many analogues you found and how close they are).

    Do NOT search for the current state of [domain] — only historical analogues. The current state is already known.
```

**Wait for the subagent to return before proceeding.** If multiple domains passed Screen 1, launch subagents in parallel.

**Interpreting subagent results:**
- If base rate is <30% (fewer than 1 in 3 similar gaps produced investable moves) → strong evidence against structural classification. Lean toward DEFER.
- If base rate is 30-60% → moderate support. Proceed but note the mixed precedent.
- If base rate is >60% → strong historical support for structural classification.
- If "insufficient historical precedent" → the domain does NOT auto-advance. It advances only if the quantified gap from Phase 1 is extreme (e.g., inventory at multi-decade lows, utilization at cycle highs, deficit at record levels relative to the domain's own history). If the gap is merely "notable but within historical range," DEFER with note: "Novel imbalance, insufficient base rate — needs stronger quantitative signal to advance without precedent." The risk of the novel-imbalance path is that any domain can be framed as unprecedented if described narrowly enough.
- If timeline classification is "CYCLICAL" → downgrade to DEFER regardless of base rate percentage.

### Screen 3: The Consensus Check (inline)
Web search: "[domain] consensus view [current year]", "[domain] widely discussed"

How well-known is this imbalance? Classify:
- **Niche:** Discussed by domain specialists, not in mainstream financial media. Highest potential edge.
- **Emerging:** Starting to appear in institutional research and macro commentary. Moderate edge.
- **Mainstream:** On the front page of the Financial Times and Bloomberg. In everyone's models. Edge is largely priced.
- **Consensus trade:** Actively being traded by the majority. Potential for crowded-exit risk.

A mainstream imbalance can still produce a thesis — if the market is pricing the wrong timeline or magnitude. But the consensus penetration level must be stated honestly. It directly affects conviction.

### Phase 2 Output: Advancement Decision

After screening, each flagged domain gets one of three outcomes:

- **ADVANCE** — Equilibrium mechanism is insufficient, base rate supports structural timeline (>30% or novel), and the imbalance is not fully priced. → Proceed to Phase 3.
- **DEFER** — Signal is real but equilibrium mechanisms are active OR base rate is weak (<30% or cyclical timeline) OR consensus is fully pricing it. → Log it. Re-check next cycle.
- **DISMISS** — False positive. The gap is cyclical, already resolving, or the data doesn't hold up. → Log reason. Don't re-flag unless new data emerges.

Include the subagent's base rate findings in the advancement decision. Quote the historical episodes — don't just state the percentage.

**Threshold:** No more than 3 domains should advance per cycle. If more than 3 pass screening, rank by: (1) size of quantified gap, (2) time to resolution, (3) distance from consensus. Take the top 3. The rest defer to next cycle.

---

## Phase 3: Structural Thesis Candidate Generation

For each domain that passed screening, produce a candidate for Skill 11 investigation. The candidate is a structured brief — not a thesis. Skill 11 does the deep research. Skill 7 formalizes the thesis.

```markdown
## STRUCTURAL SCANNER CANDIDATE

**Domain:** [e.g., "US power grid capacity vs. data center demand"]
**Detected via:** Signal [N] — [type] — [date]
**Provenance:** structural-scanner, [scan date]

### Identified Imbalance
[Quantified — e.g., "US grid interconnection queue is 2,600 GW vs. 1,250 GW of installed capacity. Average time from application to connection: 5 years. Meanwhile, data center power demand is projected to grow 15% annually through 2030."]

### Key Binding Constraint
[The physical/structural reality that prevents quick resolution — e.g., "Transformer manufacturing is bottlenecked at ~3-year lead time. Grid interconnection permitting averages 5 years. No amount of price signal accelerates these timelines."]

### What's Already Happening to Address This
[The equilibrium check — e.g., "Utilities are increasing grid capex by 12% annually. Three new transformer factories announced but not operational until 2028. FERC has proposed permitting reform but it's in comment period."]

### Consensus Penetration
[Niche / Emerging / Mainstream / Consensus trade — with evidence]

### Bear Case Inputs
[From the contrarian search — e.g., "AI demand growth may slow if model efficiency improves (see: Jevons paradox debate). Nuclear restarts could add significant baseload capacity faster than new build. Demand response technology could reduce peak load requirements by 10-15%."]

### Recommended Investigation Depth
[Full Skill 11 brief / Focused brief (1-2 binding constraints only) / Quick check]

### Data Sources Used
[Every source, with date. Be specific — "USGS Mineral Commodity Summaries 2025" not "USGS data"]

### Confidence in Data
- Institutional/government statistics: [which claims]
- Industry estimates: [which claims]
- Analyst projections: [which claims — lowest confidence]
```

---

## Phase 4: Contrarian Final Pass

**After generating all candidates, run one final check.** For each candidate, deliberately search for the opposite conclusion:

Web search: "[domain] oversupplied [current year]", "[domain] bear case", "[domain] no shortage", "[domain] demand declining"

If strong counter-evidence exists, it must be incorporated into the candidate's Bear Case Inputs. If the contrarian search finds a credible argument that fundamentally undermines the imbalance, downgrade the candidate from ADVANCE to DEFER and explain why.

If the contrarian search finds nothing credible, note: "Contrarian search found no substantive counter-argument. This is unusual — either the thesis is genuinely one-sided (rare) or the search terms were too narrow. Flagged for extra scrutiny in Skill 11."

---

## Output Files

- **Scan results:** `outputs/structural/YYYY-Www-structural-scan.md` — full output including all Phase 1 signals, Phase 2 screening, Phase 3 candidates, and Phase 4 contrarian checks
- **Individual candidates:** Each advancing candidate is ALSO saved to `outputs/structural/candidates/CANDIDATE-[domain-slug]-[date].md` — this is what Skill 7 and Skill 11 read
- **Last-run tracker:** Update `outputs/structural/last-scan.json`:
```json
{
  "last_run_date": "YYYY-MM-DD",
  "last_run_week": "YYYY-Www",
  "domains_scanned": ["list of flagged domains from Phase 1"],
  "domains_advanced": ["list of domains that passed screening"],
  "domains_deferred": ["list of deferred domains"],
  "domains_dismissed": ["list of dismissed domains"],
  "candidates_generated": 0,
  "signals_with_no_finding": 0,
  "total_signals_checked": 7
}
```

---

## Confirmation Bias Architecture

This skill is designed to find structural imbalances, which means it enters every cycle expecting to find problems. An LLM with this mandate will find problems everywhere — real or imagined. The following mitigations are mandatory, not optional.

### 1. The Emptiness Requirement
After all signal detectors run, count how many returned "no structural tension detected." If ZERO detectors returned empty, something is wrong — pause and re-evaluate whether the detection thresholds are too loose. A healthy ratio is 2-5 findings out of 7 detectors. Finding tension everywhere means the filter isn't filtering.

Report in the output: "Signal hit rate: [X]/7 detectors flagged tension. [Y] returned no finding."

### 2. The Contrarian Pass (Phase 4)
Already described above. Non-optional. Every candidate gets a deliberate search for the opposite conclusion.

### 3. Provenance Tracking
Every thesis that originates from the structural scanner carries `provenance: structural-scanner` through the entire pipeline (Skill 11 research brief → Skill 7 thesis → Skill 12 presentation → Skill 9 briefing). This allows performance tracking: do scanner-originated theses perform differently from weekly-data-originated ones?

### 4. Kill Rate Monitoring
Track how many scanner candidates survive Skill 11 research over time. Record in `last-scan.json`:
```json
"historical_kill_rate": {
  "total_candidates_generated": 0,
  "survived_skill_11": 0,
  "became_active_thesis": 0
}
```
If >80% of candidates survive Skill 11, the scanner's bar is too low. A healthy kill rate is 40-60%. Skill 8 (Self-Improvement) should monitor this metric and flag drift.

### 5. Domain Recurrence Tracking
Track which domains get flagged across cycles. If the same domain is flagged 3+ consecutive cycles, it's either a persistent real imbalance (check: is the quantified gap growing?) or the detector is stuck on a narrative (check: is the data actually changing, or are you finding the same numbers and calling it a new finding?).

Report: "Recurring domains: [domain] flagged [N] consecutive cycles. Gap trajectory: [growing/stable/shrinking]."

### 6. Sector Diversity Check
After Phase 1, check the distribution of flagged domains. If all findings cluster in one area (e.g., all commodities, all fiscal, all energy), the signal set may have a structural bias toward that type of imbalance. Note: "Findings clustered in [area]. Signal set may under-detect [other areas]. No forced diversification — but flag for review."

Do NOT force findings in underrepresented areas to achieve balance. That's worse than having a biased signal set. Just note the clustering so the user knows.

---

## What This Skill Does NOT Do

- **Generate theses.** It generates candidates for Skill 11 → Skill 7. The scanner does the initial "something is structurally stressed here" work.
- **Trade.** Structural imbalances are not timing signals. The scanner finds the thesis; the weekly cycle handles entry timing.
- **Replace the weekly flow.** Tactical theses from weekly data patterns are valid and different. The scanner adds a second input channel.
- **Pre-assign domains.** The scanner does NOT maintain a watchlist of sectors to research. It runs domain-agnostic signal detectors and follows whatever comes back. If the result is copper three cycles in a row, that's because the data says copper, not because copper is on a list.
- **Predict prices.** It identifies physical/structural constraints and asks whether the market is pricing them correctly. That's different from saying "copper will go to $15,000."

---

## Meta Block

```yaml
---
meta:
  skill: structural-scanner
  skill_version: "1.0"
  run_date: "[ISO date]"
  run_type: "[scheduled | manual | first-run]"
  execution:
    signals_checked: 7
    signals_with_findings: [number]
    signals_empty: [number]
    domains_flagged_phase1: [number]
    domains_advanced_phase2: [number]
    domains_deferred: [number]
    domains_dismissed: [number]
    candidates_generated: [number]
    additional_fred_series_pulled: ["list of series IDs"]
    recurring_domains: ["list with consecutive cycle counts"]
  confirmation_bias:
    emptiness_ratio: "[X]/7 — [healthy/suspicious]"
    contrarian_pass_completed: [true/false]
    sector_clustering: "[area or 'diverse']"
    historical_kill_rate: "[survived/total] = [%]"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues — data gaps, access failures, unusual findings]"
---
```
