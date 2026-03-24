---
description: First-run setup — install dependencies, configure API keys, currency, ETF mapping, and schedule
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Run the first-time setup for the Macro Advisor system. Execute each step sequentially. Do not skip steps. Do not proceed until each step is confirmed working.

## Step 0: Introduction

Before any setup steps, present the value proposition to the user. Use AskUserQuestion with this message:

"**Institutional-Grade Macro Research. Every Week. On Your Desktop.**

**The model.** The system tracks three forces that drive all asset prices: **Growth** (expanding or contracting?), **Inflation** (rising or falling?), and **Liquidity** (loosening or tightening?). Where these three forces sit determines the macro regime — Goldilocks, Overheating, Disinflationary Slowdown, or Stagflation. Each regime has a different playbook for what to own and what to avoid. The system reads the underlying data, identifies which regime you're in, and forecasts where the forces are heading at 6 and 12 month horizons.

**What it does.** Every Sunday (or whichever day you choose), the system pulls hard economic data (employment, inflation, credit spreads, central bank policy, commodity prices, positioning), scores each of the three forces, classifies the current regime, and produces a full investment research report. The kind of output that firms like BCA Research and Alpine Macro charge $15,000+ a year for. Except this runs on your machine, scores its own accuracy, and gets sharper over time.

**What you get.** A weekly regime call with the underlying growth, inflation, and liquidity picture — not just where we are, but which forces are shifting and what that means for the next 6-12 months. Investment theses with stated assumptions, explicit kill switches, and ETF expressions in your currency. A structural scanner that catches slow-building imbalances (supply gaps, capex underinvestment, fiscal stress) before they surface in prices. Cross-referencing against 8 leading independent macro analysts. And a self-correcting methodology that tracks every call it makes.

**What it takes.** One free API key (FRED). Five minutes to set up. Runs autonomously in about 15 minutes."

Options: Let's set it up, Tell me more about how it works, Not right now

**If "Tell me more":** Explain the three-force model: Growth, Inflation, and Liquidity are the inputs. The four regimes (Goldilocks, Overheating, Disinflationary Slowdown, Stagflation) are the output. Each week the system collects hard data (no guessing), scores each force, classifies the regime, and then builds the investment view on top: regime-driven allocation (what the current environment favors), investment theses with mandatory kill switches (specific bets with explicit exit conditions), a structural scanner for multi-year imbalances, and 6/12-month regime forecasts that track where the forces are heading — so you're not just positioned for today, you understand the direction of travel. Each layer feeds the next. The system cross-references against 8 independent macro analysts and scores its own accuracy the following week. Then re-ask if they want to proceed.

**If "Not right now":** Say "No problem. Run `/macro-advisor:setup` whenever you're ready." End the command.

**If "Let's set it up":** Continue to Step 1.

## Step 0b: Verify Workspace Folder

Before anything else, check that the user has selected a workspace folder in Cowork. The workspace folder is where all outputs, config, and data persist between sessions. Without it, everything is written to a temporary directory that vanishes.

Check if the current working directory is inside a Cowork workspace (i.e., under `/sessions/*/mnt/` with a user-selected folder mounted). If the path looks like a temporary session directory with no mounted folder, stop and tell the user:

"You need to select a workspace folder before running setup. Click the folder icon in Cowork and choose a folder on your computer — this is where all macro advisor outputs, config, and data will be saved. Once selected, run `/macro-advisor:setup` again."

Do not proceed past this step without a workspace folder.

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

Check if Chrome browser tools are available (~~browser).

The Macro Advisor monitors 8 external analysts via Skill 10. Three require browser access (Chrome extension): Andreas Steno (X), Luke Gromen (X), and Alpine Macro (LinkedIn). The other five — Alfonso Peccatiello/The Macro Compass (Substack), MacroVoices (podcast transcripts), Howard Marks/Oaktree (memos), Lyn Alden (monthly newsletter), and Evergreen Gavekal (blog) — use WebFetch and work without browser access.

**If browser IS available:** Tell the user:

"Browser access detected. The Macro Advisor will use Chrome to browse X feeds (Steno, Gromen) and LinkedIn (Alpine Macro) for full analyst coverage.

**Important:** Make sure you are logged in to X and LinkedIn in your Chrome browser before the first weekly run. Without active sessions, the browser will see login walls instead of analyst content."

Save `browser_access: true` in config.

**If browser is NOT available:** Tell the user:

"No browser access detected. The system will still work — 5 of 8 analysts use WebFetch and don't need Chrome. For the remaining 3 (Steno and Gromen on X, Alpine Macro on LinkedIn), the system will fall back to web search instead of browsing full articles.

If you'd like full analyst coverage, enable the Chrome extension for Claude and make sure you're logged in to X and LinkedIn."

Ask if they want to proceed without browser access or enable it first. Save `browser_access: false` in config.

## Step 4: Currency Preference

Ask the user using AskUserQuestion:

"What is your preferred currency for ETF investments?"
Options: CHF, EUR, USD, GBP

## Step 5: Build ETF Reference Table

The plugin ships with a comprehensive `etf-reference.md` containing Broad Allocation ETFs (USD) and Thematic/Sector ETFs (USD). These sections are universal and must be preserved for all users — they feed the Monday briefing's full sector view and thesis generator.

Setup's job is to **prepend** a currency-specific section to this file, not replace it. The file structure after setup should be:

1. **[Currency] Equivalents on [Exchange]** (generated by setup)
2. **Broad Allocation ETFs (USD tickers)** (already in file — keep as-is)
3. **Thematic/Sector ETFs (USD tickers)** (already in file — keep as-is)
4. **Dynamic ETF Discovery** (already in file — keep as-is)

### If user chose USD:
No currency-specific section needed. The Broad Allocation and Thematic sections already cover USD directly. Add a brief header noting USD is the primary currency and all sections below are directly tradeable. Keep the rest of the file unchanged.

### If user chose CHF, EUR, or GBP:
Build a comprehensive currency-specific equivalents section covering:

**Core asset classes:** US large cap, US small cap, international developed, emerging markets, long-term treasuries, short-term treasuries, corporate bonds (IG), high yield bonds, TIPS, gold, oil, broad commodities, real estate.

**All GICS sectors:** Energy, Technology/Nasdaq, Financials, Healthcare, Industrials, Consumer Discretionary, Consumer Staples, Utilities, Materials, Communication Services, Real Estate.

**Key thematic/regional:** Semiconductors, China, Japan, Europe, any other themes with known equivalents on the user's exchange.

For each category:
- Use `etf_lookup.py` and Yahoo Finance to find the best ETF available on the user's exchange (SIX for CHF with .SW suffix, Xetra for EUR with .DE suffix, LSE for GBP with .L suffix)
- Rank by TER (lowest first), then AUM (highest first)
- Include 1-2 alternatives where available
- Where no local equivalent exists, note "No [currency] equivalent — use USD: [ticker]" (this is the USD fallback)

**Currency note:** Include a note explaining the denomination (e.g., "USD on SIX" = tradeable on Swiss exchange but denominated in USD, "[currency] hedged" = eliminates FX risk).

Write the currency-specific section to `config/etf-overrides.md` in the workspace. This file persists across plugin reinstalls.

The base ETF reference (`${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/etf-reference.md`) ships with USD tickers and is read-only. The workspace override adds currency-specific equivalents. Skills that need ETF lookups read both files: `config/etf-overrides.md` first (currency-specific), then the plugin's `etf-reference.md` (USD defaults and thematic).

Show the user the resulting currency mapping and ask for confirmation before proceeding.

## Step 6: Resolve Workspace Path

The workspace path is where all outputs and user config live. Resolve it now so scheduled tasks and other contexts can always find the workspace regardless of working directory.

```bash
WORKSPACE_PATH=$(pwd)
echo "Workspace resolved to: $WORKSPACE_PATH"
```

Store this as `workspace_path` in the config (Step 8). All commands will read this path from config and use it for outputs.

## Step 7: Create Output Directories

```bash
mkdir -p outputs/data outputs/collection outputs/synthesis outputs/research outputs/theses/active outputs/theses/closed outputs/theses/presentations outputs/briefings outputs/improvement outputs/backtest outputs/structural/candidates config
```

## Step 8: Schedule

Ask the user using AskUserQuestion:

"When should the weekly macro analysis run?"
Options: Sunday afternoon, Sunday evening, Monday early morning

Then ask:

"What timezone are you in?"
Options: CET (Central European), ET (US Eastern), PT (US Pacific), GMT

Based on their answers, create a scheduled task using the schedule tool. **The scheduled task prompt must be a thin launcher — not a detailed instruction set.** The skill chain, execution order, and step-by-step instructions already live in `/macro-advisor:run-weekly` and the reference files. Duplicating them in the schedule prompt creates a second source of truth that drifts when the plugin is updated.

Use this exact prompt template:

```
Run the full weekly Macro Advisor analysis cycle.

Execute by running `/macro-advisor:run-weekly`. Follow the instructions in that command file exactly — it contains the current skill chain, execution order, and all step-by-step instructions. The workspace path is stored in config/user-config.json. Do not improvise steps or skip skills.

Present the final briefing summary when complete.
```

Do NOT list workspace paths, individual skills, API keys, or execution details in the schedule prompt. Those belong in the command file and config, not in the schedule.

## Step 9: Write Configuration

Save all user preferences to `config/user-config.json`:

```json
{
  "workspace_path": "/absolute/path/to/workspace",
  "fred_api_key": "USER_KEY",
  "preferred_currency": "CHF",
  "browser_access": true,
  "schedule_day": "sunday",
  "schedule_time": "16:00",
  "timezone": "CET",
  "etf_mapping_last_updated": "YYYY-MM-DD",
  "setup_completed": true
}
```

The `workspace_path` is the absolute path resolved in Step 6. This allows commands and scheduled tasks to find outputs regardless of what working directory they start from.

EIA petroleum data and BIS credit data are fetched automatically (no API key needed). The data collector downloads the EIA bulk file (~61MB) each run for US petroleum inventories, refinery utilization, and demand data.

## Step 10: Validation Run

Run a quick validation:

1. Pull one week of data using data_collector.py with the user's FRED key
2. Verify the output JSON is valid and contains data
3. Verify `snapshot.positioning` contains CFTC COT contracts (pulled automatically, no API key needed)
4. Confirm the ETF mapping has entries for all major asset classes

Report results. If everything passes, tell the user:

"Setup complete. Your Macro Advisor is configured and scheduled. The first full analysis will run at [scheduled time]. You can also run it manually anytime with `/macro-advisor:run-weekly`.

The first run includes a full structural scan — the system will look for multi-year macro imbalances across the economy (supply gaps, capex underinvestment, fiscal stress, demographic shifts). After that, the structural scanner runs bi-weekly as part of the regular cycle."

If `browser_access` is true, add a reminder:

"**Before your first run:** Make sure you're logged in to X and LinkedIn in Chrome so the analyst monitor (Skill 10) can access Steno, Gromen, and Alpine Macro feeds."

## Step 11: Trading Engine Introduction

After setup is complete, introduce the Trading Engine using AskUserQuestion:

"Your Macro Advisor is ready.

There's a companion plugin that paper-trades the theses this system produces — so you find out whether the macro calls actually translate into returns. Devil's advocate on every trade, mid-week defense checks, full P&L attribution. You can also overlay your real holdings to see how they align with the system's views.

Paper trading only. No real money. 5 minutes to set up with a free Alpaca account."

Options: Set up the Trading Engine now, I'll do it later

**If "Set up now":** Tell the user to run `/trading-engine:setup`.

**If "I'll do it later":** Say "No problem. Run `/trading-engine:setup` whenever you're ready." End the command.
