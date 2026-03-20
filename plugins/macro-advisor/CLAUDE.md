# Macro Advisor — Project Instructions

This is an autonomous macro research system. When working in this folder, follow these instructions.

## Architecture Documentation

The system's methodology, architecture, and design decisions are documented in `methodology.md`. This is the source of truth for how the system works.

**When you change any architectural decision — execution order, skill additions, new data sources, delivery format changes, analytical framework updates — update `methodology.md` to reflect the change.** The methodology doc must always match the current state of the system. If a user reads methodology.md, they should understand exactly how the system works today, not how it worked three iterations ago.

## Key Files

- `skills/RULES.md` — universal policy (data integrity, sizing, language, discipline). Read before executing any skill.
- `skills/references/etf-reference.md` — ETF lookup tables (broad, thematic, currency-specific equivalents).
- `methodology.md` — full system documentation. Keep in sync with any changes.
- `outputs/improvement/amendment-tracker.md` — persistent record of skill amendments and their effectiveness.
- `outputs/improvement/accuracy-tracker.md` — persistent record of analytical call accuracy.

## Scheduled Task

The weekly analysis runs on the user's configured schedule (set during `/macro-advisor:setup`). Execution order: 0→1→2→3→4→5→10→6→7→11(if triggered)→8→12→9. Delivers an HTML dashboard.

## Principles

1. Never invent numbers. Every data point must be sourced.
2. The Alpine Macro framework (liquidity-first, four-quadrant regime model) is our belief system. We commit to it. Contradictions in the data are observations, not framework failures.
3. No confirmation bias. Derive conclusions from current data. No pre-loaded causal chains. Analyst feeds read with fresh eyes.
4. ETF-focused, listed in user's preferred currency where available (set in `config/user-config.json`). Theses use first/second/third-order ETF chains verified via etf_lookup.py.
5. Plain language in all user-facing outputs. Write for a smart friend who invests in ETFs.
6. The self-improvement loop checks data quality, reasoning quality, and analytical accuracy. The accuracy tracker is the most important long-term output.
