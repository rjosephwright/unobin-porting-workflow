# Terraform construct spec: `example_function`

Status: READY
Category: function
Provider revision: 0123456789abcdef

## Summary

Invalid category.

## Sources

- `function.go:1`

## Target precedents

- Runtime: `pkg/runtime/typed.go:10-80` defines supported target categories.
- Sibling: `internal/service/example/restart_action.go:10-100` is the closest category precedent.

## Target mapping

- Register a function.

## Lifecycle and invocation

- Call it.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | IMPLEMENT | Run. | `function.go:1` | It runs. |

## Schema and operations

- None.

## Exclusions

- None.

## Coverage

- Unit test.

## Open questions

- None.
