- [x] Define the `kb-verifier` subagent

## Why
After every compile/lint/reorg pass we want an independent agent to verify
integrity rather than trusting the script's own self-report.

## Done when
- `.claude/agents/kb-verifier.md` exists describing a subagent that:
  - reads the vault
  - verifies: no empty md, every raw/ file is either referenced by a wiki
    article or explicitly parked, all wiki internal links resolve, index.md
    line count matches file count, no files in `_archive/` that are linked
    from `wiki/` (archive should be dead).
  - returns a short PASS/FAIL report with specific file:line issues.
- Verifier is invoked manually once at the end of the run to prove it works.
