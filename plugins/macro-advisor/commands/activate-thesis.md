---
description: List draft theses and activate selected ones
allowed-tools: Read, Write, Edit, Bash, Grep
---

Activate one or more draft theses from the current thesis pipeline.

## Pre-flight

1. Read `config/user-config.json`. If missing or `setup_completed` is false, tell the user to run `/macro-advisor:setup` first.
2. Read `workspace_path` from config. If the current working directory does not match, `cd` to `workspace_path`.

## Step 1: List All Draft Theses

Scan `outputs/theses/active/` for files matching `DRAFT-*.md`. For each draft, extract:
- The thesis name (from filename, cleaned)
- The plain English summary (first paragraph after `**Plain English Summary:**`)
- The claim (line after `**Claim:**`)
- The kill switch (line after `**Kill switch:**`)
- The classification (Tactical or Structural)

Present a numbered list:

```
Draft theses available for activation:

1. [Thesis Name] (TACTICAL)
   Claim: [one-line claim]
   Kill switch: [one-line kill switch]

2. [Thesis Name] (STRUCTURAL)
   Claim: [one-line claim]
   Kill switch: [one-line kill switch]

3. [Thesis Name] (TACTICAL)
   Claim: [one-line claim]
   Kill switch: [one-line kill switch]
```

If no drafts exist, tell the user: "No draft theses found. Run `/macro-advisor:run-weekly` or `/macro-advisor:investigate-theme` to generate thesis candidates."

## Step 2: Get User Selection

If the user already specified which thesis to activate (by name or number in their original message), use that. Otherwise ask:

"Which theses would you like to activate? Enter numbers (e.g., `1, 3`), `all`, or `none`."

## Step 3: Activate Selected Theses

For each selected thesis:

1. Rename `outputs/theses/active/DRAFT-[name].md` to `outputs/theses/active/ACTIVE-[name].md`
2. Inside the file, update the `**Status:**` line from `DRAFT — Pending review` to `ACTIVE — Monitoring`
3. Add an activation timestamp: `**Activated:** [current date]`

```bash
mv "outputs/theses/active/DRAFT-[name].md" "outputs/theses/active/ACTIVE-[name].md"
```

## Step 4: Confirm

Report what was activated:

```
Activated:
- [Thesis Name] — now being monitored weekly
- [Thesis Name] — now being monitored weekly

Not activated (remaining as drafts):
- [Thesis Name]

These theses will be monitored in the next /run-weekly cycle. Kill switches are checked every run — if triggered, the thesis is automatically invalidated.
```
