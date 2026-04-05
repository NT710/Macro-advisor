# Skill 0: Data Collection

## Objective

Run the Python data collector script before all other skills. Produces structured JSON with hard numbers from FRED, Yahoo Finance, CFTC COT, ECB, Eurostat, EIA, and BIS. Skills 1-13 read this data FIRST for quantitative facts, then use web search ONLY for qualitative context (commentary, policy statements, positioning narratives).

## Execution

Run the data collector script from the Macro Advisor directory:

```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt --break-system-packages -q 2>/dev/null
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

Only FRED requires an API key. EIA petroleum data is fetched via bulk download (~61MB, no key), and CFTC COT, ECB, Eurostat, and BIS data are all pulled automatically (no key needed).

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
snapshot.rates         → fed_funds, us_2y, us_5y, us_10y, us_30y, sofr, sofr_30d_avg,
                         fed_funds_target_upper (with percentile ranks)
snapshot.credit        → hy_oas, ig_oas, spread differential, hy_effective_yield, euro_hy_oas,
                         signal, private_credit_proxy
snapshot.liquidity     → m2_growth, plumbing (TGA/RRP), nfci, fed_assets, money_market_funds,
                         stl_financial_stress, adjusted_nfci, monetary_base_B
snapshot.growth        → unemployment, claims, consumer sentiment, payrolls, retail sales,
                         housing_starts, building_permits, existing_home_sales, case_shiller_hpi,
                         jolts_openings, jolts_quits, real_gdp, real_gdp_chained,
                         gdpnow, stleni, recession_probability
snapshot.inflation     → cpi yoy/mom, core_cpi, pce, core_pce, michigan expectations, breakevens
snapshot.markets       → sp500, nasdaq, russell, vix, gold, oil, copper, silver, natgas, brent,
                         eurusd, dxy, tlt, hyg, cboe_skew, euro_stoxx50, gbpusd,
                         shv_short_treasury, bdry_dry_bulk, etc.
snapshot.positioning   → CFTC COT data (9 contracts: equities, rates, FX, commodities)
snapshot.eurozone      → m3, m3_yoy, ecb_balance_sheet, hicp_headline, hicp_core
snapshot.energy        → crude_inventory, spr_inventory, refinery_utilization, days_of_supply
                         (via bulk download, no key needed)
snapshot.commodities   → term_structure (WTI-Brent spread), momentum (5 commodities vs MAs),
                         inventory_to_sales (retail, manufacturing, wholesale with trend)
snapshot.international_structural → BIS credit-to-GDP gap for US, Euro area, China, Japan, UK
snapshot.derived_signals → yield_curve_10y2y, yield_curve_10y3m, real_rate, credit_stress
                           (incl. hy_effective_yield, euro_hy_oas), vix_regime,
                           liquidity_plumbing, financial_conditions, equity_regime,
                           inflation_expectations, crude_term_structure, commodity_momentum,
                           inventory_to_sales
```

Each derived signal includes a `signal` field with a human-readable classification (e.g., "loose", "expanding", "elevated", "strong_uptrend", "drawing").

## Data Sources

The collector pulls from seven institutional-quality free sources:

1. **FRED** (requires API key): 60+ series — rates (incl. SOFR, fed funds target), credit (incl. Euro HY OAS), liquidity (incl. monetary base), inflation, employment, growth (incl. GDPNow, recession probability), housing, regional Feds, money markets, credit conditions, inventory-to-sales ratios
2. **Yahoo Finance** (no key): 27 tickers — equities, volatility, bond ETFs, commodities (gold, crude WTI, copper, silver, natural gas, Brent), currencies, regional ETFs, dry bulk shipping (BDRY)
3. **CFTC SODA API** (no key): COT positioning for 9 contracts — equities, rates, FX, commodities
4. **ECB SDW** (no key): Eurozone M3 and ECB balance sheet
5. **Eurostat** (no key): HICP headline and core inflation
6. **EIA** (no key): US petroleum data via bulk download (~61MB) — commercial crude inventories, SPR level, refinery utilization, demand proxy
7. **BIS** (no key): Credit-to-GDP gap for 5 economies (US, Euro area, China, Japan, UK) — actual ratio vs. HP-filter trend

## How Skills Should Use This Data

1. Read `latest-snapshot.json` first
2. Use the hard numbers as the foundation for your analysis
3. Use the `derived_signals` for quick regime assessment
4. Skill 13 (Structural Scanner) should exhaust snapshot data before web searching — commodity momentum, inventory-to-sales, EIA energy, BIS credit gaps are all available quantitatively
5. Use web search to fill gaps the data doesn't cover:
   - Central bank forward guidance and qualitative statements
   - Policy announcements and geopolitical developments
   - Sentiment surveys (AAII, CNN Fear & Greed, BofA FMS)
   - Analyst commentary and market narrative
   - ISM headline (proprietary), China TSF, non-US petroleum data
6. When the data shows something surprising, search for why — the number is the fact, the search provides the explanation

## Historical Data Access

The full data file (`latest-data-full.json`) contains trailing history for every series. Each FRED series includes:
- `history`: array of {date, value} going back 26 weeks (weekly mode) or 5 years (historical mode)
- `percentile_rank`: where current value sits vs. entire history fetched
- `yoy_change_percent`: year-over-year change
- `mom_change_percent`: month-over-month change

Yahoo Finance tickers include weekly resampled history (up to 52 weeks), used by the commodity momentum computation. EIA and BIS data include 52-week and quarterly history respectively.

If a skill's analysis requires comparing current conditions to historical episodes (e.g., "where were credit spreads during the 2022 tightening cycle"), it should note this in the meta block as a recommendation for historical mode, and the improvement loop will flag it.
