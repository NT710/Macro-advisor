---
description: First-run setup — install alpaca-py, configure API keys, verify macro advisor, and schedule trading runs
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Run the first-time setup for the Trading Engine. Execute each step sequentially. Do not skip steps.

## Step 0: Introduction

Before any setup steps, present the value proposition to the user. Use AskUserQuestion with this message:

"**Systematic Execution. Position Management. Real Accountability.**

**What it does.** Takes the regime calls and investment theses your Macro Advisor produces and paper-trades them. Every trade faces a devil's advocate challenge before execution. Positions are sized by conviction and regime alignment. Kill switches are enforced mid-week, not just on Sundays.

**What you get.** A paper portfolio that tests whether your macro research actually makes money. Full P&L attribution back to the thesis that generated each trade. Performance tracking by thesis type, regime, and conviction level.

**External portfolio overlay.** You can also overlay your real-world holdings: see your actual exposure across sectors, geographies, and currencies, compare it to the system's views, and get alerts when a thesis behind one of your positions gets invalidated.

**What it takes.** A free Alpaca paper trading account. The Macro Advisor already running. Five minutes to set up."

Options: Let's set it up, Tell me more, Not right now

**If "Tell me more":** Explain briefly: after the Macro Advisor completes each week, the Trading Engine reads the latest regime and theses, challenges each trade with a devil's advocate, sizes positions, and executes on Alpaca paper trading. Wednesdays it checks kill switches and drawdown on all open positions. Every trade has a full paper trail: the thesis, the devil's advocate argument, the sizing rationale, and the exit conditions. Then re-ask if they want to proceed.

**If "Not right now":** Say "No problem. Run `/trading-engine:setup` whenever you're ready." End the command.

**If "Let's set it up":** Continue to Step 1.

## Step 0b: Verify Workspace Folder

Before anything else, check that the user has selected a workspace folder in Cowork. The workspace folder is where all outputs, config, and data persist between sessions. Without it, everything is written to a temporary directory that vanishes.

Check if the current working directory is inside a Cowork workspace (i.e., under `/sessions/*/mnt/` with a user-selected folder mounted). If the path looks like a temporary session directory with no mounted folder, stop and tell the user:

"You need to select a workspace folder before running setup. Click the folder icon in Cowork and choose a folder on your computer — this is where all trading engine outputs, config, and data will be saved. Once selected, run `/trading-engine:setup` again."

Do not proceed past this step without a workspace folder.

## Step 1: Install Python Dependencies

```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt --break-system-packages -q
```

Verify installation succeeded. If any package fails, report the error and stop.

## Step 2: Alpaca API Key

Ask the user for their Alpaca API key using AskUserQuestion. Provide these instructions:

"To get a free Alpaca paper trading API key:
1. Go to https://alpaca.markets and create a free account
2. Switch to **Paper Trading** (top-right toggle — this is important, we only use paper trading)
3. Go to the Paper Trading dashboard → **API Keys**
4. Click **Generate New Key**
5. Copy both the **API Key ID** and the **Secret Key** (the secret is only shown once)

Paste your API Key ID below."

Options: [text input], Skip for now — I'll add it later

## Step 3: Alpaca Secret Key

If the user provided an API key in Step 2, ask for the secret key:

"Now paste your Alpaca Secret Key. This was shown when you generated the API key. If you didn't copy it, you'll need to regenerate a new key pair in the Alpaca dashboard."

Options: [text input], Skip for now

## Step 4: Verify Alpaca Connection

If both keys were provided, test the connection:

```bash
python -c "
from alpaca.trading.client import TradingClient
client = TradingClient('API_KEY', 'SECRET_KEY', paper=True)
account = client.get_account()
print(f'Account status: {account.status}')
print(f'Portfolio value: \${float(account.portfolio_value):,.2f}')
print(f'Buying power: \${float(account.buying_power):,.2f}')
"
```

If the test fails, tell the user the keys are invalid and ask them to try again. If it succeeds, report the account status.

## Step 5: Locate Macro Advisor

The trading engine needs to read macro advisor outputs. Try auto-detection first, then prompt.

**Auto-detection:** Search for the macro advisor outputs directory by checking these paths in order:

```bash
# Check common relative paths from the trading engine's working directory
for path in \
  "../macro-advisor/outputs" \
  "../../macro-advisor/outputs" \
  "../Macro Advisor/outputs" \
  "../../Macro Advisor/outputs" \
  "../macro-advisor/outputs"; do
  if [ -d "$path" ] && [ -d "$path/synthesis" ]; then
    echo "FOUND: $(realpath $path)"
    break
  fi
done
```

Also check if the macro-advisor plugin is installed by looking for its outputs in the Cowork plugin cache.

**If auto-detected:** Tell the user: "Found Macro Advisor outputs at [path]. I'll use this automatically." **Important:** Always resolve the path to an absolute path using `realpath` before saving to config. Never store a relative path — the trading engine may run from any working directory.

**If NOT auto-detected:** Ask the user using AskUserQuestion:

"The Trading Engine reads macro research from the Macro Advisor plugin but I couldn't auto-detect its location. Where are your Macro Advisor outputs?

If you haven't installed the Macro Advisor yet, select 'Not installed' — you can configure this later."

Options:
- [text input] — Paste the path to your Macro Advisor outputs directory
- Not installed yet — I'll set it up later

If user selects "Not installed yet", save `macro_advisor_outputs` as empty string in config and warn:

"Setup will continue, but the trading engine will skip all new trades until macro data is available. Install the macro advisor from this same marketplace and run `/macro-advisor:setup` followed by `/macro-advisor:run-weekly`, then update `config/user-config.json` with the outputs path."

**If user provided a manual path:** Resolve it to an absolute path using `realpath` before saving to config.

**Validation:** If a path was provided (auto or manual), verify it contains the expected structure:
```bash
# Resolve to absolute and verify
MACRO_PATH=$(realpath "$MACRO_PATH")
# Must contain synthesis/ and theses/ directories with at least one file
ls "$MACRO_PATH/synthesis/" "$MACRO_PATH/theses/" 2>/dev/null
```
If validation fails, warn that the macro advisor may not have completed a full cycle yet but save the resolved absolute path anyway.

## Step 6: Resolve Workspace Path

```bash
WORKSPACE_PATH=$(pwd)
echo "Workspace resolved to: $WORKSPACE_PATH"
```

Store this as `workspace_path` in the config (Step 8).

## Step 7: Create Output Directories

```bash
mkdir -p outputs/portfolio outputs/trades outputs/performance outputs/improvement outputs/dashboard
```

Create seed files for the improvement and trade trackers:

**outputs/improvement/amendment-tracker.md:**
```
# Trading Engine Amendment Tracker

Persistent record of all proposed amendments, their implementation status, and evaluation results.

## Amendment Status Lifecycle
PROPOSED → IMPLEMENTED → EVALUATED (EFFECTIVE / INEFFECTIVE / INCONCLUSIVE) → kept or REVERTED

---

## Active Amendments

| ID | Skill | Proposed | Implemented | Status | Target Metric | Before | After | Verdict |
|----|-------|----------|-------------|--------|---------------|--------|-------|---------|

## Reverted Amendments

None.

## Log

```

**outputs/improvement/performance-tracker.md:**
```
# Trading Engine Performance Tracker

Cumulative record of execution quality metrics across runs.

| Run Date | Run Type | Fill Rate | Slippage | Orders | Skipped | DA Rigor | Health Score |
|----------|----------|-----------|----------|--------|---------|----------|-------------|

```

**outputs/trades/trade-log.json:** `[]`
**outputs/trades/closed-trades.json:** `[]`

## Step 8: Schedule

Ask the user using AskUserQuestion:

"When should the trading engine run? It should run after the Macro Advisor finishes its weekly cycle."

Options: Sunday 19:00 CET (3 hours after macro advisor default), Sunday 20:00 CET, Custom time

Then ask about the Wednesday defense check:

"The trading engine also does a mid-week defense check (kill switches and drawdown only, no new trades)."

Options: Wednesday 18:00 CET (recommended), Skip Wednesday checks, Custom time

Create scheduled tasks based on their answers. **Use thin launcher prompts** — the schedule prompt should invoke `/trading-engine:run-trading` for both Sunday and Wednesday runs. The command automatically detects the day and applies defense-only mode on Wednesday (no new positions, kill switches only). Include only the workspace path and the command to run. All execution details live in the command files.

## Step 9: Write Configuration

Save all user preferences to `config/user-config.json`:

```json
{
  "workspace_path": "/absolute/path/to/workspace",
  "alpaca_api_key": "USER_KEY_HERE",
  "alpaca_secret_key": "USER_SECRET_HERE",
  "paper": true,
  "macro_advisor_outputs": "ABSOLUTE_PATH_TO_MACRO_OUTPUTS",
  "schedule_day": "sunday",
  "schedule_time": "19:00",
  "schedule_timezone": "CET",
  "wednesday_check": true,
  "wednesday_time": "18:00",
  "setup_completed": true,
  "setup_date": "YYYY-MM-DD"
}
```

The `workspace_path` is the absolute path resolved in Step 6. All commands read this on startup and `cd` to it, so output paths resolve correctly regardless of initial working directory.

## Step 10: Validation Run

Run T0 (portfolio snapshot) to verify the full pipeline works:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/trade_executor.py --action snapshot --config config/user-config.json --output outputs/portfolio/
```

Report results. If the snapshot succeeds, continue to Step 11.

## Step 11: External Portfolio (Optional)

Ask the user using AskUserQuestion:

"**External Portfolio Tracking (Optional)**

The trading engine can track your real-world holdings alongside the paper portfolio. This gives you:

- **Exposure awareness** — see what you're actually betting on across all your positions (sector, geography, currency, asset class), including look-through into ETF holdings
- **Kill switch propagation** — when the system invalidates a thesis, get alerts for your real positions that are aligned with that thesis
- **Gap analysis** — see where your real portfolio diverges from what the system's model portfolio recommends, and which thesis or regime view drives each gap

Your positions are never used as input to the trading engine's decisions — the paper portfolio stays a clean sandbox. This is purely informational.

Would you like to set up external portfolio tracking?"

Options: Yes — I want to track my real holdings, No — skip this for now

**If No:** Set `external_portfolio_enabled: false` in `config/user-config.json`. Tell the user: "No problem. You can set this up anytime later by running `/update-external-positions`." Skip to Step 15.

**If Yes:** Set `external_portfolio_enabled: true` and continue.

## Step 12: Base Currency

Ask the user using AskUserQuestion:

"What is your base currency? All external portfolio values will be converted to this currency for comparison."

Options: DKK, EUR, USD, GBP, CHF, SEK, NOK, Other (specify)

Save as `base_currency` in both `config/user-config.json` and `config/external-positions.json`.

## Step 13: Investable Asset Types

Ask the user using AskUserQuestion:

"What asset types do you invest in? The system won't flag exposure gaps in asset types you exclude. You can change this later."

Options (multi-select): Equities, Fixed Income / Bonds, Commodities, FX / Currency, Crypto, REITs

Save as `investable_asset_types` list in `config/external-positions.json`.

## Step 14: External Positions

Walk the user through adding their positions. For each position:

**14a.** Ask for the ticker symbol. Immediately validate and classify:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/external_portfolio.py --action classify --ticker "[TICKER]"
```

If the ticker is valid, show the user what the system found:
- Name, exchange, currency
- Classification: asset class, sector, geography
- For ETFs: category, sector weightings (top 3), top holdings (top 3)
- Current price

If the ticker is NOT valid (yfinance can't resolve it), tell the user:

"I couldn't find '[TICKER]' on Yahoo Finance. This could be a local fund, a delisted security, or a typo. You can:
1. Try a different ticker symbol (e.g., for Copenhagen stocks, use the .CO suffix like NOVO-B.CO)
2. Enter it as a manual position — I'll store it but you'll need to update the value manually"

**For manual positions:** Collect name, asset class (from investable types), primary sector, geography, currency, and current total value. Set `manual_valuation: true`.

**14b.** Ask for quantity (number of shares/units).

**14c.** Ask for entry price (optional): "What was your average entry price? This is optional — if you provide it, the dashboard will show your P&L. If not, it just tracks current value and exposure."

Options: [number input], Skip — just track current value

**14d.** Ask for entry date (optional): Same framing as entry price.

**14e.** Ask for account label (optional): "Which account is this in? This is just a label for your reference (e.g., 'Saxo', 'Pension', 'IBKR')."

Options: [text input], Skip

**14f.** Ask if there are more positions to add.

Options: Add another position, Done adding positions

Store all positions to `config/external-positions.json`. Format:

```json
{
  "last_updated": "YYYY-MM-DD",
  "base_currency": "DKK",
  "investable_asset_types": ["equities", "fixed_income", "commodities"],
  "positions": [
    {
      "ticker": "NOVO-B.CO",
      "name": "Novo Nordisk B A/S",
      "quantity": 50,
      "entry_price": 850.00,
      "entry_date": "2024-06-15",
      "currency": "DKK",
      "account": "Saxo",
      "manual_valuation": false,
      "classification": {
        "asset_class": "equities",
        "sector": "Healthcare",
        "industry": "Drug Manufacturers - General",
        "geography": "Denmark",
        "currency_exposure": "DKK"
      },
      "sector_weightings": null,
      "asset_classes": null
    }
  ]
}
```

Create output directory:
```bash
mkdir -p outputs/external
```

## Step 15: Final Summary

Report results. If everything passes, tell the user:

"Setup complete. Your Trading Engine is configured and scheduled. The first trading run will execute at [scheduled time] after the Macro Advisor completes its weekly cycle. You can also run it manually anytime with `/run-trading`."

If external portfolio was configured, add:
"External portfolio tracking is enabled with [N] positions ([total value in base currency]). The dashboard will include an External Portfolio tab showing exposure comparison, thesis alignment, and kill switch alerts. Update your positions anytime with `/update-external-positions`."

"**Important:** Make sure the Macro Advisor has completed at least one full weekly run before the trading engine runs. Without macro data, the engine will skip all trades."
