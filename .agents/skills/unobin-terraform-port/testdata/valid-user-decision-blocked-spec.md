# Terraform construct spec: `example_widget`

Status: BLOCKED
Category: resource
Provider revision: 0123456789abcdef

## Summary

Port the provider resource as `example.widget`.

## Sources

- `internal/provider/widget.go:10-80`

## Target precedents

- Runtime: `pkg/runtime/typed.go:10-80` supports top-level replacement fields.
- Sibling: `internal/service/example/other_rsrc.go:10-100` replaces a complete parent object.

## Target mapping

- Register `widget` in the example service library.

## Lifecycle and invocation

- Create, read, update, and delete persistent remote state.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | UNRESOLVED | One nested field is immutable while its parent has mutable fields. | `widget.go:20` | The chosen replacement rule has plan tests. |

## Schema and operations

- `settings` contains mutable and immutable fields.

## Exclusions

- Terraform path serialization is not part of the target contract.

## Coverage

- Plan tests must prove the selected replacement behavior.

## Open questions

- Question: Should a nested immutable change replace the parent or return a replacement-required error?
- Blocker type: USER_DECISION
- Required authority: Target library owner.
- Target alternatives: Replace every parent change or reject only the immutable transition.
- Recommended mapping: Reject only the immutable transition to avoid unnecessary replacement.
