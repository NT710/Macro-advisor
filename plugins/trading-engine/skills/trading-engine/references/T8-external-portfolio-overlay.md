# Skill T8: External Portfolio Overlay

## Objective

Track the user's real-world holdings, value them using live market data, and produce an exposure comparison against the paper portfolio and active theses. T8 is informational — it shows the map between what the system thinks and what the user actually holds. It never influences T1-T7. It reads their outputs but doesn't write back to them.

## What T8 Is Not

- **Not a portfolio management tool.** It doesn't rebalance, recommend specific trades, or manage tax lots.
- **Not a record-keeping system.** It doesn't track dividends, splits, or corporate actions. Valuation is price × quantity.
- **Not a trade recommender.** It shows exposure gaps and thesis alignment. The user decides what to do.
- **Not an input to T1-T7.** The paper portfolio is a clean sandbox. External positions never influence signal parsing, reconciliation, trade reasoning, or any other step in the chain.

## Prerequisite

T8 only runs if `external_portfolio_enabled` is `true` in `config/user-config.json`. This is set during setup. If the user opted out, T8 is skipped entirely.

---

## Inputs

1. **External positions config** — `config/external-positions.json` (user input from setup)
2. **User config** — `config/user-config.json` (base currency, investable asset types)
3. **Paper portfolio state** — `outputs/portfolio/latest-snapshot.json` (from T0)
4. **Performance data** — latest performance report from `outputs/performance/` (from T6)
5. **Active theses** — `{macro_advisor_outputs}/theses/active/` (same source T1 reads)
6. **Closed/invalidated theses** — `{macro_advisor_outputs}/theses/closed/` (for kill switch propagation)
7. **External portfolio utility** — `scripts/external_portfolio.py` (yfinance wrapper for pricing and classification)

---

## Execution Flow

### Step 1: Price Refresh

For each position in `config/external-positions.json`:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/external_portfolio.py \
  --action refresh_prices \
  --config config/external-positions.json \
  --output outputs/external/
```

The script:
- Pulls current price for each ticker via yfinance
- Pulls FX rates for all non-base currencies (e.g., `DKKUSD=X`, `EURUSD=X`)
- For manual-valuation positions (where yfinance can't resolve the ticker), uses the stored value and flags "manual — last updated [date]"
- Saves `outputs/external/latest-prices.json`

If yfinance is unreachable for a specific ticker, use the last known price and flag it as stale. Do not skip the position.

### Step 2: Portfolio Valuation

For each position, calculate:
- **Current value (native currency):** current price × quantity
- **Current value (base currency):** native value × FX rate to base currency
- **Allocation %:** position value / total external portfolio value
- **Unrealized P&L (absolute):** (current price − entry price) × quantity (only if entry price was provided)
- **Unrealized P&L (%):** (current price − entry price) / entry price (only if entry price was provided)
- **Holding period:** days since entry date (only if entry date was provided)

Calculate totals:
- Total external portfolio value (base currency)
- Total unrealized P&L (absolute and %)
- Position count

### Step 3: Exposure Aggregation

Aggregate all positions across four dimensions:

**By sector:** Sum allocation percentages by sector. For ETFs with `sector_weightings` data (stored during setup from yfinance), distribute the ETF's allocation proportionally. Example: if QQQ is 20% of the external portfolio and QQQ is 50% tech, contribute 10% to the tech sector bucket. For ETFs without sector weightings, assign the full allocation to the primary sector classification. For individual stocks, assign full allocation to the stock's sector.

**By geography:** Sum allocation percentages by geography classification (stored during setup).

**By asset class:** Sum allocation percentages by asset class (equities, fixed income, commodities, FX/currency, crypto, REITs, cash/other). For ETFs with `asset_classes` data from yfinance, use the stock/bond/other split. Example: a balanced ETF that is 60% stock, 40% bond distributes accordingly.

**By currency exposure:** Sum allocation percentages by the currency in which each position is denominated. This is the user's FX exposure regardless of what the assets do — holding US stocks means holding USD.

### Step 4: Paper Portfolio Comparison

Read the paper portfolio state from `outputs/portfolio/latest-snapshot.json`. Aggregate the same four dimensions (sector, geography, asset class, currency). For paper portfolio positions, use the regime template and thesis data from T1/T2 to tag each position's sector and asset class.

Produce a side-by-side comparison:
```
| Dimension   | External % | Paper % | Delta |
|-------------|-----------|---------|-------|
| Technology  | 42%       | 15%     | +27%  |
| Healthcare  | 18%       | 5%      | +13%  |
| Energy      | 2%        | 12%     | -10%  |
...
```

Compute for each dimension. Flag the top 5 largest absolute deltas.

**Investable universe filter:** The delta column only highlights differences in asset classes the user marked as investable. If the paper portfolio holds 15% in commodities but the user's investable types don't include commodities, that 15% does not appear as a delta to close. Instead, produce a single summary line at the bottom of the comparison:

```
X% of paper portfolio exposure is in asset classes outside your investable universe
(commodities: 15%, FX/currency: 3%). This is structural — not a gap to act on.
```

This line appears once, aggregated. Not repeated per position or per thesis.

### Step 5: Thesis Alignment Scan

For each active thesis in `{macro_advisor_outputs}/theses/active/`:

1. **Extract the thesis direction and sector/asset exposure.** Read the thesis's ETF expression section. Identify what sectors, geographies, and asset classes the thesis is betting on (first/second/third-order) and betting against (reduce/avoid).

2. **Scan external positions for exposure overlap.** For each external holding, check if its classification (sector, geography, asset class) overlaps with the thesis's exposure characteristics. This is **exposure matching, not instrument matching** — the scan checks sector/geography/factor overlap regardless of whether the asset classes are the same.

   This means: if the paper portfolio expresses "long gold" via GLD (commodity ETF) and the user holds Newmont Mining (gold miner equity), that's overlapping exposure even though the asset classes differ. The thesis exposure is "gold price goes up" — both instruments carry that exposure through different wrappers.

   Matching rules:
   - **Overlapping exposure:** External position has exposure in the same sector, geography, or macro factor as the thesis direction, regardless of asset class. Example: thesis says "long energy" and user holds Shell (energy equity) — overlapping, even if the paper portfolio expresses the thesis via XLE (energy ETF). The user's reason for holding Shell may be unrelated to the thesis.
   - **Opposing exposure:** External position has exposure the thesis says to reduce/avoid, regardless of asset class. Example: thesis says "reduce US large cap growth" and user holds 40% QQQ. The user may have tax, time horizon, or conviction reasons for holding QQQ that the system doesn't know about.
   - **No overlap:** No meaningful sector/geography/factor connection.

3. **Output per thesis:**
   ```
   Thesis: [name]
   Direction: [long/short summary]
   Status: [ACTIVE/STRENGTHENING/WEAKENING]
   External positions with overlapping exposure: [list with ticker, allocation %, and which sector/asset class overlaps]
   External positions with opposing exposure: [list with ticker, allocation %, and which sector/asset class opposes]
   ```
   Do NOT include the thesis conviction level in T8 output. Conviction is calibrated for paper portfolio constraints and does not transfer to the user's real portfolio decisions.

### Step 6: Kill Switch Propagation

For each thesis that has been recently invalidated (moved to `theses/closed/` since last T8 run) OR has a kill switch approaching/triggered (from T1 signal data if available):

1. **Identify external positions with overlapping exposure to the invalidated thesis** (using the same exposure matching from Step 5).
2. **Produce a kill switch notice:**
   ```
   THESIS INVALIDATED: [Thesis name]
   Kill switch condition: [what fired]
   Date invalidated: [date]
   Paper portfolio action: [positions closed by T3/T4]
   External positions with overlapping exposure:
   - [Ticker] ([Name]) — [allocation %] — overlaps in [sector/asset class]
   - [Ticker] ([Name]) — [allocation %] — overlaps in [sector/asset class]
   Note: This is informational. Your real positions may serve a different purpose
   than the thesis that was invalidated. The system does not know your tax situation,
   time horizon, or reasons for holding these positions.
   ```

Also check for approaching kill switches (if T1 signal data includes kill switch proximity):
   ```
   KILL SWITCH APPROACHING: [Thesis name]
   Condition: [kill switch condition]
   Proximity: [NEAR — within 20% of trigger]
   External positions with overlapping exposure: [list]
   ```

### Step 7: Gap Analysis

Compare the paper portfolio's exposure profile against the external portfolio's. Filter by the user's `investable_asset_types` from config.

For each exposure dimension (sector, geography, asset class):
1. Compute the delta between paper and external allocation.
2. For each significant delta (> 5%), identify what drives the paper allocation (which thesis or regime template).
3. Label the source of the delta:
   - **Thesis-driven:** The paper portfolio holds this exposure because of a specific thesis.
   - **Regime-driven:** The paper portfolio holds this exposure because of the current regime template.
   - **External-only:** The external portfolio holds significant exposure the paper portfolio does not.

Present deltas as descriptive facts, not as problems to fix. The user's real portfolio reflects constraints, convictions, and time horizons the system doesn't know about. A delta between paper and external is expected — they serve different purposes.

**Filter rules:**
- **Investable universe filter (primary):** Only compute deltas for asset classes the user marked as investable. If the paper portfolio holds commodities but the user can't/won't trade commodities, that exposure doesn't appear in the delta table at all. Instead, it's captured in the structural gap summary (see Step 4).
- **Non-investable exposure (collapsed section):** Show a separate collapsed section labeled "Outside your investable universe (informational only)" that lists what percentage of the paper portfolio sits in non-investable asset classes. This is context, not a call to action.
- **Gaps smaller than 5%:** Omit from the primary output. Include in a detailed appendix if needed.

### Step 8: Snapshot Persistence

Save all computed data:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/external_portfolio.py \
  --action save_snapshot \
  --config config/external-positions.json \
  --output outputs/external/
```

- `outputs/external/latest-external-snapshot.json` — current valuations, exposure aggregations, thesis alignment, kill switch alerts
- `outputs/external/YYYY-MM-DD-external-snapshot.json` — dated copy for historical tracking
- `outputs/external/external-value-history.json` — append total portfolio value + date for the value-over-time chart in the dashboard

### Step 8b: Write Dashboard Sidecar JSONs

After saving the snapshot, write three additional JSON files that the dashboard generator reads directly. These are **structured versions of the analysis already computed in Steps 3–6** — not new analysis. Write them from the data you already have.

**`outputs/external/latest-exposure.json`** — exposure aggregations from Step 3:
```json
{
  "by_asset_class": { "Global Equities": 91.3, "Crypto": 3.3, "Cash": 5.4 },
  "by_geography":   { "Global Developed (ex-US)": 50.0, "US": 40.0, "Denmark": 5.1, "Crypto": 3.3, "Cash": 1.6 },
  "by_currency":    { "EUR": 91.3, "USD": 3.5, "CHF": 5.2 }
}
```
Keys are human-readable labels. Values are allocation percentages (floats).

**`outputs/external/latest-thesis-overlap.json`** — thesis alignment from Step 5:
```json
{
  "overlaps": [
    {
      "thesis_name": "short-duration-capital-preservation",
      "type": "tactical",
      "status": "ACTIVE",
      "direction": "Long short-duration USD bonds",
      "overlapping_positions": [
        { "ticker": "IS3S.DE", "allocation_pct": 26.52, "overlap_reason": "Value equities outperform in rising-inflation regimes — weak positive alignment" }
      ],
      "opposing_positions": [],
      "conclusion": "Weak positive alignment. No contradiction."
    }
  ]
}
```
Include one entry per active thesis. `overlapping_positions` and `opposing_positions` are lists of `{ticker, allocation_pct, overlap_reason}`. Use empty lists if none.

**`outputs/external/latest-kill-switches.json`** — kill switch status from Step 6:
```json
{
  "propagations": [],
  "approaching": [
    {
      "thesis_name": "structural-metals-supercycle",
      "condition": "LME copper below $8,000/ton",
      "proximity": "APPROACHING",
      "external_positions": [
        { "ticker": "IS3S.DE", "allocation_pct": 26.52, "overlap_reason": "Index weight in BHP/Rio/Glencore — incidental, not thesis expression" }
      ]
    }
  ]
}
```
`propagations` = fully invalidated theses (closed since last T8 run). `approaching` = kill switch status APPROACHING or NEAR. Use empty lists when none apply.

These three files replace the need for the dashboard to parse prose markdown, giving it reliable structured data for all comparison tables and charts.

---

## Dashboard Integration

T8 adds a fourth tab to the trading engine dashboard: **"External Portfolio"**

### Section 1: Holdings Table

| Ticker | Name | Qty | Entry Price | Current Price | P&L % | Value (base) | Allocation % | Account | ⚠ |
|--------|------|-----|-------------|---------------|-------|-------------|-------------|---------|---|

- Sortable by any column
- P&L columns only shown for positions where entry price was provided
- ⚠ icon for manual-valuation positions or stale prices
- Account column groups positions by the user's account labels

### Section 2: Value Over Time

Line chart of total external portfolio value in base currency, using `external-value-history.json`. Simple single line — no benchmark comparison. This is a tracking chart, not a performance chart.

### Section 3: Exposure Comparison

Side-by-side horizontal bar charts for each dimension:
- Sector allocation: external vs paper
- Geography allocation: external vs paper
- Asset class allocation: external vs paper
- Currency exposure: external vs paper

Visual design: two bars per row (external in one color, paper in another), with the delta shown numerically. Largest deltas at the top.

### Section 4: Thesis Exposure Overlap

Table with one row per active thesis:

| Thesis | Direction | Overlapping Positions | Opposing Positions | Kill Switch Status |
|--------|-----------|----------------------|-------------------|--------------------|

- Rows with fired or approaching kill switches highlighted (amber for approaching, red for invalidated)
- Clicking a thesis row expands to show which external positions overlap/oppose and which sector/asset class connects them
- No conviction column — conviction is calibrated for the paper portfolio, not the user's real portfolio

### Section 5: Allocation Deltas

Largest differences between paper and external exposure, filtered by investable asset types. Framed as descriptive comparison, not as recommendations:

| Exposure | Paper % | External % | Delta | Paper Source |
|----------|---------|-----------|-------|-------------|
| Energy   | 12%     | 2%        | -10%  | [Thesis name] |
| Duration | 15%     | 3%        | -12%  | Regime: Disinflation |
| US Tech  | 8%      | 42%       | +34%  | External-only |

Header text above the table: "These are the largest exposure differences between the paper model portfolio and your real holdings. Differences are expected — your real portfolio reflects constraints, time horizons, and convictions that the paper model doesn't know about."

A separate collapsed section shows deltas in non-investable asset types (informational only).

### Section 6: Staleness Warnings

- Banner if `external-positions.json` `last_updated` is > 30 days ago: "Your external positions were last updated [N] days ago. Run `/update-external-positions` to refresh."
- List any manual-valuation positions with their last-update dates.
- List any tickers where yfinance returned stale prices (> 3 days old on a weekday).

---

## What T8 Explicitly Does Not Do

1. **Does not feed data back into T1-T7.** The paper portfolio is a clean sandbox. External positions never influence signal parsing, reconciliation, trade reasoning, performance tracking, or self-improvement.
2. **Does not calculate risk metrics** (VaR, Sharpe, max drawdown) for the external portfolio. That's a portfolio management tool.
3. **Does not track dividends, splits, or corporate actions.** Price × quantity is the valuation model.
4. **Does not recommend specific trades.** It shows exposure gaps and thesis alignment. The user decides.
5. **Does not create a "combined portfolio" view** that blends paper + external into one allocation. They stay separate. The comparison is the output.
6. **Does not appear in the Monday Briefing** or any macro advisor output.
7. **Does not run on Wednesday defense checks.** T8 runs on Sunday full runs only — the user's external positions don't change mid-week based on kill switches (only the user can act on their real portfolio).

---

## Meta Block

```yaml
---
meta:
  skill: external-portfolio-overlay
  skill_version: "1.0"
  run_date: "[ISO date]"
  positions_tracked: [number]
  positions_manual_valuation: [number]
  total_external_value_base: [number]
  base_currency: "[currency code]"
  fx_rates_used: {"USD": [rate], "EUR": [rate], ...}
  thesis_alignments: [number of theses with aligned positions]
  kill_switch_alerts: [number]
  largest_gap_dimension: "[sector/geography/asset_class]"
  largest_gap_delta_pct: [number]
  stale_prices: [number of tickers with stale data]
  quality:
    self_score: [0.0-1.0]
    confidence: [high/medium/low]
  notes: "[any issues]"
---
```
