# Terraform construct spec: `example_lookup`

Status: BLOCKED
Category: data-source
Provider revision: 0123456789abcdef

## Summary

The provider behavior is ambiguous.

## Sources

- `internal/provider/lookup.go:10-40`

## Target precedents

- Runtime: `pkg/runtime/typed.go:10-80` defines the target data-source contract.
- Sibling: `internal/service/example/item_data_source.go:10-100` cannot resolve empty-result meaning.

## Target mapping

- Candidate registration is `example.lookup`.

## Lifecycle and invocation

- Read remote data without side effects.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | UNRESOLVED | Empty results may be an error. | `lookup.go:30` | A user decision is required. |

## Schema and operations

- The result fields are computed.

## Exclusions

- None established.

## Coverage

- Coverage depends on the unresolved decision.

## Open questions

- Question: Should an empty result return null or an error?
- Blocker type: SOURCE_GAP
- Required authority: Complete provider production source or provider owner decision.
- Target alternatives: Return null or return an error.
- Recommended mapping: Return null because the closest target sibling treats absence as null.
