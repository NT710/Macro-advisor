---
description: Refresh the dynamic ETF mapping based on current market offerings
allowed-tools: Read, Write, Edit, Bash
---

Refresh the ETF reference table by re-scanning available ETFs for the user's configured currency and hedging preference.

## Execution

1. Read `config/user-config.json` for `preferred_currency` and `hedging_preference`.
2. If config is missing, tell the user to run `/setup` first and stop.
3. For each asset class in the allocation framework, search for the best available ETF:
   - Use ~~browser to scrape justETF (or Yahoo Finance as fallback)
   - Filter by currency denomination and hedging preference
   - Rank by TER (lowest), then AUM (highest)
   - Select top option; fall back to USD if no match in preferred currency
4. Write the updated mapping to `skills/macro-advisor/references/etf-reference.md` in the working directory.
5. Update `etf_mapping_last_updated` in `config/user-config.json`.
6. Show the user a summary of any changes from the previous mapping (new ETFs, changed TERs, removed products).
