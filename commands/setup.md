---
description: First-run setup — install dependencies, configure API keys, currency, ETF mapping, and schedule
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Run the first-time setup for the Macro Advisor system. Execute each step sequentially. Do not skip steps. Do not proceed until each step is confirmed working.

## Step 1: Install Python Dependencies

```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt --break-system-packages -q
```

Verify installation succeeded. If any package fails, report the error and stop.

## Step 2: FRED API Key

Ask the user for their FRED API key using AskUserQuestion. Provide these instructions:

"To get a free FRED API key:
1. Go to https://fred.stlouisfed.org
2. Create an account (or sign in)
3. Go to My Account → API Keys
4. Request a new API key

Paste your API key below."

Once received, verify the key works by running a test query:

```bash
python -c "from fredapi import Fred; fred = Fred(api_key='USER_KEY_HERE'); print(fred.get_series('DFF').tail(1))"
```

If the test fails, tell the user the key is invalid and ask them to try again.

## Step 3: Browser Access

Check if Chrome browser tools are available (~~browser). If not, inform the user:

"The Macro Advisor uses browser access to scrape justETF for ETF data and to read external analyst feeds (Steno Research, Alpine Macro). You'll need to enable the Chrome extension for Claude.

Without browser access, the system will still work but:
- ETF mapping will use Yahoo Finance data only (less comprehensive)
- Analyst monitoring (Skill 10) will be limited to web search"

Ask if they want to proceed with or without browser access.

## Step 4: Currency and Hedging Preference

Ask the user using AskUserQuestion:

"What is your preferred currency for ETF investments?"
Options: CHF, EUR, USD, GBP

Then ask:

"Do you prefer currency-hedged or unhedged ETFs?"
Options: Hedged (reduces currency risk, slightly higher TER), Unhedged (accepts currency exposure, lower TER)

## Step 5: Dynamic ETF Mapping

Using the user's currency and hedging preferences, build the ETF reference table:

1. For each asset class in the allocation framework (US large cap, US small cap, international developed, emerging markets, US treasuries, corporate bonds, high yield, gold, commodities, real estate):
   - Search justETF via ~~browser (or Yahoo Finance as fallback) for ETFs denominated in the user's preferred currency
   - Filter by hedging preference
   - Rank by TER (lowest first), then AUM (highest first)
   - Select the top option
   - If no match exists in the preferred currency, fall back to USD and flag it

2. Write the result to `skills/macro-advisor/references/etf-reference.md` in the working directory, replacing the template version.

3. Show the user the resulting ETF mapping and ask for confirmation.

## Step 6: Create Output Directories

```bash
mkdir -p outputs/data outputs/collection outputs/synthesis outputs/research outputs/theses/active outputs/theses/closed outputs/theses/presentations outputs/briefings outputs/improvement outputs/backtest
```

## Step 7: Schedule

Ask the user using AskUserQuestion:

"When should the weekly macro analysis run?"
Options: Sunday afternoon, Sunday evening, Monday early morning

Then ask:

"What timezone are you in?"
Options: CET (Central European), ET (US Eastern), PT (US Pacific), GMT

Based on their answers, create a scheduled task using the schedule tool. The task should execute the full skill chain: 0→1→2→3→4→5→10→6→7→11(if triggered)→8→12→9.

## Step 8: Write Configuration

Save all user preferences to `config/user-config.json`:

```json
{
  "fred_api_key": "USER_KEY",
  "preferred_currency": "CHF",
  "hedging_preference": "hedged",
  "browser_access": true,
  "schedule_day": "sunday",
  "schedule_time": "16:00",
  "timezone": "CET",
  "etf_mapping_last_updated": "YYYY-MM-DD",
  "setup_completed": true
}
```

## Step 9: Validation Run

Run a quick validation:

1. Pull one week of data using data_collector.py with the user's FRED key
2. Verify the output JSON is valid and contains data
3. Confirm the ETF mapping has entries for all major asset classes

Report results. If everything passes, tell the user:

"Setup complete. Your Macro Advisor is configured and scheduled. The first full analysis will run at [scheduled time]. You can also run it manually anytime with /run-weekly."
