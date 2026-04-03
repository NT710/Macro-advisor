# Changelog

## v0.8.0 (2026-04-03)

### New
- **8-regime model:** Growth x Inflation x Liquidity (was 4-quadrant Growth x Inflation). Liquidity as 3rd axis splits each quadrant into Ample/Tight, producing 8 distinct regimes with differentiated asset playbooks.
- **Regime Evaluator (Skill 6b):** Blind classification for anti-anchoring. Independent regime assessment without seeing Skill 6 output first. Tracks divergence frequency, lead time, and CHALLENGE accuracy.
- **Empirical pattern matching (Skill 6c):** Analog matcher finds historical periods similar to current macro state. Cosine similarity on state vectors, top-N analogs, per-ETF risk/reward ratios, surprise detection. Hard rule: never sole justification for a position.
- **3-axis regime forecasts:** 6-month and 12-month forecasts with Growth, Inflation, and Liquidity driver trajectories. Probability distributions and conditional triggers.
- **Synthesis JSON sidecar:** Structured data handoff to Trading Engine (`YYYY-Www-synthesis-data.json`) eliminates markdown parsing for regime and forecast data.
- **Out-of-sample backtest:** `analog_matcher.py --mode backtest` validates empirical sentiment against naive baselines. Current result: model does not beat naive (57.9% vs 63.3%), confirming "context only" treatment.

### Absorbed from self-improvement loop
- **A-2026W13-005:** Structural thesis turnover reservation (T3). Reserve 33% of first-entry amount for structural theses ACTIVE 2+ runs with zero position.
- **A-2026W13-006:** Regime forecast pass-through (T1 + T3). T1 extracts 6/12-month forecasts + driver readings. T3 uses for durability-aware sizing and cross-regime position awareness.
- **AT-2026W14-001:** Structural limit price verification (T4 Pre-Flight Check #5). Verifies limit within 5% of live ask; auto-recalculates if stale.
- **AT-2026W14-002:** Neutral conviction retry gate (T3 + T5). Skip neutral-conviction entries after 2 expired orders; market order escalation for directional conviction.

### Changed
- **Execution chain:** `0→1→2→3→4→5→10→14→13→streak→6→6b→6c→7→11→8→12→9` (added 6b and 6c between synthesis and thesis generation)
- **T1 signal parser:** Reads `empirical-sentiment.json` + synthesis JSON sidecar. Full 3-axis driver extraction into `regime_forecast` block.
- **T3 trade reasoner:** Forecast-aware sizing (durability assessment), cross-regime position awareness (tiebreaker for turnover budget), structural reservation section, retry gate.
- **T5 trade logger:** `retry_count` field for retry gate tracking.
- **Dashboards:** Per-dot regime family colors on history chart. Liquidity condition markers (circle = Ample, rectRot = Tight). Full 8-regime label display.
- **regime_backtest.py:** Extended with 3-axis classification, `analyze_eight_regimes()`, `backfill_regime_history()`, `--backfill` CLI flag.
- **evaluation_streak.py:** Reports family divergence + liquidity divergence separately.
- **regime_week_count.py:** Counts streak on `regime_family`, not full 8-regime label.

### Fixed
- Regime streak counting uses `regime_family` for backward compatibility with kill switches (which operate on 4-quadrant families)
- Liquidity condition: rolling 4-week directional assessment (not 2-month confirmation filter, not purely instantaneous)
- Trading engine dashboard `parse_regime_templates()` skips `_liquidity_modifiers` key

## v0.7.9

- Private credit proxy composite: BIZD (BDC ETF) added as 5th proxy alongside SLOOS, C&I loans, BKLN, HY OAS
- Fed balance sheet rolling trends: `snapshot.liquidity.trends.fed_total_assets` with 4w/8w direction bias
- Analyst Monitor: Chrome/WebFetch priority logic for improved source access
- Positioning: Fallback search queries for CFTC COT, Put/Call, AAII data
- YAML meta block standardization for Skills 4 and 5

## v0.7.8

- Initial 4-quadrant regime model (Growth x Inflation)
- 14-skill analysis chain (Skills 0-9, 10-14)
- Trading Engine beta (T0-T8)
- Self-improvement loop (Skill 8 / T7)
