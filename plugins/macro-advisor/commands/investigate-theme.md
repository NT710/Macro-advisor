---
description: Investigate a macro theme idea — run deep research, check latest data, and evaluate thesis potential
allowed-tools: Read, Write, Edit, Bash, Grep, WebSearch, WebFetch
---

Investigate a user-identified macro theme. This command runs a focused research cycle outside the weekly chain, combining the latest data snapshot with Skill 11 structural research and Skill 7 thesis evaluation.

Use this when the user spots something interesting — a data pattern, a news development, a structural shift — and wants to explore whether it warrants an investment thesis.

## FIRST: READ THE RULES

Read `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/RULES.md`. These guardrails apply to all analytical output.

## Pre-flight

1. Read `config/user-config.json`. If missing or `setup_completed` is false, tell the user to run `/macro-advisor:setup` first.
2. Read `workspace_path` from config. If the current working directory does not match, `cd` to `workspace_path`.
3. Determine the current date and ISO week (YYYY-Www format) for output filenames.
4. Read ETF references:
   - `config/etf-overrides.md` (workspace, may not exist for USD users)
   - `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/etf-reference.md`

## Step 1: Understand the Theme

Ask the user (if they haven't already specified):
- **What is the theme?** One sentence describing what they're seeing.
- **What triggered it?** A data point, news event, or pattern they noticed.
- **Time horizon?** Weeks-to-months (tactical) or quarters-to-years (structural)?

If the user has already described the theme in their message, extract these elements directly — don't ask again.

## Step 2: Check Latest Data

Read `outputs/data/latest-snapshot.json` for the most recent data foundation.

If the snapshot is more than 7 days old, refresh it:
```bash
pip install -r ${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt --break-system-packages -q 2>/dev/null
python ${CLAUDE_PLUGIN_ROOT}/scripts/data_collector.py --fred-key "FRED_KEY_FROM_CONFIG" --output-dir outputs/data/ --mode weekly
```

Identify which data series in the snapshot are directly relevant to the theme. Pull the specific numbers — levels, trends, percentile ranks.

## Step 3: Check Existing Work

Before duplicating effort:
- Check `outputs/theses/active/` for any existing theses touching this theme
- Check `outputs/research/` for any prior Skill 11 research briefs on this theme
- Check the latest synthesis (`outputs/synthesis/`) for related regime context

Report what already exists. If a closely related thesis is active, note its current status and what the new investigation might add or change.

## Step 4: Run Structural Research (Skill 11)

Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/11-structural-research.md`

Execute the full Skill 11 three-phase process:
- **Phase 1:** First-principles framing (150-200 words, binding constraints, key variables)
- **Phase 2:** Structured research (6 passes with decision gate after Pass 2)
  - Use web search for current data, policy context, positioning, contrarian views
  - Decision gate: If the supply-demand gap or structural constraint doesn't show material significance, stop and report honestly — "not a structural constraint at this time"
- **Phase 3:** Output the Structural Research Brief

Save to: `outputs/research/STRUCTURAL-[theme-name]-[date].md`

## Step 5: Thesis Evaluation (Skill 7 Assessment)

Read: `${CLAUDE_PLUGIN_ROOT}/skills/macro-advisor/references/07-thesis-generator-monitor.md`

Based on the research brief and data, evaluate:
1. **Does this warrant a thesis?** Apply the Skill 7 criteria — clear mechanism, testable assumptions, specific kill switches, implementable via ETFs.
2. **Tactical or structural?** Structural requires the Skill 11 brief (just completed). Tactical needs a clear catalyst within weeks/months.
3. **Conviction level?** High / Medium / Low, with explicit reasoning.

If the theme passes evaluation, generate a DRAFT thesis:
- For themes not in the ETF reference table, run:
  ```bash
  python ${CLAUDE_PLUGIN_ROOT}/scripts/etf_lookup.py --theme "[keywords]"
  ```
- Save to: `outputs/theses/active/DRAFT-[theme-name].md`

If the theme does NOT pass evaluation, explain why clearly. Common reasons: mechanism too vague, no testable kill switch, insufficient data support, already priced in, or not actionable via ETFs.

## Step 6: Present Findings

Summarize for the user:
1. **Theme:** What was investigated
2. **Data context:** Key numbers from the snapshot relevant to this theme
3. **Research verdict:** What the first-principles analysis found (binding constraints, key variables, supply-demand picture)
4. **Thesis decision:** Generated / Not generated, with reasoning
5. **If generated:** Thesis name, type (tactical/structural), conviction, primary ETF expression, key kill switch
6. **Next steps:** When the thesis will be monitored (next weekly run), what would change the view

Keep the language accessible. Write for a smart non-specialist.
