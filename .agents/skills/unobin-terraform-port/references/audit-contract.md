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

For a `PASS` audit, the Findings section must contain exactly `- None.`; omit the empty
findings table. A `PASS` audit also has exactly `- None.` under remaining delta. `FAIL` and `BLOCKED`
must state the remaining work. For later rounds, verify prior findings and inspect the immediate
interactions of the correction; do not repeat an unchanged first-round source inventory.

## Native input contract

Check compiler tests and fixtures against the target's established layout. Flag compiler-only
checks that bypass an existing compile-test suite. Keep runtime and lifecycle tests with the
relevant construct or integration tests.

Flag tests that only restate registration names, total counts or getters. Require actual input or
runtime behavior; collection assertions must check contents rather than lengths alone. Compiled
valid/invalid fixtures and executed native rules establish registration and schema behavior.

Apply `input-constraints.md` independently. For Go, verify Constraints() is in the construct entry
file. Verify native declarations define input validity once and are extracted through production
registration. Inspect pinned engine checks and tests for literal, evaluated, pending, unchanged,
and saved-plan inputs. Require tests that exercise native enforcement. Flag missing declarations,
duplicate validators, wrong method placement, and NoOp or deferred apply bypasses. Check valid
omissions and destruction of historical state. Route incorrect source-to-target mappings to
SPEC_GAP and missing implementation or runtime integration to PORT_GAP. Include the affected
paths and their owners.
