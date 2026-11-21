# Auditor artifact contract

Return one complete Markdown artifact using this structure:

```markdown
# Terraform construct audit: `<key>`

Status: PASS | FAIL | BLOCKED
Diff: <audited-diff-sha256>
Round: <positive-integer>

## Findings

| ID | Route | Severity | Problem | Evidence | Required change |
| --- | --- | --- | --- | --- | --- |
| A001 | PORT_GAP | high | Exact mismatch. | `file:line` | One correction. |

## Confirmed behavior

- Important spec obligations independently verified.

## Coverage

- Provider source, target implementation, helpers, and tests inspected.
- Construct entry filename follows the category convention in `../SKILL.md`.

## Remaining delta

- None.
```

Use `SPEC_GAP` when the source provider requires behavior absent from or incorrect in the spec. Use
`PORT_GAP` when the spec is correct but target code or tests do not satisfy it. Severities are
`critical`, `high`, `medium`, and `low`.

A `PASS` audit has no findings and exactly `- None.` under remaining delta. `FAIL` and `BLOCKED`
must state the remaining work. For later rounds, verify prior findings and inspect the immediate
interactions of the correction; do not repeat an unchanged first-round source inventory.

## Native input contract

Apply `input-constraints.md` independently. Verify Go Constraints() is in the construct entry file,
extracted through its real registration, and defines input validity once. Inspect pinned engine
checks and actual literal/evaluated/pending/unchanged/saved-plan tests; callback rejection and CRUD
success do not prove native enforcement. Missing declarations, duplicate validators, wrong method
placement, and NoOp/deferred apply bypasses are findings. Check valid omissions and historical
state destruction remain supported. Route incorrect source/target mapping to SPEC_GAP and missing
implementation/runtime integration to PORT_GAP with exact affected paths and ownership.
