# Terraform construct spec: `example_restart`

Status: READY
Category: action
Provider revision: 0123456789abcdef

## Summary

Port the provider action as `example.restart`.

## Sources

- `internal/provider/restart_action.go:8-55`

## Target precedents

- Runtime: `pkg/runtime/typed.go:10-80` defines the target action contract.
- Sibling: `internal/service/example/reload_action.go:10-100` uses the established action contract.

## Target mapping

- Register `restart` in the example service library.

## Lifecycle and invocation

- Invoke the operation without persistent Terraform state.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | IMPLEMENT | Validation rejects an empty target. | `restart_action.go:22` | An action test proves the error. |

## Schema and operations

- `target` is required input.

## Exclusions

- Progress messages are not public outputs.

## Coverage

- Unit, schema, registration, and emulator coverage are required.

## Open questions

- None.
