# Macro Advisor — Project Instructions

This is an autonomous macro research system.

## File Location Convention

This plugin uses two locations:

- **`${CLAUDE_PLUGIN_ROOT}/`** — Plugin code (scripts, skill references, RULES.md, etf-reference.md, methodology.md). Read-only at runtime. Lives in Cowork's plugin cache.
- **Workspace** — All runtime data: `outputs/`, `config/user-config.json`, `config/etf-overrides.md`. Written during setup and each run. Persists in the user's selected Cowork folder.

The workspace path is stored as `workspace_path` in `config/user-config.json` (resolved to an absolute path during setup). On startup, every command reads this config and `cd`s to the workspace path. This ensures output paths resolve correctly regardless of the initial working directory.

When reading plugin code, use `${CLAUDE_PLUGIN_ROOT}/`. When reading or writing outputs and user config, use relative paths from the workspace (e.g., `outputs/synthesis/`, `config/user-config.json`).

## Architecture Documentation

The system's methodology, architecture, and design decisions are documented in `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/methodology.md`. This is the source of truth for how the system works.

**When you change any architectural decision — execution order, skill additions, new data sources, delivery format changes, analytical framework updates — update `methodology.md` to reflect the change.** The methodology doc must always match the current state of the system. If a user reads methodology.md, they should understand exactly how the system works today, not how it worked three iterations ago.

## Key Files

- `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/RULES.md` — universal policy (data integrity, sizing, language, discipline). Read before executing any skill.
- `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/etf-reference.md` — ETF lookup tables (USD defaults, broad, thematic).
- `config/etf-overrides.md` — Currency-specific ETF equivalents (workspace, generated during setup).
- `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/methodology.md` — full system documentation. Keep in sync with any changes.
- `outputs/improvement/amendment-tracker.md` — persistent record of skill amendments and their effectiveness (workspace).
- `outputs/improvement/accuracy-tracker.md` — persistent record of analytical call accuracy (workspace).

## Scheduled Task

The weekly analysis runs on the user's configured schedule (set during `/macro-advisor:setup`). Execution order: 0→1→2→3→4→5→10→14(quarterly)→13(bi-weekly)→streak→6→6b→6c→7→11(if triggered)→blind-spot-refresh→8→12→9. Delivers an HTML dashboard.

## Principles

1. Never invent numbers. Every data point must be sourced.
2. The Alpine Macro framework (liquidity-first, eight-regime model: Growth × Inflation × Liquidity) is our belief system. We commit to it. Contradictions in the data are observations, not framework failures.
3. No confirmation bias. Derive conclusions from current data. No pre-loaded causal chains. Analyst feeds read with fresh eyes.
4. ETF-focused, listed in user's preferred currency where available (set in `config/user-config.json`). Theses use first/second/third-order ETF chains verified via etf_lookup.py.
5. Plain language in all user-facing outputs. Write for a smart friend who invests in ETFs.
6. The self-improvement loop checks data quality, reasoning quality, and analytical accuracy. The accuracy tracker is the most important long-term output.
