---
description: Refresh the dynamic ETF mapping based on current market offerings
allowed-tools: Read, Write, Edit, Bash
---

Refresh the ETF reference table by re-scanning available ETFs for the user's configured currency preference.

## Execution

1. Read `config/user-config.json` for `preferred_currency`.
2. If config is missing, tell the user to run `/macro-advisor:setup` first and stop.
3. If preferred currency is USD, no currency-specific section is needed — the Broad Allocation and Thematic sections in the file already cover USD directly. Just verify tickers are still active via Yahoo Finance and report any delistings.
4. If preferred currency is CHF, EUR, or GBP, regenerate the currency-specific equivalents section at the top of `etf-reference.md`. Cover comprehensively:
   - **Core asset classes:** US large cap, US small cap, international developed, emerging markets, long-term treasuries, short-term treasuries, corporate bonds (IG), high yield, TIPS, gold, oil, broad commodities, real estate
   - **All GICS sectors:** Energy, Technology/Nasdaq, Financials, Healthcare, Industrials, Consumer Discretionary, Consumer Staples, Utilities, Materials, Communication Services, Real Estate
   - **Key thematic/regional:** Semiconductors, China, Japan, Europe, and any other themes with known equivalents on the user's exchange
   - For each: use `etf_lookup.py` + Yahoo Finance, rank by TER then AUM, include 1-2 alternatives, note "No [currency] equivalent — use USD: [ticker]" where none exists
5. **Do not modify** the Broad Allocation ETFs (USD) or Thematic/Sector ETFs (USD) sections — these are universal and must remain intact.
6. Update `etf_mapping_last_updated` in `config/user-config.json`.
7. Show the user a summary of any changes from the previous mapping (new ETFs, changed TERs, delistings, removed products).

Note: This refreshes the currency-specific section (Layer 1) and verifies USD fallbacks (Layer 2). The dynamic discovery layer (`etf_lookup.py` for niche themes during thesis generation) runs automatically and does not need manual refresh.
