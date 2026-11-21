# Terraform construct spec: `example_widget`

Status: BLOCKED
Category: resource
Provider revision: 0123456789abcdef

## Summary

Port the provider resource as `example.widget`.

## Sources

- `internal/provider/widget.go:10-80`

## Target precedents

- Runtime: `pkg/runtime/typed.go:10-80` defines the target lifecycle.
- Sibling: `internal/service/example/other_rsrc.go:10-100` uses the established lifecycle.

## Target mapping

- Register `widget` in the example service library.

## Lifecycle and invocation

- Create, read, update, and delete persistent remote state.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | UNRESOLVED | Terraform stores partial state after Create fails. | `widget.go:20` | Add partial state to the target runtime. |

## Schema and operations

- `name` is required and replacement-only.

## Exclusions

- Provider diagnostics are not part of the target contract.

## Coverage

- Unit, schema, registration, and emulator coverage are required.

## Open questions

- Question: Must the target runtime persist partial state after Create fails?
- Blocker type: RUNTIME_GAP
- Required authority: Runtime maintainer.
- Target alternatives: Add partial state or fail Create.
- Recommended mapping: Add partial state.
