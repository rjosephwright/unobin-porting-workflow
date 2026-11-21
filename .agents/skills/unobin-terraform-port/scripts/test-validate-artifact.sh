#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
validator="${script_dir}/validate-artifact"
testdata="${script_dir}/../testdata"

expect_success() {
    if ! "${validator}" "$@"; then
        echo "expected success: $*" >&2
        exit 1
    fi
}

expect_failure() {
    if "${validator}" "$@" >/dev/null 2>&1; then
        echo "expected failure: $*" >&2
        exit 1
    fi
}

expect_success spec "${testdata}/valid-resource-spec.md"
expect_success spec "${testdata}/valid-action-spec.md"
expect_success spec "${testdata}/valid-blocked-spec.md"
expect_success spec "${testdata}/valid-user-decision-blocked-spec.md"
expect_success spec "${testdata}/valid-required-input-blocked-spec.md"
expect_failure spec "${testdata}/invalid-category-spec.md"
expect_failure spec "${testdata}/invalid-ready-unresolved-spec.md"
expect_failure spec "${testdata}/invalid-missing-target-precedents-spec.md"
expect_failure spec "${testdata}/invalid-runtime-gap-blocked-spec.md"
expect_failure spec "${testdata}/invalid-blocked-without-unresolved-spec.md"
expect_success audit "${testdata}/valid-pass-audit.md"
expect_success audit "${testdata}/valid-fail-audit.md"
expect_failure audit "${testdata}/invalid-pass-delta-audit.md"
expect_failure audit "${testdata}/invalid-pass-findings-audit.md"
expect_success evidence "${testdata}/valid-evidence.md" "${testdata}/valid-resource-spec.md"
expect_failure evidence "${testdata}/invalid-evidence.md" "${testdata}/valid-resource-spec.md"
expect_failure evidence "${testdata}/invalid-headerless-evidence.md" \
  "${testdata}/valid-resource-spec.md"
expect_failure unknown "${testdata}/valid-resource-spec.md"
expect_failure spec "${testdata}/missing.md"
