# Terraform construct spec: `example_widget`

Status: READY
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
| E001 | IMPLEMENT | Omitted size uses the provider default. | `widget.go:20` | An omission test proves the request value. |
| E002 | VERIFY | Missing remote objects clear local state. | `widget.go:50` | A read test proves removal. |

## Schema and operations

- `name` is required and replacement-only.

## Exclusions

- Provider diagnostics are not part of the target contract.

## Coverage

- Unit, schema, registration, and emulator coverage are required.

## Open questions

- None.
