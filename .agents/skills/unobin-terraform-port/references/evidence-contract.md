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
