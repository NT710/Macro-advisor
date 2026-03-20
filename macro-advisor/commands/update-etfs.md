---
description: Refresh the dynamic ETF mapping based on current market offerings
allowed-tools: Read, Write, Edit, Bash
---

Refresh the ETF reference table by re-scanning available ETFs for the user's configured currency preference.

## Execution

1. Read `config/user-config.json` for `preferred_currency`.
2. If config is missing, tell the user to run `/setup` first and stop.
3. For each major asset class in the allocation framework, use `etf_lookup.py` and Yahoo Finance to find the best available ETF:
   - Search for ETFs denominated in the user's preferred currency
   - Rank by TER (lowest), then AUM (highest)
   - Select top option; fall back to USD if no match in preferred currency and flag it
4. Write the updated mapping to `skills/macro-advisor/references/etf-reference.md` in the working directory.
5. Update `etf_mapping_last_updated` in `config/user-config.json`.
6. Show the user a summary of any changes from the previous mapping (new ETFs, changed TERs, removed products).

Note: This updates the static reference table (Layer 1 + 2). The dynamic discovery layer (`etf_lookup.py` for thematic/niche ETFs) runs automatically during thesis generation and does not need manual refresh.
