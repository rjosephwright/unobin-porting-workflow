# Terraform construct audit: `example_widget`

Status: FAIL
Diff: aabbccdd
Round: 1

## Findings

| ID | Route | Severity | Problem | Evidence | Required change |
| --- | --- | --- | --- | --- | --- |
| A001 | PORT_GAP | high | Update ignores size changes. | `widget.go:70` | Send size when it changes. |

## Confirmed behavior

- Create and read satisfy the spec.

## Coverage

- The update test does not assert the request.

## Remaining delta

- Fix A001 and add an update request test.
