# Native Unobin input constraints

Declare input validity once through native Unobin constraints. Do not copy source validators into
parallel `validate()` methods, `ResourceDefinition.Validate` callbacks, or validation predicates in
equality/replacement functions. The engine must enforce constraints when their inputs become known.
Conversion failures, saved identity and UID checks, API errors, and lifecycle preconditions remain
operation checks; they do not justify duplicate definitions of input validity.

## Investigation and mapping

Inventory required fields, mutual exclusions, conditional requirements, enums, numeric/list bounds,
and syntax checks. Distinguish structural schema checks from declared constraints and genuine
optional/computed inputs from missing required inputs. Apply explicit target decisions before
copying Terraform omission behavior. Do not preserve an omission workaround the target rejects.

Read the pinned SDK vocabulary, source extraction, compiler checking, and plan/apply enforcement.
Do not assume plan checks also run at apply. Inspect unchanged and deferred execution. For each
rule, state its native declaration, enforcement stage, and executable acceptance condition. If the
SDK cannot express a rule or enforce an execution path, identify that exact gap for the coordinator
to correct in its owning layer. Do not disguise it with a callback or claim the obligation complete.

## Declaration ownership

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
