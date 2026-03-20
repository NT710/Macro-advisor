---
description: Review and apply self-improvement amendments proposed by the trading engine
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

Review the skill amendments proposed by the self-improvement loop (T7) and let the user decide which to implement.

## Execution

1. Read `outputs/improvement/amendment-tracker.md` to find all proposed amendments that have not yet been implemented.

2. Also check the latest `outputs/improvement/*-trading-improvement.md` report for any new proposals not yet in the tracker.

3. If no pending amendments exist, tell the user: "No pending amendments. The system will propose new improvements after the next weekly run."

4. For each pending amendment, present it to the user clearly:
   - Which skill it affects
   - What the current instruction says
   - What the proposed change would be
   - Why it was proposed (the observation that triggered it)
   - Expected impact on which metric
   - Risk assessment

5. Ask the user using AskUserQuestion for each amendment (or group related amendments):
   "Do you want to implement this amendment?"
   Options: Yes — implement it, No — skip it, Tell me more — explain the reasoning in detail

6. For amendments the user approves:
   - Apply the change to the relevant skill reference file in `skills/trading-engine/references/`
   - Update the amendment tracker to mark it as IMPLEMENTED with the current date
   - Log the implementation so the next T7 run can evaluate whether it improved results

7. For amendments the user skips:
   - Mark as "DEFERRED" in the amendment tracker so T7 does not re-propose the same change

8. After processing all amendments, summarize what was implemented and what was deferred.

9. Regenerate the dashboard to reflect the updated improvement state:
   ```bash
   python scripts/generate_dashboard.py \
     --portfolio outputs/portfolio/ \
     --trades outputs/trades/ \
     --performance outputs/performance/ \
     --improvement outputs/improvement/ \
     --output outputs/dashboard/
   ```

## Guardrails

- NEVER implement amendments that modify risk constraints, anti-bias rules, kill switch discipline, or the devil's advocate requirement. If T7 somehow proposed such an amendment, flag it as an error and skip it.
- Read `skills/trading-engine/references/RULES.md` to verify no approved amendment would violate the universal rules.
