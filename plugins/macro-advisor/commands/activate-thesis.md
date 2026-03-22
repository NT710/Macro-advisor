---
description: List draft theses and activate selected ones
allowed-tools: Read, Write, Edit, Bash, Grep
---

Activate one or more draft theses from the current thesis pipeline.

## Pre-flight

1. Read `config/user-config.json`. If missing or `setup_completed` is false, tell the user to run `/macro-advisor:setup` first.
2. Read `workspace_path` from config. If the current working directory does not match, `cd` to `workspace_path`.

## Step 1: Read the Latest Briefing Recommendations

Find the most recent Monday Briefing in `outputs/briefings/` (latest by date). Read the **Draft candidates** table — this contains the recommendation for each draft thesis (activate/watch/discard), conviction level, one-line summary, and reasoning.

Present it to the user as-is:

```
From this week's briefing — draft thesis recommendations:

| Thesis | Conviction | Summary | Recommendation | Why |
|--------|-----------|---------|---------------|-----|
| [from briefing] | [H/M/L] | [from briefing] | [activate/watch/discard] | [from briefing] |
```

If no briefing exists yet, fall back to scanning `outputs/theses/active/` for `DRAFT-*.md` files and present a simple list:

```
No briefing found — listing draft theses without recommendations.
Run /macro-advisor:run-weekly first to get assessed recommendations.

1. [Thesis Name] (TACTICAL) — Conviction: [H/M/L]
   Claim: [one-line claim]
   Kill switch: [one-line kill switch]
```

## Step 2: Get User Selection

If the user already specified which thesis to activate (by name or number in their original message), use that. Otherwise ask:

"Which theses would you like to activate? Enter numbers (e.g., `1, 3`), `all`, `recommended` (activates only those marked activate in the briefing), or `none`."

The user can override any briefing recommendation — they can activate a thesis marked watch or discard one marked activate. The briefing recommendations are advisory, not gates.

## Step 3: Activate Selected Theses

For each selected thesis:

1. Rename `outputs/theses/active/DRAFT-[name].md` to `outputs/theses/active/ACTIVE-[name].md`
2. Inside the file, update the `**Status:**` line from `DRAFT — Pending review` to `ACTIVE — Monitoring`
3. Add an activation timestamp: `**Activated:** [current date]`

```bash
mv "outputs/theses/active/DRAFT-[name].md" "outputs/theses/active/ACTIVE-[name].md"
```

For any thesis the user chooses to discard:

1. Move `outputs/theses/active/DRAFT-[name].md` to `outputs/theses/archive/DISCARDED-[name].md`
2. Add a discard note at the top: `**Discarded:** [current date] — [reason]`

## Step 4: Confirm

Report what was done:

```
Activated:
- [Thesis Name] — now being monitored weekly
- [Thesis Name] — now being monitored weekly

Held as drafts:
- [Thesis Name] — will be re-assessed next cycle

Discarded:
- [Thesis Name] — moved to archive

These theses will be monitored in the next /run-weekly cycle. Kill switches are checked every run — if triggered, the thesis is automatically invalidated.
```
