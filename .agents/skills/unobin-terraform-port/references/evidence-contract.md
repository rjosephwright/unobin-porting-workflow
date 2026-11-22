# Porter evidence contract

For a completed implementation, return one complete Markdown artifact:

```markdown
# Terraform construct evidence: `<key>`

Status: COMPLETE
Diff: <sha256-from-portctl>
Spec: <spec-path>

## Obligations

| ID | Implementation | Tests |
| --- | --- | --- |
| E001 | `target/file:line` | `target/file_test:line` |

## Checks

- `<exact focused command>`: PASS | FAIL | BLOCKED
```

Include every `IMPLEMENT` and `VERIFY` ID from the current spec. Both implementation and executable
test evidence are required. For an obligation fulfilled entirely by an existing target helper,
name that helper and its existing or newly added behavior test.

Identify the construct entry file using the category convention in `../SKILL.md`.

If work cannot complete, return `SPEC_GAP` or `BLOCKED` followed by the exact missing decision,
source, tool, or dependency. Do not invent a COMPLETE artifact.

## Native input contract

Follow `input-constraints.md`. Identify native declarations and tests proving public registration
and enforcement for literal, evaluated, unchanged, and resolved deferred or saved-plan inputs.
Identify any domain parser used in request preparation and the test that proves conversion fails
before side effects. Distinguish enforcement from configuration-only validation. Define native
predicates once. Report exact SDK enforcement gaps and any required behavior that remains unproven.
Return COMPLETE only when all required behavior is proven.
