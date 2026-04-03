# Universal Rules — Apply to EVERY Trading Skill

Read this file before executing any skill. These rules override all other instructions.

## Risk Constraints (Hardcoded — Not Adjustable by Improvement Loop)

1. **Max single position: 15% of portfolio.** No single ETF can exceed 15% of total portfolio value at time of entry. If market movement pushes it above 15%, flag for rebalance — do not force-sell immediately.

2. **Max sector concentration: 30%.** No GICS sector can exceed 30% of total equity allocation. Measured at time of new entry, not retroactively.

3. **Max drawdown trigger: 10%.** If total portfolio value drops 10% from its all-time high watermark, raise cash to 25% minimum by closing weakest-conviction positions first. This is a circuit breaker, not a trading signal.

4. **Minimum cash: 5%.** Always hold at least 5% in cash or cash equivalents (SGOV/BIL). Measured after every trade execution.

5. **Max thesis overlay: 25% of portfolio.** Total allocation to thesis-driven positions (tactical + structural combined) cannot exceed 25%. The remaining 75%+ is regime-driven strategic allocation.

6. **No leverage.** Paper trading account should not use margin for leveraged positions. 1x only.

7. **No short selling.** Long-only portfolio. If a thesis says "reduce/avoid" an asset, we simply don't hold it — we don't short it.

## Execution Discipline

1. **Kill switch = immediate exit.** When the macro advisor marks a thesis INVALIDATED, the next trading engine run closes all positions associated with that thesis. Market order. No discretion, no "let's wait one more day." This is the single most important rule.

2. **Scale in, not all-at-once.** New positions are built over 2 runs (tactical) or 3-4 runs (structural). First entry is 50% of target size. Subsequent runs bring it to full size if conditions still hold.

3. **Regime change = gradual rotation.** When the macro synthesis reports a regime shift, rotate over 2-3 runs. Don't fire-sale the old regime allocation. Exception: if the shift is to Stagflation from any other regime, accelerate rotation to 1-2 runs (Stagflation destroys value fastest).

4. **Orders use limit prices during market hours.** For non-urgent trades, use limit orders with a 0.3% buffer from last close. For kill-switch exits, use market orders.

5. **Trade only during market hours.** All orders submitted with time_in_force="day". No extended-hours trading.

## Data Integrity

1. **Never fabricate portfolio data.** Every position, P&L figure, and allocation percentage must come from Alpaca's API response. If the API is down, skip the run and log it.

2. **Log every decision.** Every trade and every decision NOT to trade gets logged with full reasoning. The trade log is the primary audit trail.

3. **Separate facts from reasoning.** The portfolio snapshot (T0) is fact. The signal parser (T1) is interpretation. The trade reasoner (T3) is judgment. Label each clearly.

## Anti-Confirmation-Bias Rules

1. **T3 does not see P&L.** The trade reasoner receives current positions and their sizes, but NOT their unrealized profit/loss. Decisions are based on macro signals and thesis status, not on whether a position is winning or losing.

2. **T1 is stateless.** The signal parser reads the macro advisor outputs fresh each run. It does not remember or reference prior parses. If the regime changed, it reports the change without anchoring to last week's signal.

3. **Devil's advocate is mandatory.** Before every new position entry, T3 must articulate the bear case — what specific scenario makes this trade lose money. This gets logged. The improvement loop tracks whether realized losses matched articulated bear cases or came from unarticulated risks.

4. **T7 does not optimize by asset class.** The self-improvement loop tracks performance by thesis mechanism type (divergence, regime shift, positioning extreme, etc.) and by time horizon (tactical vs structural). It does NOT optimize sizing by which asset classes recently performed well. That's survivorship bias.

5. **Sizing follows reasoning, not expression order.** The trade reasoner evaluates every ETF expression in a thesis — first, second, or third-order — on its own merits. There is no mechanical formula mapping expression order to position size. The reasoner must articulate conviction reasoning for each expression it includes. A third-order expression can be sized larger than a first-order one if the thesis logic and macro context support it. Expressions are skipped when the reasoning doesn't support them, not because of their order.

6. **Empirical sentiment is never sole justification.** The analog matcher's risk/reward ratios (from `empirical-sentiment.json`) are informational context, not directional signals. Out-of-sample testing showed the model does not beat naive baselines. T3 must never cite empirical sentiment as the primary reason for a position or sizing decision. It must be corroborated by a named, concrete signal (regime template allocation, active thesis direction, or specific data point from the macro synthesis). "Qualitative reasoning" alone does not count as corroboration.

## External Portfolio Rules

1. **T8 is informational only.** External portfolio data never flows back into T1-T7. The paper portfolio does not know about, reference, or adjust for the user's real holdings.

2. **Separate value tracking.** Paper portfolio P&L and external portfolio P&L are never combined, blended, or presented as a single number. They are always shown as distinct datasets.

3. **No trade recommendations.** T8 shows exposure gaps and thesis alignment. It does not recommend specific trades, position sizes, or timing for the user's real portfolio. The framing is always: "here's what the data shows" not "here's what you should do."

4. **Kill switch alerts are informational.** When a thesis is invalidated, T8 flags aligned external positions. It does not assume the user should sell — the user's real portfolio has constraints (tax, lockup, risk tolerance) the system doesn't know about.

5. **Deltas only show investable asset classes.** Allocation deltas between paper and external are only computed for asset classes the user marked as investable. Paper exposure in non-investable asset classes (e.g., commodities when the user only trades equities and bonds) is reported as a single structural summary line — not as per-position gaps, not as actionable divergences.

6. **Thesis alignment matches on exposure, not instrument.** T8 checks sector/geography/factor overlap between external holdings and thesis direction. The asset class of the instrument is irrelevant — a gold miner equity overlaps with a "long gold" thesis even if the paper portfolio expresses it via a commodity ETF. This prevents false comfort ("no thesis overlap") when the user's equity holdings carry the same macro exposure through a different wrapper.

## Interface with Macro Advisor

1. **Read-only.** The trading engine reads macro advisor outputs. It never writes to, modifies, or provides feedback to the macro advisor directories.

2. **Source paths:**
   - Weekly synthesis: `{macro_advisor_outputs}/synthesis/`
   - Active theses: `{macro_advisor_outputs}/theses/active/`
   - Closed theses: `{macro_advisor_outputs}/theses/closed/`
   - Data snapshot: `{macro_advisor_outputs}/data/`
   - ETF reference: `{macro_advisor_skills}/references/etf-reference.md`

3. **If macro advisor outputs are missing or stale (>7 days old), do not trade.** Log the gap and wait for the next macro run.
