# Skill 14: Decade Horizon Strategic Map

## Objective

Map the 3–5 mega-forces shaping the global economy over the next decade, trace their causal chains through industries, and check the active thesis book for blind spots. This is a top-down strategic layer — it starts from forces, not from data. The structural scanner (Skill 13) works bottom-up: data → signal → thesis candidate. This skill works top-down: mega-force → causal chain → industry impact → positioning gap.

The purpose is NOT to generate theses directly. It is to provide strategic context that sharpens the scanner's interpretation, surfaces blind spots in the active thesis book, and ensures the system isn't over-indexed on the current cycle while ignoring slow-moving forces that will dominate the next 5–10 years.

---

## When to Run

**Quarterly, or on first-ever run.** At the start of the run, check `outputs/strategic/last-horizon.json` for `last_run_date`:
- If the file **doesn't exist** → this is the first run. Always proceed. Establishes baseline mega-force map and initial causal chains.
- If `last_run_date` is **fewer than 80 days ago** → skip entirely and note: "Decade horizon: last ran [date], skipping this cycle."
- If `last_run_date` is **80+ days ago** → proceed with quarterly update.

**Manual invocation:** Can be triggered via `/macro-advisor:investigate-theme` with a decade-horizon framing, or by the user asking for a strategic map update.

**Chain position:** Runs quarterly, BEFORE Skill 13 (structural scanner). When both run in the same cycle, Skill 14's output feeds into Skill 13's Phase 1 as supplementary context — it does NOT replace the scanner's data-first detection. The scanner still runs its own signals independently.

---

## Data Access

Skill 14 uses a different data mix than the weekly or structural skills. The decade horizon operates on slow-moving variables — demographics, energy transitions, technology adoption curves, fiscal trajectories, geopolitical structural shifts — where the relevant data often comes from institutional reports rather than high-frequency time series.

### 1. Existing system data (read first)
Read `outputs/data/latest-data-full.json` for any relevant long-run series. The 5-year snapshot provides useful trend context even for decade-scale analysis.

### 2. FRED long-run series (on-demand)
For demographic, fiscal, and structural series not in the weekly collection:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/research-temp/ --series "SERIES1,SERIES2" --mode historical
```

**Decade-relevant FRED series (illustrative — pull what the mega-force requires):**

*Demographics:*
- `LFWA64TTUSM647S` — Working age population (15-64)
- `SPPOPGROW` — Population growth rate
- `LNS11300060` — Prime-age labor force participation

*Fiscal trajectory:*
- `GFDEBTN` — Federal debt: total public debt
- `A091RC1Q027SBEA` — Federal interest payments
- `FYFSD` — Federal surplus/deficit
- `FDHBFIN` — Federal debt held by foreign investors

*Energy & Infrastructure:*
- `DCOILWTICO` — Crude oil WTI
- `GASREGW` — Regular gasoline price
- Available EIA data via web search for renewable capacity, grid interconnection queues

### 3. Web search (primary for this skill)
Decade-scale analysis relies heavily on institutional reports, government projections, and academic research. Sources to prioritize:
- **Demographics:** UN Population Division, national statistics offices, World Bank
- **Energy transition:** IEA World Energy Outlook, BloombergNEF, EIA Annual Energy Outlook, IRENA
- **Technology adoption:** Gartner, IDC, industry-specific S-curve data
- **Fiscal:** CBO long-term budget outlook, IMF Fiscal Monitor, BIS annual report
- **Geopolitical structure:** OECD, WTO trade statistics, World Bank governance indicators

### 4. Active thesis book
Read all files in `outputs/theses/active/` — the current thesis book is the blind-spot comparison baseline.

### 5. Previous horizon map
If `outputs/strategic/latest-horizon-map.md` exists, read it. The quarterly update should evolve the existing map, not rebuild from scratch each time.

---

## Phase 1: Mega-Force Identification

Identify 3–5 forces that will structurally reshape the global economy over the next decade. These are NOT themes or trade ideas. They are forces — large, slow, directional, and difficult to reverse.

### Selection Criteria

A mega-force must meet ALL of the following:

1. **Multi-year momentum.** The force has been building for at least 3 years and has measurable acceleration or deceleration. It is not a headline trend from the last quarter.
2. **Physical or demographic grounding.** The force is anchored in something that changes slowly — population structure, energy infrastructure, geological constraints, institutional architecture. Sentiment-driven forces do not qualify.
3. **Cross-sector impact.** The force affects at least 3 distinct sectors or asset classes through different causal mechanisms. A single-sector dynamic (however large) is a structural thesis, not a mega-force.
4. **Policy-resistant in the medium term.** Even aggressive policy intervention cannot fully reverse the force within 3–5 years. Policy can accelerate, decelerate, or redirect — but the force persists.

### Candidate Generation

Do NOT start with a pre-set list. Each cycle:

1. **Data scan FIRST.** Review the 5-year trend of key structural series (demographics, fiscal, energy, trade flows, technology adoption). Flag variables that show persistent directional drift (not cyclical oscillation). Form your initial candidate list from the data BEFORE reading institutional reports. This prevents anchoring to whatever the IEA or IMF currently emphasizes.
2. **Institutional report scan SECOND.** Web search for the latest IEA, CBO, UN Population, BIS, and IMF flagship reports (annual or semi-annual). Extract their top structural concerns. These are well-resourced analytical shops — their consensus deserves a read, even if we ultimately disagree. Compare their concerns against your data-derived candidates. Note which forces appear in both (convergence) and which appear only in one (potential blind spot on either side).
3. **Contrarian source scan.** Deliberately search for structural forces that are NOT in the institutional consensus: "[current year] underappreciated macro risk", "structural shift nobody is talking about", "overlooked demographic/energy/fiscal trend". The purpose is to counteract the anchoring effect of institutional reports. Most of these will be noise — but the process of looking prevents the mega-force list from simply tracking the IEA/IMF agenda.
4. **Previous map evolution.** If a mega-force from the previous quarter still meets all criteria, it stays. Forces don't appear and disappear quarterly. If a force no longer meets criteria (e.g., policy intervention has successfully reversed it), note the change and remove it with an explanation.
5. **Novel force check.** Is there a force meeting the criteria that the previous map missed? Technology displacement signals from Skill 13's Signal 7 can escalate to mega-force level if the adoption curve has crossed 10% AND the displacement chain spans 3+ sectors.

### Output Format per Mega-Force

```markdown
## Mega-Force [N]: [Name]

**Direction:** [Accelerating / Decelerating / Steady — with data]
**Time horizon:** [When did this start → when does it peak/plateau]
**Confidence in persistence:** [High / Medium / Low — with reasoning]
**Data anchor:** [The specific quantitative measure that grounds this force — not a narrative, a number with a source]
**Last quarter change:** [What's different from the previous horizon map, if anything]
```

---

## Phase 2: Causal Chain Mapping

For each mega-force, map the causal chain through three orders of impact. This is where the strategic value lives — most analysts see the force and the first-order impact. The second and third orders are where blind spots hide.

### First-Order Impacts (Direct)
Industries and asset classes directly affected by the mega-force. These are obvious and likely priced.

**Format:** [Force] → [Direct industry/sector impact] → [Direction: positive/negative] → [Already in consensus: yes/no]

### Second-Order Impacts (Supply Chain & Adjacent)
Industries affected through supply chain dependencies, input costs, labor competition, regulatory spillover, or capital reallocation. These are less obvious and often mispriced.

**Format:** [First-order impact] → [Transmission mechanism] → [Second-order industry/sector] → [Direction] → [Consensus awareness: low/medium/high]

### Third-Order Impacts (Behavioral & Structural Shifts)
Changes in consumer behavior, capital allocation patterns, institutional structures, or policy regimes triggered by accumulated first and second-order effects. These are rarely priced because they haven't happened yet — they're implications of the chain, not observable data.

**Format:** [Accumulated lower-order effects] → [Behavioral/structural shift] → [Industry/asset class implications] → [Timeline: when does this become investable]

### Chain Quality Rules

- **Every link must have a transmission mechanism.** "This leads to that" is not a chain — "this leads to that BECAUSE [mechanism]" is. If you can't name the mechanism, the link is speculation.
- **Quantify where possible.** "Rising energy costs hurt manufacturing" is a narrative. "A 30% increase in industrial electricity costs reduces US manufacturing margins by 2–4 percentage points based on sector-average energy intensity of 8–12% of COGS" is a chain link.
- **Mark confidence per link.** First-order links should be high confidence. Third-order links will often be medium or low. That's fine — flag it, don't pretend.

---

## Phase 3: Thesis Book Blind Spot Analysis

Compare the causal chains from Phase 2 against the active thesis book.

### Step 1: Coverage Mapping
For each second and third-order impact identified in Phase 2, check: does the active thesis book have a thesis that covers this impact? Classification:

- **Covered:** An active thesis directly addresses this impact. Note which thesis.
- **Partially covered:** An active thesis touches the area but through a different mechanism or on a different timeline.
- **Blind spot:** No active thesis addresses this impact. This is the key output.

### Step 2: Blind Spot Prioritization
For each blind spot, assess:

1. **Investability:** Can this impact be expressed through liquid ETFs or instruments? If not, note it as strategic context but not actionable.
2. **Timeline to materiality:** When does this impact become large enough to move asset prices? If >5 years, it's context. If 1–3 years, it's a candidate for Skill 13 or Skill 11 investigation.
3. **Data availability:** Can we monitor this impact with available data? If we can't measure it, we can't build a thesis around it.

### Step 3: Recommendations
For each prioritized blind spot with timeline <3 years and available data:
- **Flag for Skill 13:** If the impact involves a supply-demand imbalance or structural constraint → suggest it as a domain for the scanner's next cycle.
- **Flag for Skill 11:** If the impact requires deep first-principles research → suggest direct Skill 11 investigation.
- **Flag for monitoring only:** If the impact is real but not yet investable → add to a watch list with a trigger condition (e.g., "becomes actionable when X crosses Y threshold").

**Zero blind spots is a valid outcome.** If the active thesis book adequately covers the second and third-order impacts of the current mega-forces, report: "No actionable blind spots identified this quarter. Thesis book coverage is adequate for the current mega-force map." Do NOT manufacture blind spots to justify the skill's existence. The skill adds value even when it confirms coverage — that confirmation prevents false complacency in quarters when it does find gaps.

---

## Phase 4: Contrarian Stress Test

The decade horizon is particularly vulnerable to narrative capture — these are big, compelling stories that feel true. Apply these checks:

### 1. Consensus Saturation Check
For each mega-force, search: "[force] investment thesis [current year]", "[force] ETF", "[force] crowded trade"

If a mega-force is already a consensus trade (e.g., "AI will change everything" in 2024-2025), it doesn't mean the force is wrong — it means the FIRST-ORDER impacts are priced. The strategic value shifts to second and third-order impacts where consensus hasn't reached yet. Note the consensus saturation level explicitly.

### 2. Historical Base Rate
For each mega-force, find a historical analogue. How did similar forces play out?
- **Technology displacement:** How long did previous technology transitions actually take vs. projections at the time? (Hint: almost always longer than contemporaneous projections.)
- **Demographic shifts:** How did Japan's aging, China's one-child policy aftermath, or Europe's immigration waves actually affect asset prices vs. projections?
- **Energy transitions:** How did coal→oil, oil→gas transitions actually unfold vs. predicted timelines?

The purpose is NOT to dismiss the current force. It's to calibrate the timeline. Most mega-forces are real but slower than projected.

### 3. Scenario Inversion
For each mega-force, write one paragraph articulating the scenario where this force stalls, reverses, or fails to produce the expected impacts. What would have to be true? Is that scenario plausible?

If you cannot write a credible inversion scenario, you're in narrative capture territory. Every force has a failure mode. Find it.

---

## Output Files

- **Horizon map:** `outputs/strategic/YYYY-QN-horizon-map.md` — full output including all phases
- **Latest symlink:** Copy to `outputs/strategic/latest-horizon-map.md` (overwrite) — this is what other skills read
- **Blind spot candidates:** Each actionable blind spot is ALSO saved to `outputs/strategic/blind-spots/BLINDSPOT-[slug]-[date].md` — Skill 13 and Skill 7 read these
- **Last-run tracker:** Update `outputs/strategic/last-horizon.json`:
```json
{
  "last_run_date": "YYYY-MM-DD",
  "last_run_quarter": "YYYY-QN",
  "mega_forces_mapped": ["list of force names"],
  "mega_forces_changed": ["list of forces added/removed/upgraded/downgraded vs previous quarter"],
  "blind_spots_identified": 0,
  "blind_spots_actionable": 0,
  "blind_spots_flagged_for_scanner": 0,
  "blind_spots_flagged_for_research": 0
}
```

---

## Interaction with Other Skills

### Feeds INTO:
- **Skill 13 (Structural Scanner):** Blind spots flagged for scanner become supplementary context for Phase 1 signal detection. The scanner reads `outputs/strategic/blind-spots/` at the start of each cycle. This does NOT override the scanner's data-first approach — it adds "areas to look more carefully" without pre-loading conclusions.
- **Skill 7 (Thesis Generator):** Blind spots flagged for Skill 11 research enter Skill 7's investigation queue alongside data-pattern and analyst-sourced candidates. They share the 5-investigation cap.
- **Skill 11 (Structural Research):** A fifth trigger path — decade-horizon blind spot investigation — joins the existing four (data-pattern, analyst, scanner, manual).
- **Skill 9 (Monday Briefing):** When the horizon map updates (quarterly), the briefing includes a "Strategic Context" section summarizing the current mega-forces and any new blind spots.

### Reads FROM:
- **Skill 13 Signal 7 (Technology Displacement):** Displacement signals that span 3+ sectors may escalate to mega-force level in the horizon map.
- **Active thesis book:** Coverage comparison baseline.
- **Previous horizon map:** Ensures continuity rather than quarterly reinvention.

---

## Confirmation Bias Architecture

The decade horizon faces a different bias profile than the weekly or structural skills. The risk is not finding too many things (the scanner's problem) — it's falling in love with big narratives and losing objectivity. These mitigations are mandatory.

### 1. The Inversion Requirement
Every mega-force must include a credible failure/reversal scenario (Phase 4, Check 3). If the analyst cannot articulate how the force could fail, the force is being treated as destiny rather than probability. Destiny-framing is the hallmark of narrative capture.

### 2. Timeline Discipline
Every causal chain link must include a timeline estimate. "Eventually" is not a timeline. Historical base rates (Phase 4, Check 2) are the calibration tool. If the projected timeline for an impact is faster than the historical base rate for similar transitions, the faster timeline requires specific evidence — not optimism.

### 3. Consensus Awareness
Every mega-force and every first-order impact must include a consensus saturation assessment. The strategic value of the horizon map comes from second and third-order impacts — if the output is dominated by first-order consensus views, the skill is not adding value. Track: what percentage of identified impacts are in consensus vs. novel? Target: >50% of actionable blind spots should be second or third-order.

### 4. Force Stability Tracking
Track how often mega-forces change between quarters. A healthy horizon map is STABLE — mega-forces should persist for years, not rotate quarterly. If more than 1 force changes per quarter (added/removed/fundamentally revised), the selection criteria may be too loose or the analyst is chasing headlines.

Report: "Force stability: [N]/[total] mega-forces unchanged from previous quarter. [Changes described]."

### 5. Blind Spot Conversion Rate
Track what happens to flagged blind spots over time. Record in `last-horizon.json`:
```json
"historical_conversion": {
  "total_blind_spots_flagged": 0,
  "became_scanner_candidates": 0,
  "became_research_investigations": 0,
  "became_active_theses": 0,
  "remained_on_watch_list": 0,
  "dismissed_as_irrelevant": 0
}
```
If blind spots never convert to theses, the horizon map may be too abstract. If they all convert, the map may be too tactical (duplicating the scanner). A healthy conversion rate is 20–40% over 4 quarters.

---

## What This Skill Does NOT Do

- **Generate theses.** It identifies blind spots and provides strategic context. Theses come from Skill 7 via the existing pipeline.
- **Replace the structural scanner.** The scanner is bottom-up and data-driven. This skill is top-down and framework-driven. They complement each other. Neither replaces the other.
- **Predict the future.** It maps forces and traces chains of impact. The chains are hypotheses about transmission, not forecasts about outcomes.
- **Run weekly.** Mega-forces don't change weekly. Quarterly cadence prevents over-analysis and narrative drift.
- **Override the data.** If the decade horizon says "energy transition will dominate" but the scanner sees no energy supply-demand tension in the data, the data wins. The horizon map adds context — it doesn't overrule quantitative signals.

---

## Meta Block

```yaml
---
meta:
  skill: decade-horizon
  skill_version: "1.0"
  run_date: "[ISO date]"
  run_type: "[scheduled | manual | first-run]"
  execution:
    mega_forces_mapped: [number]
    mega_forces_unchanged: [number]
    mega_forces_added: [number]
    mega_forces_removed: [number]
    causal_chains_traced: [number]
    blind_spots_identified: [number]
    blind_spots_actionable: [number]
    blind_spots_flagged_scanner: [number]
    blind_spots_flagged_research: [number]
  confirmation_bias:
    inversion_requirement_met: [true/false]
    timeline_discipline_applied: [true/false]
    consensus_novel_ratio: "[consensus%] / [novel%]"
    force_stability: "[N unchanged] / [total] — [stable/volatile]"
    historical_conversion_rate: "[converted/total] = [%]"
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues — data gaps, uncertain chains, forced additions]"
---
```
