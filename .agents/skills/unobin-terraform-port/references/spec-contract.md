# Investigator spec contract

Return one complete Markdown artifact using this structure:

```markdown
# Terraform construct spec: `<key>`

Status: READY | BLOCKED
Category: resource | data-source | action
Provider revision: <full-revision>

## Summary

One concise paragraph naming the source construct and target registration.

## Sources

- Provider registration, implementation, and behavior-affecting helpers with paths and lines.
- Any provider tests or local API model used to resolve a specific ambiguity.

## Target precedents

- Runtime: pinned target contract with paths and lines.
- Sibling: current same-category implementation with paths and lines, or the search proving none
  exists and the closest category precedent used instead.

## Target mapping

- Target service/library, registration name, implementation location, and category type.

## Lifecycle and invocation

- Resource: create, read, update, delete, import, retries, waits, and not-found handling.
- Data source: read, selection, pagination, empty and multiple results, and errors.
- Action: validation, invocation, progress, retries, waits, cancellation, and results.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | IMPLEMENT | Exact required behavior. | `file:line` | Executable proof. |

## Schema and operations

- Inputs, outputs, defaults, omission, constraints, sensitivity, replacement, and operations.

## Exclusions

- Terraform-framework behavior that does not affect the target contract.

## Coverage

- Source read and tests required for the target.

## Open questions

- None.
```

Allowed dispositions are `IMPLEMENT`, `EXCLUDE`, `VERIFY`, and `UNRESOLVED`. Use stable IDs starting
at `E001`. A `READY` spec cannot contain `UNRESOLVED`. A `BLOCKED` spec must contain at least one
`UNRESOLVED` row and use this exact `Open questions` structure:

```markdown
- Question: <one concrete unresolved decision>
- Blocker type: REQUIRED_INPUT | SOURCE_GAP | USER_DECISION
- Required authority: <source needed or user who must choose>
- Target alternatives: <bounded alternatives>
- Recommended mapping: <one recommendation and why>
```

`REQUIRED_INPUT` means a task-supplied snapshot, revision, target root, or contract is unavailable.
`SOURCE_GAP` means required production source is missing or contradictory. `USER_DECISION` means no
established target precedent resolves the issue and the remaining alternatives materially differ in
public behavior, security, or destructive behavior. A runtime difference alone is not a blocker
type. First apply the target-representation decision order in `transfer-model.md`.

Keep the artifact concise and omit a source-reading diary.
