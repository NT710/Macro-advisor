# Macro Investment Advisor — Methodology & System Reference

**Version:** 2.3
**Last Updated:** 2026-03-20
**Framework:** Alpine Macro methodology

---

## What This System Produces

The system makes three types of claims each week: regime calls (which macroeconomic quadrant are we in — Goldilocks, Overheating, Disinflationary Slowdown, or Stagflation), asset tilts (what to favor and avoid, expressed as specific ETFs), and thesis predictions (specific investment bets with explicit mechanisms, testable assumptions, and kill switches). Theses come in two depths: tactical (generated from weekly data patterns, weeks-to-quarters horizon) and structural (grounded in first-principles research on physical/economic constraints, quarters-to-years horizon). Everything runs on a Sunday, and the Monday briefing is the user-facing output.

---

## Core Methodology

### What We Believe (Alpine Macro Framework)

1. **Liquidity drives markets.** Changes in money supply, credit conditions, and central bank balance sheets are the primary transmission mechanism to asset prices. This is our analytical lens — we commit to it consistently. When the data contradicts it, we report the contradiction as an observation worth investigating, not as evidence the framework is wrong.

2. **Central banks are the key actors.** Their policy shifts (rate changes, balance sheet operations, forward guidance) are the most important signals to track.

3. **Positioning reveals vulnerability.** When consensus positioning is extreme, the risk/reward skews against it. Crowded trades unwind violently when the macro picture shifts.

4. **Regime identification over point forecasting.** The goal is to identify which regime we're in and which way it's turning. Asset allocation follows regime — but each instance is unique. The framework tells us how to think; the data tells us what to conclude. Regimes are structural conditions that persist for quarters or longer. A regime change requires confirmation across multiple data prints and a visible shift in the 6-month trend — not a single anomalous month.

5. **Contrarian framing is structural.** The question is always: what does the market believe, and what would have to be true for the market to be wrong?

### Four-Quadrant Regime Model

|                    | Inflation Falling | Inflation Rising |
|--------------------|-------------------|------------------|
| **Growth Rising**  | Goldilocks        | Overheating      |
| **Growth Falling** | Disinflationary Slowdown | Stagflation |

The regime label is the starting point. Asset implications are derived from each specific instance's data — credit conditions, positioning, policy stance, valuations — not read from a template. Two different Overheating regimes can look different.

---

## System Architecture

### Execution Chain (Single Sunday Run)

```
Skill 0:  Data Collection (FRED + Yahoo Finance → structured JSON)
Skill 1:  Central Bank Watch (Fed, ECB, SNB, BoJ, PBoC)
Skill 2:  Liquidity & Credit Monitor (M2, credit spreads, NFCI, Fed balance sheet)
Skill 3:  Macro Data Tracker (PMIs, employment, inflation, GDP, surprises)
Skill 4:  Geopolitical & Policy Scanner (trade, fiscal, regulatory, energy)
Skill 5:  Market Positioning & Sentiment (COT, flows, VIX, AAII, Fear & Greed)
Skill 10: External Analyst Monitor (Steno X feed + Alpine Macro LinkedIn via Chrome)
Skill 6:  Weekly Macro Synthesis (reads all above → regime assessment + sector view + 6/12M forecast)
Skill 7:  Thesis Generator & Monitor (reads synthesis + active theses + analyst insights)
Skill 11: Structural Research (first-principles research for structural theses — invoked on demand, not weekly)
Skill 8:  Self-Improvement Loop (observe → inspect → amend → evaluate + accuracy scoring)
Skill 12: Thesis Presentation (renders theses into visual reports + briefing cards + chart specs)
Skill 9:  Monday Morning Briefing (reads synthesis + theses + presentation cards + improvement → HTML dashboard)
```

Order: 0→1→2→3→4→5→10→6→7→11(if triggered)→8→12→9. Single scheduled task, Sundays at 16:00 CET.

### Data Foundation

**Skill 0 (data_collector.py)** runs before every analysis cycle, pulling 62+ series from two free institutional-quality sources. Every subsequent skill reads this structured data first. Web search is used only for qualitative context not available in structured form.

Two modes: `weekly` (26-week trailing history) for regular Sunday runs, `historical` (5 years) for regime comparison and first-ever run.

#### Source 1: FRED (Federal Reserve Economic Data)
Free API (key required). 42+ series covering:

**Money Supply:**
- US M2 Money Stock (weekly: WM2NS, monthly: M2SL)

**Fed Balance Sheet & Plumbing:**
- Fed Total Assets (WALCL) — tracks QT pace
- Treasury General Account / TGA (WTREGEN) — TGA draining = liquidity injection
- Reverse Repo Facility / ON RRP (RRPONTSYD) — RRP falling = liquidity injection
- Reserve Balances at Fed (WRESBAL)

**Interest Rates:**
- Fed Funds Effective Rate (DFF)
- Treasury Yields: 2Y (DGS2), 5Y (DGS5), 10Y (DGS10), 30Y (DGS30)
- Yield Curve Spreads: 10Y-2Y (T10Y2Y), 10Y-3M (T10Y3M)

**Credit Spreads:**
- ICE BofA US High Yield OAS (BAMLH0A0HYM2) — the primary credit stress indicator
- ICE BofA US Investment Grade OAS (BAMLC0A0CM)
- ICE BofA US HY Effective Yield (BAMLH0A0HYM2EY)

**Financial Conditions:**
- Chicago Fed NFCI (NFCI) — negative = loose, positive = tight
- Adjusted NFCI (ANFCI)
- St. Louis Fed Financial Stress Index (STLFSI4)

**Inflation:**
- CPI All Urban Consumers (CPIAUCSL)
- Core CPI ex Food & Energy (CPILFESL)
- PCE Price Index (PCEPI)
- Core PCE (PCEPILFE)
- 5-Year Breakeven Inflation (T5YIE)
- 10-Year Breakeven Inflation (T10YIE)
- U of Michigan Inflation Expectations (MICH)

**Employment:**
- Total Nonfarm Payrolls (PAYEMS)
- Unemployment Rate (UNRATE)
- Initial Jobless Claims (ICSA)
- Continuing Jobless Claims (CCSA)
- JOLTS Job Openings (JTSJOL)
- JOLTS Quits Rate (JTSQUR)

**Growth & Activity:**
- Real GDP (GDP, GDPC1)
- Industrial Production Index (INDPRO)
- Retail Sales (RSAFS)
- U of Michigan Consumer Sentiment (UMCSENT)

**Housing:**
- Housing Starts (HOUST), Building Permits (PERMIT)
- Existing Home Sales (EXHOSLUSM495S)
- Case-Shiller Home Price Index (CSUSHPISA)

**Leading Indicators:**
- Conference Board LEI (USSLIND)

#### Source 2: Yahoo Finance
Free, no API key required. 20+ tickers covering:

**Equity Indices:** S&P 500 (^GSPC), Nasdaq 100 (^NDX), Russell 2000 (^RUT), Euro Stoxx 50 (^STOXX50E)
**Volatility:** VIX (^VIX)
**Bond ETFs:** TLT (20+ Year Treasury), HYG (High Yield), LQD (Investment Grade)
**Commodities:** Gold (GC=F), Crude Oil WTI (CL=F), Copper (HG=F)
**Currencies:** EUR/USD, USD/JPY, USD/CHF, GBP/USD, USD/CNY, DXY (DX-Y.NYB)
**Regional ETFs:** EEM (Emerging Markets), EFA (EAFE)
**Money Markets:** SHV (Short Treasury)

#### Derived Signals (computed automatically)
The data collector computes higher-level signals from raw data:

- **Yield Curve State:** steepening (expansion), flat (transition), or inverted (recession warning) — with consecutive weeks in current state
- **Real 10Y Rate:** nominal 10Y minus breakeven — restrictive / neutral / accommodative
- **Credit Stress:** HY OAS level + direction + percentile rank vs. history
- **VIX Regime:** panic / fear / elevated / normal / complacent
- **Liquidity Plumbing:** TGA + RRP direction → double injection / net injection / net drain / double drain
- **M2 Growth Regime:** expanding / moderate / stagnant / contracting
- **Financial Conditions:** NFCI with consecutive weeks in loose/tight state
- **USD Trend:** DXY direction over week/month
- **Equity Regime:** S&P 500 trend over week/month/3-month
- **Inflation Expectations:** 5Y and 10Y breakevens, anchored vs. drifting assessment

Every series includes a **percentile rank** vs. the full history fetched — "where is the current value relative to the range?" This enables statements like "HY OAS is at the 97th percentile of tightness" without needing external benchmarking.

#### What Structured Data Does NOT Cover (web search fills these gaps)
- Central bank policy statements, forward guidance, press conferences (qualitative)
- CFTC Commitments of Traders / COT positioning data (no free structured API)
- Sentiment surveys: AAII, CNN Fear & Greed, BofA Fund Manager Survey (no free API)
- Geopolitical and policy developments (inherently qualitative)
- PMI releases: ISM, Eurozone, China Caixin (not on FRED in timely fashion)
- Eurozone M3 and China Total Social Financing (ECB API had issues, accepted as web search + fallback)
- Analyst views and research (Chrome-based browsing via Skill 10)

#### Dynamic ETF Discovery
`etf_lookup.py` searches a curated universe of ~100 liquid ETFs on Yahoo Finance, verifies real price data, and returns ticker + AUM + performance. Used by the thesis generator when it needs a thematic ETF not in the static reference table. Only verified ETFs are recommended — never guessed.

### External Analyst Monitoring

**Skill 10** browses two analyst feeds via Chrome: Andreas Steno (@AndreasSteno on X) and Alpine Macro (LinkedIn). It reads with fresh eyes — no pre-loaded expectations about what to find. Crucially, it follows links to full articles, not just feed headlines. The reasoning behind analyst conclusions is what makes this useful for thesis cross-referencing.

### Thesis System

Theses are specific, falsifiable investment bets classified into two types:

**Tactical theses** are generated from weekly data patterns (divergences, regime shifts, positioning extremes). They use a standard template with mechanism, assumptions, kill switches, and ETF expressions. Time horizon: weeks to quarters. Generated directly from Skill 6 synthesis output.

**Structural theses** are grounded in first-principles research on physical, economic, or structural constraints that take years to resolve. They require a Skill 11 Structural Research Brief before generation — quantified binding constraints, supply-demand analysis, capital flow data, and a steelmanned contrarian stress-test. The expanded structural template separates thesis conviction from expression selection from entry timing, requires independently testable assumptions ("What We Have To Believe"), and monitors through weekly kill switch checks with full structural reviews triggered by data changes (assumption pressure, binding constraint updates, regime shifts) rather than fixed calendar intervals.

Both types share:
- Plain English summary (readable by a non-specialist)
- Testable assumptions (each checked weekly)
- First/second/third-order ETF expressions (verified via etf_lookup.py, CHF-listed where available)
- Kill switches (specific, measurable — if met, thesis is INVALIDATED, no negotiation)
- Parameter review (when analyst insights challenge thesis parameters, flagged for review)
- Time horizon derived from the mechanism, not from a default

No fixed limit on thesis count. Quality over quantity. The thesis monitor reads the analyst monitor output to cross-reference assumptions.

Lifecycle: DRAFT → ACTIVE → STRENGTHENING / WEAKENING → INVALIDATED / TIME EXPIRED → CLOSED

### Thesis Presentation (Three-Layer Architecture)

Theses exist in three layers, each serving a different consumption mode:

**Layer 1: Structured file** (the thesis markdown in `outputs/theses/active/`). Machine-readable, for monitoring. This is what Skill 7 writes and maintains.

**Layer 2: Full thesis report** (rendered by Skill 12 into `outputs/theses/presentations/`). The deep-read version with charts, evidence tables, steelmanned bear case, and status history. This is what a human opens when they want to understand a thesis in full. Structural theses get expanded treatment: Structural Foundation section, "What We Have To Believe" table, quantified bear claims, and supply-demand trajectory charts.

**Layer 3: Briefing card** (generated by Skill 12, consumed by Skill 9). A compressed summary for the Monday Briefing — status, one-line bet, what changed this week, key risk. Includes a tactical/structural badge so the reader knows the thesis depth at a glance.

The dashboard (`generate_dashboard.py`) renders all three: briefing cards in the Briefing tab, full thesis reports in the Theses tab (with thesis-specific charts from Skill 12's chart specs), and raw thesis files accessible via the Skills tab.

### Self-Improvement Loop (Cognee Framework)

Every weekly run ends with a self-improvement cycle:

1. **Observe:** Each skill writes structured meta blocks with quality metrics
2. **Inspect:** Detects patterns — data gaps, quality trends, search effectiveness, reasoning quality, analytical accuracy
3. **Amend:** Proposes specific, targeted changes to skill instructions (never re-proposes already-implemented amendments)
4. **Evaluate:** Checks whether prior amendments improved metrics. Updates the amendment tracker.

Three layers of quality:
- **Data quality** (2a-2e): Are skills collecting data reliably?
- **Reasoning quality** (2g): Is information flowing between skills? Are cross-references being made?
- **Analytical accuracy** (2h): Were our calls right? Regime, asset tilts, event predictions, thesis performance — scored weekly, cumulative rates tracked in accuracy-tracker.md.

Persistent state files:
- `amendment-tracker.md` — all amendments from proposal through evaluation
- `accuracy-tracker.md` — cumulative scorecard of analytical call accuracy

### Weekly Delivery

One HTML dashboard file containing:
1. **Briefing tab** — 5-minute read, plain language, ETF-focused, with last week's scorecard. Thesis section uses Skill 12 briefing cards with tactical/structural badges.
2. **Regime Map tab** — four-quadrant scatter with current position, 6/12M forecast dots, historical trail
3. **Theses tab** — tabbed view of all active and draft theses. Renders Skill 12 presentation reports (with thesis-specific charts) when available, falls back to raw thesis markdown. Structural and tactical theses are badge-distinguished.
4. **System Health tab** — improvement report, amendment proposals, accuracy tracking
5. **Skills tab** — expandable view of all skill definitions
6. **About tab** — this methodology document

Historical week selector allows browsing past briefings and improvement reports.

---

## Investment Context

### ETF-Focused

All recommendations use specific ETF tickers. CHF-listed equivalents from SIX Swiss Exchange are primary (verified via Yahoo Finance). USD tickers shown in parentheses when no CHF version exists.

Reference tables: `skills/references/etf-reference.md` (broad allocation, thematic/sector, CHF equivalents).
Dynamic discovery: `scripts/etf_lookup.py` searches ~100 liquid ETFs and verifies real price data before recommending.

### Sizing

- **Monday Briefing:** Directional tilts only ("favor CSSPX.SW over CSNDX.SW"). No percentage allocations.
- **Theses:** Sizing ranges ("small 1-3%", "medium 3-5%"). The user decides exact amounts.

### Sector View

All 11 GICS sectors covered weekly. Timing derived from catalysts (not pre-set categories): what drives the view, when does it resolve, what's the exit signal. Thematic sub-sectors added when active theses or events make them relevant.

---

## Analytical Discipline

### Data Integrity (Non-Negotiable)
- Never invent numbers. Every data point sourced.
- Date-stamp every number. Source-tag ambiguous claims.
- Four-tier data quality: Tier 1 (FRED, official) → Tier 2 (market prices) → Tier 3 (surveys) → Tier 4 (commentary).
- When data conflicts, both values reported.

### Avoiding Confirmation Bias
- No pre-loaded causal chains or expected outcomes. Derive from current data.
- The regime model is our belief system — we commit to it. But asset implications are derived per-instance, not from a template.
- Analyst feeds read with fresh eyes. Frameworks emerge from observation over time, not from pre-loading.
- Thesis patterns are open-ended — the "What to Look For" list is a starting point, not a closed set.
- The improvement loop checks reasoning quality: did skills connect information across outputs?

### Accountability
- Monday briefing opens with a scorecard: what we said last week, what happened, were we right.
- Improvement loop tracks cumulative accuracy across all weeks.
- After 4+ weeks, the track record reveals where the system adds value and where it doesn't.

---

## Historical Validation of the Regime Model

A quantitative backtest (`scripts/regime_backtest.py`) tests the core claim: does the four-quadrant regime model carry predictive information about forward asset class returns? The backtest also tests whether a liquidity overlay improves the signal.

### What Was Tested

**Layer 1 — Regime only.** Mechanical regime classification (growth × inflation direction over a 6-month window, with a 2-month confirmation filter before regime changes register) applied to 15 years of monthly data (180 months). Forward 1/3/6-month returns computed for 9 asset classes across all four regimes. The 6-month window and confirmation filter align the backtest with the Skill 6 regime stability principle — regimes are structural, not monthly fluctuations.

**Layer 2 — Regime × liquidity.** Same as Layer 1 but conditioned on liquidity (M2 YoY growth, NFCI, Fed balance sheet growth — each measured relative to its own rolling 36-month median, not absolute thresholds).

### Key Findings (as of March 2026)

**The regime model carries information.** Return spreads across regimes are consistent and directionally match the framework's logic across asset classes. The regime classification has predictive power for forward returns.

**Liquidity adds value in the regime that matters most.** The liquidity overlay (M2, NFCI, Fed balance sheet) meaningfully improves signal quality during Disinflationary Slowdown — the most common regime in the dataset. In the other three regimes, the liquidity signal did not cross the significance threshold with this sample size.

**Regime stability improved signal quality.** The 6-month direction window and 2-month confirmation filter reduced noise significantly, raising average regime duration and making return patterns cleaner without losing real transitions.

Full numbers and detailed breakdowns are in `outputs/backtest/`.

### What This Does NOT Validate

**6-12 month regime forecasting.** The backtest validates the classification → return link (if you're in the right regime, the asset implications are real). It does not validate the system's ability to predict which regime will be active 6 or 12 months from now. That forecasting involves judgment, policy interpretation, and analyst cross-referencing that cannot be mechanically replayed on historical data. Forward forecasting accuracy can only be measured through the weekly accuracy tracker over time.

**The judgment layer.** Thesis generation, analyst interpretation, kill switch calibration, and contrarian positioning calls are not tested. These are inherently forward-looking and are scored by the self-improvement loop (Skill 8).

### Critical Warning: Historical Bias

These backtest results are base rates, not predictions. The most dangerous thing this system can do is treat historical averages as templates for current decisions. Two Stagflation periods can produce completely different asset returns depending on credit conditions, positioning, policy response, and starting valuations.

The weekly system must derive its conclusions from current-instance data. The backtest tells us which regimes historically favored which assets. It does not tell us that the current instance will behave the same way. Every weekly synthesis should reason from the data forward, not from historical averages backward.

If the backtest numbers start appearing in skill outputs as justification for positioning ("historically, Goldilocks produces +4.7% equity returns, therefore..."), that is a failure mode. The regime label is a starting point. The data fills in the detail. The backtest provides context, not conclusions.

### Running the Backtest

```bash
python scripts/regime_backtest.py \
  --fred-key "YOUR_KEY" \
  --output-dir outputs/backtest/ \
  --years 15
```

Outputs: `regime-backtest-results.json` (raw data) and `regime-backtest-report.html` (visual report).

---

## File Structure

```
Macro Advisor/
├── skills/
│   ├── RULES.md                    (universal policy — data integrity, sizing, language, discipline)
│   ├── references/
│   │   └── etf-reference.md        (ETF lookup tables — broad, thematic, CHF)
│   ├── 00-data-collection.md
│   ├── 01-central-bank-watch.md    (v1.1)
│   ├── 02-liquidity-credit-monitor.md (v1.1)
│   ├── 03-macro-data-tracker.md    (v1.1)
│   ├── 04-geopolitical-policy-scanner.md (v1.1)
│   ├── 05-market-positioning-sentiment.md
│   ├── 06-weekly-macro-synthesis.md
│   ├── 07-thesis-generator-monitor.md (v1.3)
│   ├── 08-self-improvement-loop.md
│   ├── 09-monday-briefing.md
│   ├── 10-analyst-monitor.md       (v1.1)
│   ├── 11-structural-research.md   (v1.0 — first-principles research for structural theses)
│   └── 12-thesis-presentation.md   (v1.0 — renders theses into visual reports + briefing cards)
├── scripts/
│   ├── data_collector.py           (FRED + Yahoo Finance data pull)
│   ├── etf_lookup.py               (dynamic ETF discovery + verification)
│   ├── generate_dashboard.py       (HTML dashboard generator)
│   └── regime_backtest.py          (historical regime backtest — Layer 1 + Layer 2 liquidity)
├── outputs/
│   ├── data/                       (JSON snapshots — weekly + latest)
│   ├── collection/                 (per-skill weekly outputs)
│   ├── synthesis/                  (weekly regime assessments)
│   ├── research/                   (Skill 11 structural research briefs)
│   ├── theses/active/              (ACTIVE- and DRAFT- thesis files)
│   ├── theses/closed/              (closed thesis files with outcomes)
│   ├── theses/presentations/       (Skill 12 rendered reports + chart specs)
│   ├── briefings/                  (weekly briefing MD + HTML dashboard)
│   ├── improvement/                (improvement reports + amendment-tracker.md + accuracy-tracker.md)
│   └── backtest/                   (regime backtest results JSON + HTML report)
└── methodology.md                  (this file)
```

### Naming Conventions
- Weekly outputs: `YYYY-Www-[skill-name].md` (e.g., `2026-W12-central-bank-watch.md`)
- Theses: `[STATUS]-[thesis-name].md` (e.g., `ACTIVE-labor-recession-credit-stress.md`)
- Dashboard: `YYYY-Www-dashboard.html`

---

## Honest Limitations

### What this system does well
- Structured data collection from institutional-quality free APIs (62+ FRED/Yahoo series, 95%+ success rate) with four-tier quality classification and date-stamped sourcing
- Interprets policy — reads central bank decisions, analyst views, and geopolitical developments and takes positions ("Fed is dovish despite inflation revision"). The user can override any interpretation; the thesis review process is the governance mechanism.
- Forces weekly regime identification with explicit reasoning
- Thesis accountability through testable assumptions and absolute kill switches
- Self-corrects through the improvement loop (data quality + reasoning quality + analytical accuracy)
- Builds cumulative institutional memory and track record over time
- Reads external analysts with fresh eyes, follows links to full articles, and cross-references against thesis parameters

### What this system does not do
- Provide real-time monitoring — weekly cadence only, not a Bloomberg terminal
- Give specific trade execution — it tells you the regime, thesis, and instruments, you decide when and how much
- Predict future regimes mechanically — the completed backtest (`scripts/regime_backtest.py`, results in `outputs/backtest/`) confirmed that regime classifications predict forward asset returns and validated the regime + liquidity model. But the system's 6-12 month regime *forecasts* involve judgment calls (policy interpretation, analyst cross-referencing) that cannot be mechanically replayed. Forecast accuracy is tracked weekly by the accuracy tracker, not by the backtest.

### The meta-risk
The system produces structured output every week. There's a danger of treating "system says Stagflation" as a substitute for thinking. The regime model is our framework — we believe in it — but we also check each instance against the data rather than reading off a template. The accountability scorecard exists precisely to catch when the framework stops working.
