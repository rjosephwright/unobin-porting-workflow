# Terraform construct spec: `example_lookup`

Status: READY
Category: data-source
Provider revision: 0123456789abcdef

## Summary

Invalid unresolved contract.

## Sources

- `lookup.go:1`

## Target precedents

- Runtime: `pkg/runtime/typed.go:10-80` defines the target data-source contract.
- Sibling: `internal/service/example/item_data_source.go:10-100` uses the established contract.

## Target mapping

- Register `lookup`.

## Lifecycle and invocation

- Read data.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | UNRESOLVED | Unknown. | `lookup.go:1` | Decide. |

## Schema and operations

- None.

## Exclusions

- None.

## Coverage

- Unit test.

## Open questions

- None.
