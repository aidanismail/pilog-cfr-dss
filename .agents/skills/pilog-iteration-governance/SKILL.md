---
name: pilog-iteration-governance
description: Plan, execute, review, and close a PILOG CFR DSS simulation iteration with traceable feedback, safe scope boundaries, and a mentor-driven next iteration.
---

# PILOG Iteration Governance

Use this skill for iteration planning, task selection, implementation sequencing, mentor review preparation, and iteration closure.

## Required reading order

1. `.agents/00_READ_CURRENT.md`
2. `.agents/ITERATION_STATE.json`
3. active task board in `.agents/tasks/`
4. latest iteration review in `.agents/reviews/`
5. `.agents/DECISIONS.md`

## Operating model

```text
PLAN -> TASK -> EXECUTE -> TEST -> REVIEW -> REFLECTION -> STATE UPDATE
```

Work on one bounded task at a time. A task is complete only when its acceptance criteria, test evidence, and review implications are recorded.

## Decision rules

- Mentor feedback is an accepted requirement until explicitly revised.
- AI takeaways are hypotheses. Validate data availability and business relevance before implementation.
- Do not advance to MVP because a script runs once. Iterations continue until final simulation validation is mentor-approved.
- A `blocked` outcome is valid. Record the missing definition, source, policy, or authority; do not fill the gap with an assumption.
- Preserve existing simulation evidence unless a task explicitly replaces it with tested behaviour.

## Iteration closure

Close each iteration with one of:

```text
accepted
needs-revision
blocked
```

The review must state what changed, what was tested, what remains uncertain, mentor feedback, decisions made, and the next task/iteration.

