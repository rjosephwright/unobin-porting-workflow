# Terraform provider transfer model

The provider source at the exact revision recorded in the ledger defines the source behavior. The
target repository instructions and pinned runtime define how that behavior is represented in the
destination. Do not assume a cloud vendor, provider SDK, implementation language, or target folder
layout.

## Detect the provider implementation

Before tracing behavior, locate registration and identify the provider framework and version. A
provider may use Terraform Plugin SDK v2, Terraform Plugin Framework, another supported framework,
or a mix during migration. Read the registered construct and the functions it calls; do not infer
contracts from type names supplied in a prompt.

Framework code for diagnostics, Terraform state serialization, diff suppression, private state,
timeouts, and import syntax is relevant only when it changes observable remote behavior or a public
target value.

## Category boundaries

- A `resource` owns persistent remote state. Trace create, read, update, delete, import,
  replacement, not-found behavior, retries, and waits.
- A `data-source` reads remote information without mutating it. Trace lookup selection, no-result
  and multiple-result behavior, computed values, pagination, normalization, and errors.
- An `action` invokes an operation without Terraform resource state. Trace validation, request
  construction, progress, retries, waits, cancellation, errors, and any target result.

Do not turn a resource sub-operation into a target action merely because it uses a second API call.
Classify by the provider's public construct and the target runtime's category contract.

## Behavior that transfers

Record behavior that a user or remote API can observe:

- required, optional, computed, sensitive, immutable, and mutually constrained fields;
- provider-supplied defaults versus remote defaults after omission;
- request omission, explicit zero values, empty collections, clear and removal operations;
- create/read/update/delete or invocation call order;
- exact not-found handling, typed errors, transient retries, pagination, and wait completion;
- values read after create or wait, identifiers, normalization needed by consumers, and imports;
- update gates and replacement decisions; and
- tests needed to prove each decision in the target.

Separate provider behavior from framework bookkeeping. Terraform-only IDs, aggregate metadata,
state hashing, set ordering, diff suppression, and state upgrade code are normally excluded. If
one changes a request or a value visible to target consumers, record that observable consequence
instead of copying the framework mechanism.

## Target representation

The target repository and its pinned runtime define how transferred behavior is represented. Read
the relevant runtime contract and at least one current target sibling of the same category before
choosing a disposition. Prefer a sibling from the same service when one exists. If no useful sibling
exists, record the search and use the closest category precedent.

Use this decision order:

1. Follow an established target precedent that preserves the remote operation and public target
   values.
2. Use a construct-local mapping built from existing target lifecycle, planning, validation, and
   state contracts.
3. Exclude Terraform bookkeeping while specifying its observable consequence in target terms.
4. Ask for a user decision only when no established precedent resolves the issue and the remaining
   alternatives materially differ in public behavior, security, or destructive behavior.

A difference between Terraform's state engine and the target runtime is not by itself a blocker and
does not establish a requirement to change the target runtime. Rare races and refresh behavior use
the target's existing convention unless the provider source establishes a normal remote or public
contract that the convention cannot represent.

Before proposing a target-runtime change, document:

- the required remote or public behavior;
- the runtime and sibling precedents inspected;
- construct-local mappings considered;
- why each existing mapping is unsafe or materially incompatible; and
- the recommended alternative.

Do not prescribe a runtime change in a canonical spec. When the choice needs user authority, record
the alternatives and recommendation under `Open questions`.

## Evidence rules

Read complete behavior-affecting functions and only the helpers needed to understand their
contract. Prefer production source. Consult provider tests or local API models when production code
leaves one concrete decision ambiguous. Every spec decision needs an exact local path and line
reference plus an acceptance condition.

Use `UNRESOLVED` and `Status: BLOCKED` only when a required investigation input is unavailable,
required source is absent or contradictory, or the target-representation decision order ends in a
material user decision. Do not fill source gaps from memory or general cloud knowledge. Do not
classify a runtime difference as a missing input or source gap.
