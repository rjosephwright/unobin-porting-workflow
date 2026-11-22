# Native Unobin input constraints

Declare supported input rules once through native Unobin constraints. The engine must enforce them
when their inputs become known. Keep the declarations as the sole definition of those rules across
validation, equality, and replacement.
Conversion failures, persisted identity checks, API errors, and lifecycle preconditions belong in
the operation that needs them.

Use the target library's request-construction conventions for provider-specific parsing. Keep each
parser in one request preparation function. Existing lifecycle preflight hooks may call that function
so conversion errors fail before mutation or replacement deletion. Keep native predicates in their
declarations. Preserve the target's pinned SDK unless a version change is authorized. Report actual
engine enforcement bugs separately from domain parsing and repair them within the authorized scope.

## Investigation and mapping

Inventory required fields, mutual exclusions, conditional requirements, enums, numeric/list bounds,
and syntax checks. Distinguish structural schema checks from declared constraints and genuine
optional/computed inputs from missing required inputs. Apply explicit target decisions before
copying Terraform omission behavior. Do not preserve an omission workaround the target rejects.

Read the pinned SDK vocabulary, source extraction, compiler checking, and plan/apply enforcement.
Do not assume plan checks also run at apply. Inspect unchanged and deferred execution. For each
rule supported by the pinned SDK, state its native declaration, enforcement stage, and executable
acceptance condition. Map domain parsing to existing conversion paths before proposing any SDK
extension. If the engine fails to enforce a declared constraint on an execution path, identify that
exact bug for separate correction. Do not claim that enforcement passed when it did not.

## Declaration ownership

Follow the target's pinned constraint API. Where it provides `IsMatch` and `IsFormat`, use
`IsMatch` with a constant regex pattern and use the SDK's exported constants for `IsFormat`.
Examples in Go include `constraint.FormatRegex`, `constraint.FormatIP`, `constraint.FormatCIDR`,
`constraint.FormatBase64`, and `constraint.FormatPositiveDuration`. Preserve existing rule and
null semantics when changing declarations.

For Go, the registered input type's `Constraints()` method belongs in its construct entry file:
`*_rsrc.go`, `*_dsrc.go`, or `*_action.go`. Do not create separate `*_constraints.go` files. Verify
extraction through production library registration. Methods on nested helper types and ordinary
Go helper calls are not automatically extracted; use the pinned SDK's supported declaration syntax.
Preserve schema discovery when composing registrations.

Keep Go lines at or below 100 characters, including nested constraint declarations. Use readable
multiline call chains and inline ForEach bodies; do not generate dense single-line blocks. Do not
reflow calls already within the limit. Break long lines at commas, operators, or nested expression
boundaries with one continuation tab. Run
gofmt and inspect changed Go line lengths before returning an implementation. Formatting alone
does not wrap long Go calls. Auditors must flag added lines that exceed the target limit.

Keep shared SDK and lifecycle corrections separate from resource commits. Refresh dependent
worktrees onto the corrected dependency before final validation. Do not edit module-cache copies,
bypass missing checks, or add machine-specific dependency replacements to a release.

Keep SDK changes within the user-authorized scope. A constraint mapping gap does not itself
authorize expanding the SDK or making the entire construct queue depend on new SDK features.
Explain the exact proposed SDK behavior and compatibility impact when those changes need a user
decision, and continue independent queue work.

When correcting SDK behavior, update the affected public documentation and follow the SDK's release
note conventions in the same commit. Run the complete SDK test suite before committing, including
any generated expectations and compatibility checks. When the user directs amendment, amend the
affected commits, preserve unrelated work, and keep the history changes local.

## Executable proof

Use package-local `testdata/ub/` fixtures, never inline Unobin in Go tests or tests of instruction text.

Always run `unobin fmt --wrap-strings` on all target-owned `.ub` files, including fixtures and
integration factories/configurations. Use the installed or target-built Unobin formatter, rather
than manual formatting. Porters use `--write`; auditors use `--list` and require empty output.
Repository-wide formatting changes must be a separate commit from constraints or other behavior
changes. Format new/changed fixtures normally, but keep unrelated formatting sweeps out of feature
commits. Separate mixed fixture formatting from semantic edits before staging.
Inspect the result before tests and completion. Preserve deliberate
syntax-error fixtures when the formatter rejects them and report the exact exception.

Put tests in the target's existing suite by behavior. Reuse its compile-test package and fixture
layout for compiler checks; do not invent a separate constraints-test suite. Keep runtime/lifecycle
tests with their existing resource or integration tests. Reuse the target test helpers.

- Compile actual valid/invalid literals through public registration and check evaluated inputs.
- Identify the enforcing command; configuration-only `validate` may not evaluate resource arguments.
- Reject invalid desired inputs during native planning, including otherwise unchanged resources.
- Defer pending inputs without false errors; reject invalid resolved inputs before actions, data
  lookups, resource mutations, or replacement deletion.
- Exercise saved NoOp plan apply without a duplicate validation callback. Preserve valid unchanged
  and deferred execution, plus destruction of historical state whose old inputs fail new rules.
- Assert construct/rule constraint diagnostics. A callback error is not native enforcement proof.

Auditors check declaration placement, extraction, enforcement, and executable tests. Missing native
rules, duplicate validators, and bypasses are findings even when CRUD tests pass. Do not introduce
source-absent restrictions without an explicit target decision.
