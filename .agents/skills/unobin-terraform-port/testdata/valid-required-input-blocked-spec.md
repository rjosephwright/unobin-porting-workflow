# Terraform construct spec: `example_widget`

Status: BLOCKED
Category: resource
Provider revision: unavailable

## Summary

The provider snapshot required to investigate `example.widget` is unavailable.

## Sources

- Provider snapshot: unavailable at the task-supplied path.

## Target precedents

- Runtime: Review is pending until the provider behavior can be identified.
- Sibling: Review is pending until the provider category can be confirmed.

## Target mapping

- Target registration cannot be selected without the provider construct.

## Lifecycle and invocation

- Lifecycle behavior cannot be investigated without the provider snapshot.

## Edge cases

| ID | Disposition | Behavior | Evidence | Acceptance |
| --- | --- | --- | --- | --- |
| E001 | UNRESOLVED | Required provider source is unavailable. | Task snapshot path. | The snapshot becomes readable. |

## Schema and operations

- Unknown until the required input is available.

## Exclusions

- None established.

## Coverage

- Investigation resumes after the snapshot becomes readable.

## Open questions

- Question: Where is the readable revision-pinned provider snapshot?
- Blocker type: REQUIRED_INPUT
- Required authority: Coordinator supplying the investigation task.
- Target alternatives: Supply the snapshot or remove the construct from the queue.
- Recommended mapping: Supply the snapshot so source behavior can be investigated.
