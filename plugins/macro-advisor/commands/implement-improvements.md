---
description: Review and apply self-improvement amendments proposed by the system
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Review the skill amendments proposed by the self-improvement loop (Skill 8) and let the user decide which to implement.

## Execution

1. Read `outputs/improvement/amendment-tracker.md` to find all proposed amendments that have not yet been implemented.

2. If no pending amendments exist, tell the user: "No pending amendments. The system will propose new improvements after the next weekly run."

3. For each pending amendment, present it to the user clearly:
   - Which skill it affects
   - What the proposed change is
   - Why it was proposed (the observation that triggered it)
   - Expected impact

4. Ask the user using AskUserQuestion for each amendment (or group related amendments):
   "Do you want to implement this amendment?"
   Options: Yes — implement it, No — skip it, Tell me more — explain the reasoning in detail

5. For amendments the user approves:
   - Apply the change to the relevant skill reference file in the working directory
   - Update the amendment tracker to mark it as implemented with the current date
   - Log the implementation so the next Skill 8 run can evaluate whether it improved results

6. For amendments the user skips:
   - Mark as "deferred" in the amendment tracker so Skill 8 does not re-propose the same change

7. After processing all amendments, summarize what was implemented and what was deferred.
