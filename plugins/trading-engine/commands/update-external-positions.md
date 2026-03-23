---
description: Set up, add, remove, or update external portfolio positions
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Manage the user's external portfolio positions. This command handles both first-time setup and ongoing CRUD operations. It modifies `config/external-positions.json` and `config/user-config.json` without running the full trading engine chain.

## Pre-Flight

1. Read `config/user-config.json`. If not found, tell the user to run `/trading-engine:setup` first and stop.

2. Check `external_portfolio_enabled`:
   - If `true`: external portfolio is already set up. Go to **Manage Existing Positions**.
   - If `false` or missing: external portfolio is not configured. Go to **First-Time Setup**.

---

## First-Time Setup

This runs when the user hasn't set up external portfolio tracking yet. It follows the same flow as setup Steps 11-14 but can be run independently after initial trading engine setup.

### Step 1: Explain and Opt In

Ask the user using AskUserQuestion:

"**External Portfolio Tracking**

The trading engine can track your real-world holdings alongside the paper portfolio. This gives you:

- **Exposure awareness** — see what you're actually betting on across all your positions (sector, geography, currency, asset class), including look-through into ETF holdings
- **Kill switch propagation** — when the system invalidates a thesis, get notices for your real positions with overlapping exposure
- **Allocation deltas** — see where your real portfolio differs from what the system's model portfolio shows, and what drives each difference

Your positions are never used as input to the trading engine's decisions — the paper portfolio stays a clean sandbox. This is purely informational.

Would you like to set up external portfolio tracking?"

Options: Yes — set it up, No — not now

**If No:** Set `external_portfolio_enabled: false` in `config/user-config.json`. Tell the user: "No problem. You can run this command anytime to set it up later." Stop.

**If Yes:** Continue.

### Step 2: Base Currency

Ask the user using AskUserQuestion:

"What is your base currency? All external portfolio values will be converted to this currency for comparison."

Options: DKK, EUR, USD, GBP, CHF, SEK, NOK, Other (specify)

Save as `base_currency` in `config/user-config.json`.

### Step 3: Investable Asset Types

Ask the user using AskUserQuestion:

"What asset types do you invest in? The system won't flag exposure differences in asset types you exclude. You can change this later."

Options (multi-select): Equities, Fixed Income / Bonds, Commodities, FX / Currency, Crypto, REITs

### Step 4: Add Positions

Walk the user through adding their positions using the **Add a New Position** flow below. Loop until the user says "Done adding positions."

### Step 5: Save and Enable

Create `config/external-positions.json` with all positions, base currency, and investable asset types.

Set `external_portfolio_enabled: true` in `config/user-config.json`.

Create output directory:
```bash
mkdir -p outputs/external
```

Report: "External portfolio tracking is set up with [N] positions ([total value in base currency]). The dashboard will include an External Portfolio tab on the next Sunday run. To add or remove positions, run this command again anytime."

Stop.

---

## Manage Existing Positions

This runs when external portfolio is already configured.

### Show Current State

Read `config/external-positions.json` and show the user their current positions as a summary table:
```
# | Ticker | Name | Qty | Account | Asset Class | Last Updated
```

Also show total position count and the last-updated date.

### Actions

Ask the user using AskUserQuestion:

"What would you like to do?"

Options:
- Add a new position
- Remove a position
- Update quantity (bought more or sold some)
- Update a manual valuation
- Change investable asset types
- Disable external portfolio tracking
- Done

### Add a New Position

1. Ask for the ticker symbol. Immediately validate and classify:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/external_portfolio.py --action classify --ticker "[TICKER]"
   ```

2. If the ticker is valid, show the user what the system found:
   - Name, exchange, currency
   - Classification: asset class, sector, geography
   - For ETFs: category, sector weightings (top 3), top holdings (top 3)
   - Current price

3. If the ticker is NOT valid (yfinance can't resolve it), tell the user:
   "I couldn't find '[TICKER]' on Yahoo Finance. This could be a local fund, a delisted security, or a typo. You can:
   1. Try a different ticker symbol (e.g., for Copenhagen stocks, use the .CO suffix like NOVO-B.CO)
   2. Enter it as a manual position — I'll store it but you'll need to update the value manually"

   **For manual positions:** Collect name, asset class (from investable types), primary sector, geography, currency, and current total value. Set `manual_valuation: true`.

4. Ask for quantity (number of shares/units).

5. Ask for entry price (optional): "What was your average entry price? This is optional — if you provide it, the dashboard will show your P&L. If not, it just tracks current value and exposure."
   Options: [number input], Skip — just track current value

6. Ask for entry date (optional).

7. Ask for account label (optional): "Which account is this in? This is just a label for your reference (e.g., 'Saxo', 'Pension', 'IBKR')."
   Options: [text input], Skip

8. Append to `positions` array in `config/external-positions.json`.

9. Update `last_updated` date.

### Remove a Position

Show numbered list of current positions. Ask which to remove (by number or ticker). Confirm before removing. Remove from `positions` array. Update `last_updated`.

### Update Quantity

Show numbered list. Ask which position to update. Ask for new quantity. Optionally ask for average entry price adjustment (if they bought at a different price). Update the position. Update `last_updated`.

### Update Manual Valuation

Show only manual-valuation positions. If none exist, tell the user "You don't have any manual-valuation positions." and return to Actions.

Ask which to update. Ask for current total value. Update `manual_current_price` (value / quantity). Update `last_updated`.

### Change Investable Asset Types

Show current investable types. Ask what to change (add or remove types). Update `investable_asset_types`. Update `last_updated`.

### Disable External Portfolio Tracking

Ask the user to confirm: "This will disable external portfolio tracking. Your position data will be preserved in config/external-positions.json — you can re-enable anytime by running this command again. Disable?"

Options: Yes — disable, No — keep enabled

If Yes: Set `external_portfolio_enabled: false` in `config/user-config.json`. Report: "External portfolio tracking disabled. The paper portfolio and trading engine are unaffected. Run `/update-external-positions` anytime to re-enable."

## After Any Change

After each action, ask if the user wants to make another change (loop back to Actions) or is done.

When done, save `config/external-positions.json` and run a price refresh:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/external_portfolio.py \
  --action refresh_prices \
  --config config/external-positions.json \
  --user-config config/user-config.json \
  --output outputs/external/
```

Report: "External positions updated. [N] positions tracked. Changes will be reflected in the next Sunday trading engine run, or you can run `/run-trading` now."
