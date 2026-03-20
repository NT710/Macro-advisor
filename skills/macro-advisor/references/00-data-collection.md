# Skill 0: Data Collection

## Objective

Run the Python data collector script before all other skills. Produces structured JSON with hard numbers from FRED and Yahoo Finance. Skills 1-5 read this data FIRST for quantitative facts, then use web search ONLY for qualitative context (commentary, policy statements, positioning narratives).

## Execution

Run the data collector script from the Macro Advisor directory:

```bash
pip install fredapi yfinance --break-system-packages -q 2>/dev/null
python scripts/data_collector.py \
  --fred-key "YOUR_FRED_API_KEY" \
  --output-dir outputs/data/ \
  --mode weekly
```

For the first-ever run or when historical context is needed:
```bash
python scripts/data_collector.py \
  --fred-key "YOUR_FRED_API_KEY" \
  --output-dir outputs/data/ \
  --mode historical
```

Historical mode pulls 5 years of data. Use it when:
- The synthesis skill flags "insufficient historical context for regime comparison"
- A thesis needs comparison to prior regime transitions
- The improvement loop recommends deeper lookback for a specific series

## Output Files

- `outputs/data/latest-snapshot.json` — concise current readings (what skills should read first)
- `outputs/data/latest-data-full.json` — full data with trailing history per series
- `outputs/data/YYYY-Www-snapshot.json` — weekly archive
- `outputs/data/YYYY-Www-data-full.json` — weekly archive

## What the Snapshot Contains

```
snapshot.rates         → fed_funds, us_2y, us_5y, us_10y, us_30y (with percentile ranks)
snapshot.credit        → hy_oas, ig_oas, spread differential, signal
snapshot.liquidity     → m2_growth, plumbing (TGA/RRP), nfci, fed_assets
snapshot.growth        → unemployment, claims, consumer sentiment, lei, payrolls, retail sales
snapshot.inflation     → cpi yoy/mom, core_cpi, pce, core_pce, michigan expectations, breakevens
snapshot.markets       → sp500, nasdaq, russell, vix, gold, oil, copper, eurusd, dxy, tlt, hyg, etc.
snapshot.derived_signals → yield_curve, real_rate, credit_stress, vix_regime, liquidity_plumbing,
                           financial_conditions, equity_regime, inflation_expectations
```

Each derived signal includes a `signal` field with a human-readable classification (e.g., "loose", "expanding", "elevated").

## How Skills Should Use This Data

1. Read `latest-snapshot.json` first
2. Use the hard numbers as the foundation for your analysis
3. Use the `derived_signals` for quick regime assessment
4. Use web search to fill gaps the data doesn't cover:
   - Central bank forward guidance and qualitative statements
   - Policy announcements and geopolitical developments
   - Positioning data (COT, fund flows, sentiment surveys)
   - Analyst commentary and market narrative
5. When the data shows something surprising, search for why — the number is the fact, the search provides the explanation

## Historical Data Access

The full data file (`latest-data-full.json`) contains trailing history for every series. Each FRED series includes:
- `history`: array of {date, value} going back 26 weeks (weekly mode) or 5 years (historical mode)
- `percentile_rank`: where current value sits vs. entire history fetched
- `yoy_change_percent`: year-over-year change
- `mom_change_percent`: month-over-month change

If a skill's analysis requires comparing current conditions to historical episodes (e.g., "where were credit spreads during the 2022 tightening cycle"), it should note this in the meta block as a recommendation for historical mode, and the improvement loop will flag it.
