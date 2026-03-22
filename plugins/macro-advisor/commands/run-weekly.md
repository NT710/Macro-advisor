---
description: Run the full weekly macro analysis cycle manually
allowed-tools: Read, Write, Edit, Bash, Grep, WebSearch, WebFetch, ~~browser
---

Run the full Macro Advisor weekly analysis cycle. This executes the same sequence as the scheduled run.

## FIRST: READ THE RULES

Before doing anything else, read `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/RULES.md`. This contains non-negotiable data integrity guardrails, ETF-focused investment context, and language accessibility requirements. These rules apply to EVERY skill output.

**The cardinal rule: never invent numbers.** Every data point must come from the FRED/Yahoo data snapshot, a web search result, or an official publication. If you cannot find a number, say "data not available." Never estimate, infer, or fabricate.

## Pre-flight

1. Read `config/user-config.json` to load the user's configuration. If not found at the relative path, the working directory may not be the workspace — stop and tell the user to select their workspace folder in Cowork.
2. If config is missing or `setup_completed` is false, tell the user to run `/macro-advisor:setup` first and stop.
3. **Config upgrade check.** Read `${CLAUDE_PLUGIN_ROOT}/config/config-schema.json`. For every field that has an `upgrade_notice`, check if that field is entirely missing from `user-config.json` (not null — missing). For each missing field, collect its `upgrade_notice` message. If any notices were collected, show them all at once under a single header:
   > "**New capabilities available since your last setup:**"
   > - [each upgrade_notice]
   > "Your system works fine without these. Enable them when convenient by editing `config/user-config.json`."

   Then continue the run normally. Do not block.
4. Read `workspace_path` from config. If the current working directory does not match `workspace_path`, `cd` to `workspace_path` so all relative output paths resolve correctly.
5. Determine the current date and ISO week number. All output files use the format: `YYYY-Www-[skill-name].md`.
6. Read `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/SKILL.md` for system overview and execution chain.
7. **Record the start time.** Run `date +%s` and save the Unix timestamp. You'll need this at the end.
8. Read ETF references — two files, both consulted by Skills 7, 9, and 12:
   - `config/etf-overrides.md` (workspace) — currency-specific equivalents. Read first. May not exist if user chose USD.
   - `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/etf-reference.md` (plugin) — USD defaults and thematic/sector ETFs.

## SKILL 0: DATA COLLECTION (run first, always)

```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt --break-system-packages -q 2>/dev/null
```

Check if `outputs/data/latest-data-full.json` exists. If NOT (first run), use historical mode:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/ --mode historical
```

If it exists (subsequent runs), use weekly mode:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/ --mode weekly
```

Replace `FRED_KEY_FROM_CONFIG` with the actual key from `config/user-config.json`. EIA petroleum data, CFTC COT, and BIS credit data are all pulled automatically (no API key needed). Never hardcode keys in any output file.

Read `outputs/data/latest-snapshot.json` after completion. This snapshot is the data foundation for all subsequent skills.

## EXECUTION SEQUENCE: 0→1→2→3→4→5→10→13(bi-weekly)→6→7→11(if triggered)→8→12→9

Each skill MUST:
1. Read `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/RULES.md` (re-read for each skill to keep guardrails in context)
2. Read its skill definition file from `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/`
3. Read the data snapshot for hard numbers
4. Use web search only for qualitative context (not as a substitute for snapshot data)
5. Express investment views using specific ETF tickers (user's preferred currency where available, per `config/etf-overrides.md` and `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/etf-reference.md`)
6. Write in accessible language — explain acronyms, define technical terms
7. Save output with meta block (self-score, confidence, data gaps)
8. Never invent, estimate, or fabricate any data point

### SKILL 1: Central Bank Watch
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/01-central-bank-watch.md` + snapshot.
Save to: `outputs/collection/central-bank-watch/YYYY-Www-central-bank-watch.md`

### SKILL 2: Liquidity & Credit Monitor
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/02-liquidity-credit-monitor.md` + snapshot.
Save to: `outputs/collection/liquidity-credit/YYYY-Www-liquidity-credit.md`

### SKILL 3: Macro Data Tracker
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/03-macro-data-tracker.md` + snapshot.
Save to: `outputs/collection/macro-data/YYYY-Www-macro-data.md`

### SKILL 4: Geopolitical & Policy Scanner
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/04-geopolitical-policy-scanner.md` + snapshot for market context.
Save to: `outputs/collection/geopolitical/YYYY-Www-geopolitical.md`

### SKILL 5: Market Positioning & Sentiment
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/05-market-positioning-sentiment.md` + snapshot.
Save to: `outputs/collection/positioning/YYYY-Www-positioning.md`

### SKILL 10: External Analyst Monitor
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/10-analyst-monitor.md`
Monitor 8 external macro analysts across two groups:
- **Group A (frequent):** Andreas Steno (X), Luke Gromen (X), Alfonso Peccatiello/Macro Compass (Substack), MacroVoices (podcast transcripts)
- **Group B (less frequent):** Howard Marks/Oaktree (memos), Lyn Alden (monthly newsletter), Evergreen Gavekal (blog), Alpine Macro (LinkedIn)

Browse X feeds and LinkedIn via Chrome. Use WebFetch for Substack, Oaktree, Lyn Alden, Evergreen Gavekal, and MacroVoices (these don't require Chrome). Read with fresh eyes — no pre-loaded expectations. Report what they're actually saying, with dates. Follow links to full articles — the feed headlines are teasers, the articles contain the real analysis.
Group B sources: check for new content first. If nothing new since last week, note it in one line and move on. Don't re-analyze stale content.
If Chrome/browser unavailable (check `browser_access` in config), fall back to web search for the social media sources.
Save to: `outputs/collection/YYYY-Www-analyst-monitor.md`
Also update: `outputs/collection/analyst-themes.md` (overwrite with current themes — see Skill 10 Step 5).

### SKILL 13: Structural Scanner (bi-weekly)
Read: `outputs/structural/last-scan.json`. If `last_run_date` exists and is fewer than 12 days ago, skip: "Structural scanner: last ran [date], skipping this cycle." If the file doesn't exist (first run), proceed.
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/13-structural-scanner.md` + snapshot + full data file.
Runs Phase 1 (signal detection) → Phase 2 (screening) → Phase 3 (candidate generation) → Phase 4 (contrarian pass).
Has full data access: can pull on-demand FRED series, use web search, read snapshot.
Save scan to: `outputs/structural/YYYY-Www-structural-scan.md`
Save candidates to: `outputs/structural/candidates/CANDIDATE-[domain-slug]-[date].md`
Update: `outputs/structural/last-scan.json`
Candidates are consumed by Skill 7 as structural thesis candidates (alongside data patterns and analyst-sourced candidates).

### SKILL 6: Weekly Macro Synthesis
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/06-weekly-macro-synthesis.md` + ALL collection outputs (Skills 1-5) + analyst monitor (Skill 10) + snapshot + prior synthesis (if exists in `outputs/synthesis/`).
**Note:** Do NOT read Skill 13 (Structural Scanner) output here. The synthesis is a cyclical regime assessment. Structural imbalances enter through a separate pipeline: Skill 13 → Skill 11 → Skill 7.
Save to: `outputs/synthesis/YYYY-Www-synthesis.md`

### SKILL 7: Thesis Generator & Monitor
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/07-thesis-generator-monitor.md`
Read: synthesis + active theses in `outputs/theses/active/` + analyst themes index (`outputs/collection/analyst-themes.md`) + current week analyst monitor output (`outputs/collection/YYYY-Www-analyst-monitor.md`) + data snapshot. If a theme in the index is relevant to an active thesis, follow the Detail link to read the full weekly analyst file for substance.
**Function A (Generate):** Three thesis sources:
- **Data patterns:** Scan synthesis for divergences, dislocations, regime shifts per standard process.
- **Analyst-sourced candidates:** Scan analyst monitor for structural views or novel frameworks not captured by existing theses or the synthesis. Max 2 analyst-sourced investigation candidates per week. Each auto-triggers Skill 11 — no human gate. Tag provenance as "analyst-sourced: [name]" on every candidate.
- **Structural scanner candidates:** Read `outputs/structural/candidates/` for any CANDIDATE- files not yet processed. These are structural imbalances identified by Skill 13's signal-based detection. Each auto-triggers Skill 11 for full or focused research. Tag provenance as "structural-scanner" on every candidate. Do not duplicate — if a scanner candidate overlaps with an existing thesis or current-week data pattern, note the convergence but don't create a second thesis.
**Function B (Monitor):** Cross-reference analyst monitor findings against active thesis assumptions, kill switches, and mechanisms. If external insights are directly relevant to a thesis parameter, flag as "Parameter Review" and write finding to thesis file.
For structural thesis candidates: check for existing Skill 11 research brief in `outputs/research/`. If none exists, flag for Skill 11 invocation — do not generate a structural thesis without the research foundation.
For themes not in the ETF reference table, run:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/etf_lookup.py --theme "[keywords]"
```
Save candidates to: `outputs/theses/active/DRAFT-[name].md`
Save monitor: `outputs/collection/YYYY-Www-thesis-monitor.md`

### SKILL 11: Structural Research (IF TRIGGERED by Skill 7)
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/11-structural-research.md`
Runs if Skill 7 flagged a structural thesis candidate (from data patterns, analyst-sourced, or structural scanner). Most weeks this does not fire. When triggered by a scanner candidate, the candidate file already contains the quantified imbalance, binding constraint, and bear case inputs — use these as Phase 1 starting points rather than researching from scratch.
Data access: read `outputs/data/latest-snapshot.json` first. For FRED series not in the snapshot, pull on-demand to `outputs/data/research-temp/`. Use `etf_lookup.py` for price data. Web search for everything else.
For analyst-sourced investigations: the analyst's framework is a hypothesis to test, not a conclusion. Evidence independence must be assessed — if the research can't find support beyond the originating analyst's own claims, conviction is reduced.
Save to: `outputs/research/STRUCTURAL-[theme-name]-[date].md`

### SKILL 8: Self-Improvement Loop
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/08-self-improvement-loop.md` + meta blocks from all outputs (including Skill 13 structural scanner meta, if it ran this cycle) + structural scanner last-run tracker (`outputs/structural/last-scan.json`) + prior improvement output (if exists).
CRITICAL: Read the amendment tracker (`outputs/improvement/amendment-tracker.md`) FIRST to check which amendments are already implemented. Do not re-propose implemented amendments. Evaluate implemented amendments against current metrics and update the tracker with results.
Assess both data quality AND reasoning quality. Includes scanner health checks: emptiness ratio, kill rate, provenance distribution, domain recurrence, and sector clustering.
Save to: `outputs/improvement/YYYY-Www-improvement.md`
Update: `outputs/improvement/amendment-tracker.md` with evaluation results.
Update: `outputs/improvement/accuracy-tracker.md` with this week's scorecard.

### SKILL 12: Thesis Presentation
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/12-thesis-presentation.md`
Read: all thesis files in `outputs/theses/active/` + data snapshot + full data file.
For structural theses: also read the corresponding Skill 11 research brief from `outputs/research/`.
Render each active/draft thesis into:
- Mode A: Full thesis report (saved to `outputs/theses/presentations/[thesis-name]-report.md`)
- Mode B: Briefing card (consumed by Skill 9)
- Chart specs (saved to `outputs/theses/presentations/[thesis-name]-charts.json`)
CRITICAL: Do not editorialize. Render what Skill 7 and Skill 11 produced. Do not add, remove, or reweight analytical conclusions.

### SKILL 9: Monday Morning Briefing
Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/09-monday-briefing.md` + synthesis + thesis monitor + Skill 12 presentation cards + improvement summary.
Read actual thesis files in `outputs/theses/active/` to determine status from filenames (ACTIVE- vs DRAFT-).
Read Skill 12 briefing cards from `outputs/theses/presentations/` for the Active Theses section.
If Skill 12 output is missing (error recovery only), generate cards directly from thesis files.
Write for a smart non-specialist. Explain acronyms. Use ETF tickers (user's preferred currency as primary). Keep under 5 minutes reading time.
Save to: `outputs/briefings/YYYY-Www-briefing.md`

## DASHBOARD GENERATION

After Skill 9, generate the HTML dashboard:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/generate_dashboard.py \
  --week YYYY-Www \
  --output-dir outputs/ \
  --plugin-root ${CLAUDE_PLUGIN_ROOT} \
  --out outputs/briefings/YYYY-Www-dashboard.html
```

## Post-run

**Calculate elapsed time.** Run `date +%s` again and subtract the start timestamp from pre-flight step 6. Convert to minutes.

Present to the user:

1. **Monday Morning Briefing** — the dashboard HTML file and briefing markdown
2. **Regime identified** — which quadrant, confidence level, and whether it changed from last week
3. **Active theses** — count of ACTIVE- and DRAFT- files, any new or invalidated this week
4. **Structural scanner** — if it ran this cycle: signal hit rate, domains advanced, candidates generated. If skipped: "Structural scanner: last ran [date], next cycle [date]."
5. **Self-improvement** — system health score and count of proposed amendments
6. **Run time** — "This run covered 90+ economic data series (FRED, Yahoo, CFTC COT, ECB, Eurostat, EIA, BIS), 8 external analysts, structural scanning (if bi-weekly cycle), regime identification, thesis generation, self-improvement scoring, and a full HTML dashboard. For a human analyst, that's roughly 2-3 days of work. Claude did it in [X] minutes."

If Skill 8 proposed any amendments, include: "X skill amendments proposed this week. Run `/macro-advisor:implement-improvements` to review and apply them."

## CRITICAL RULES (reinforced)

1. Read RULES.md before anything else and re-read before each skill.
2. Run Skill 0 first. Everything depends on it.
3. Execute in order: 0→1→2→3→4→5→10→13(bi-weekly)→6→7→11(if triggered)→8→12→9.
4. Every number must be sourced. Never fabricate.
5. All investment views use specific ETF tickers. User's preferred currency where available.
6. Write briefing and theses in accessible language.
7. Analyst monitor reads feeds with fresh eyes — no pre-loaded expectations.
8. Thesis monitor must cross-reference analyst insights against active thesis parameters.
9. Improvement loop reads the amendment tracker first. Never re-propose implemented amendments.
10. Kill switches on theses are absolute. Met = INVALIDATED, no negotiation.
11. First-ever run uses historical data mode (5 years).
12. Always deliver briefing + theses + improvement doc.
13. Skill 12 renders thesis presentations — it does not generate analytical content or editorialize.
14. Structural theses require a Skill 11 research brief before generation. Flag if missing.
15. Analyst-sourced thesis candidates must be tagged with provenance. Max 2 per week. Skill 11 is the quality filter — not a human approval gate.
16. Analyst-sourced investigations must produce independent evidence. If evidence base relies primarily on the originating analyst, conviction is reduced.
