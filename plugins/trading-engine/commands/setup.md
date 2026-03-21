---
description: First-run setup — install alpaca-py, configure API keys, verify macro advisor, and schedule trading runs
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Run the first-time setup for the Trading Engine. Execute each step sequentially. Do not skip steps.

## Step 0: Verify Workspace Folder

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
  "../Marco economics/Macro Advisor/outputs"; do
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

Create scheduled tasks based on their answers.

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

Report results. If everything passes, tell the user:

"Setup complete. Your Trading Engine is configured and scheduled. The first trading run will execute at [scheduled time] after the Macro Advisor completes its weekly cycle. You can also run it manually anytime with `/run-trading`.

**Important:** Make sure the Macro Advisor has completed at least one full weekly run before the trading engine runs. Without macro data, the engine will skip all trades."
