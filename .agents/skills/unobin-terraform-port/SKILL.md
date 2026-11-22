---
name: unobin-terraform-port
description: >-
  Port, audit, repair, or finish Terraform provider resources, data sources, and actions in an
  Unobin provider library. Use for one construct or an ordered queue from any Terraform provider.
  Reads provider and target settings from .codex/terraform-port.toml, gives each implementation
  an isolated Git worktree, permits independent services to progress concurrently, and requires an
  independent audit plus target-defined validation before commit.
---

# Unobin Terraform construct porting

Use the manifest and executable ledger instead of embedding provider, language, repository, or
validation assumptions in prompts. The controller derives the target repository, target name,
queue, artifact paths, worktree root, snapshot root, and cache root from the repository and provider
checkout.

Keep every repository, linked worktree, provider snapshot, and build/module cache off the system
temporary filesystem. The default durable runtime root is `_output/terraform-port-runtime` in the
target repository. The controller rejects a `runtime_root` or provider checkout under the system
temporary directory. Use the manifest's cache environment for dependencies and builds, and the
configured runtime cache directory for other bulky scratch output. Never substitute an ad hoc
`/tmp` path.

## Required agents

- `unobin-terraform-investigator`
- `unobin-terraform-porter`
- `unobin-terraform-auditor`

Use these exact role definitions in fresh sessions with no inherited conversation turns. The
coordinator alone updates the ledger and writes canonical artifacts. Agent responses are inputs to
those updates; they are not queue state by themselves.

Read these files before dispatching work:

- The target manifest (defaults to `.codex/terraform-port.toml`) and repository porting guidance,
  including `.agents/repository-porting-guidance.md` when present
- `references/transfer-model.md`
- `references/spec-contract.md`
- `references/evidence-contract.md`
- `references/audit-contract.md`
- `references/input-constraints.md`

## Native input contract

Follow [input-constraints.md](references/input-constraints.md) during investigation, implementation,
and audit. Declare supported rules once through native constraints in the construct entry file. Do not
substitute validate() callbacks or validation-driven equality for native enforcement. Verify
compiled literals, evaluated inputs, unchanged plans, and deferred/saved-plan apply. Resolve exact
engine enforcement bugs separately before declaring the affected checks complete. Domain-specific
parsers can remain in a single request-conversion path with existing preflight hooks; do not make
exact native equivalents of every provider validator a prerequisite for porting.
Always use `unobin fmt --wrap-strings` on target `.ub` files before completion.

## Initialize the run

Keep target settings in `.codex/terraform-port.toml` and machine-specific permissions in
`.codex/config.toml`. The `.agents` directory can be copied unchanged between target repositories.
Read `.agents/README.md` when configuring a new target or checking session isolation.

Before dispatch, check that the target has an initial Git commit, pinned runtime dependencies,
repository guidance, and the configured validation commands. Populate the dependency cache selected
by the manifest's environment before starting offline agents. Missing prerequisites are setup work,
not permission to skip checks.

Set the provider-source environment variable named by `provider_source_env` in the manifest. The
coordinator needs read access to that checkout:

```sh
export UNOBIN_TERRAFORM_PROVIDER_SOURCE=/durable/path/to/terraform-provider-example
```

The checkout must be on durable storage. Set `runtime_root` in the manifest when the repository's
default `_output/terraform-port-runtime` directory is not appropriate; it must also be durable.

The queue accepts one item per line:

```text
resource example-service.widget
data-source example-service.widget-info
action example-service.restart
```

An optional third field overrides the default lock derived from the part before the final dot:

```text
resource example-control.widget shared-control-plane
```

Initialize the ledger and create a revision-pinned, read-only provider snapshot:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml init
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml prepare-source
```

Never send a mutable provider checkout to an agent. Use the resolved snapshot recorded under
`source.snapshot` in the ledger. This gives every investigator and auditor the same provider
revision, even when the source checkout changes during a long queue.

## Dispatch from ledger state

Follow the session mode authorized by the user or target repository guidance. If that guidance
chooses the built-in roles and all three are available, use `collaboration.spawn_agent` with the
exact `agent_type` above and `fork_turns: "none"`. Pass the role task directly and use the returned
agent name as the owner. A fresh role inherits the coordinator's filesystem permissions. In this
mode, say so and instruct the porter to read only the specification, target, and target dependencies.
Pass the assigned worktree as the porter’s required working directory for edits and commands.
Apply the manifest's cache environment to role commands. Start with the configured built-in mode
without probing the standalone launcher or requesting approval again.

When filesystem isolation is required or the target has no authorized built-in mode, use
`scripts/run_agent.py` to start fresh sessions under the analysis or porter permission profile.
Prepare each task as a text file under the role's cache directory:

```sh
python3 .agents/skills/unobin-terraform-port/scripts/run_agent.py \
  --role porter --workdir "${worktree}" --task "${task_file}"
```

Use the target root as the working directory for investigation and audit. Use the assigned
worktree for implementation. Pass `--model` when the session must use the coordinator's explicitly
selected model; otherwise it uses the local Codex configuration. No role fixes a model or effort.

For standalone sessions, verify before implementation that the canonical spec and dependencies
are readable, the assigned worktree is writable, and provider checkouts, snapshots, source-bearing
caches, and analysis scratch deny reads. Test denial without printing file contents. Start the
standalone porter only after these checks succeed. In either mode, send behavior and references in
specifications and corrections. Keep provider source excerpts and access paths out of porter tasks.

Ask the controller for the next useful work whenever an agent returns or a stage changes:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml actions \
  --porter-slots 3 --audit-slots 2 --investigator-slots 2
```

The result is an ordered JSON list. Dispatch it in this priority order:

1. Correct failed audits.
2. Audit stable implementations.
3. Start implementations for available locks.
4. Investigate queued items.

The controller enforces `max_porters` and prevents two implementations with the same lock. A
blocked item does not prevent an unrelated implementation. Commits remain in queue order unless a
blocked item is explicitly marked `deferred` with a reason.

The coordinator launches each action in the selected session mode. Use the built-in agent name or
the standalone launcher's JSON session identifier with `start`, then submit the final artifact with
the matching `set-*` command. Keep concurrency within the manifest limit.

## Investigate

For an `investigate` action:

1. Record the assignment:

   ```sh
   .agents/skills/unobin-terraform-port/scripts/portctl.py \
     --manifest .codex/terraform-port.toml \
     start <key> investigator <agent-id>
   ```

2. Give the investigator the provider name, category, construct key, recorded snapshot path and
   revision, target root, a dedicated directory beneath `<cache_root>/analysis/`, the spec contract
   path, and explicit user decisions.
3. Save its complete response to
   `<artifact_root>/specs/<key>.md` without paraphrasing it.
4. Validate and record it:

   ```sh
   .agents/skills/unobin-terraform-port/scripts/validate-artifact spec <spec-path>
   .agents/skills/unobin-terraform-port/scripts/portctl.py \
     --manifest .codex/terraform-port.toml \
     set-spec <key> <READY-or-BLOCKED> <spec-path>
   ```

Do not implement a `BLOCKED` spec. Continue unrelated queue work. Use `defer <key> <reason>` only
when the item should no longer hold commit order; the ledger retains the reason.

The investigator must apply target precedents before returning `BLOCKED`. A runtime difference is
not a blocker type. The validator rejects specs that omit target precedents, use an unsupported
blocker type, or declare `BLOCKED` without an `UNRESOLVED` decision.

## Implement in isolated worktrees

For a `port` or `correct` action, create or reuse the construct worktree:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml create-worktree <key>
```

Record the assignment with `start <key> porter <agent-id> --worktree <path>`. Give the porter only:

- the construct identity, category, target root, and worktree;
- a dedicated directory beneath `<cache_root>/porter/`;
- the spec, optional overrides, and evidence contract paths;
- the implementation skills listed in the manifest;
- target repository instructions and configured focused checks; and
- the prior audit for a correction.

Omit provider excerpts and the provider snapshot path. In standalone mode the porter profile must
deny the snapshot and every other provider source copy. In either mode the porter must derive target
APIs, naming, and test conventions from the target repository and its dependencies.

For Go Unobin libraries, name construct entry files by category: `*_rsrc.go` for
resources, `*_dsrc.go` for data sources, and `*_action.go` for actions. Matching
tests use `*_rsrc_test.go`, `*_dsrc_test.go`, and `*_action_test.go`. Helper files
keep descriptive filenames. Include the exact entry filename in the spec's
target mapping and verify it during implementation and audit.

Save a complete porter response to `<artifact_root>/evidence/<key>.md`. Calculate the worktree diff
hash, validate the evidence against the current spec, and record it:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml diff-hash <worktree>
.agents/skills/unobin-terraform-port/scripts/validate-artifact \
  evidence <evidence-path> <spec-path>
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml \
  set-implementation <key> <diff-hash> <evidence-path>
```

If the diff changes later, the controller invalidates the old audit and validation results.

## Audit independently

For an `audit` action, record `start <key> auditor <agent-id>`. Give a new auditor the provider
snapshot, spec, evidence, worktree, current diff hash, audit round, and audit contract. The auditor
may read provider and target code but must not edit either.

Give the auditor a dedicated directory beneath `<cache_root>/analysis/`. Save its response to
`<artifact_root>/audits/<key>/round-<n>.md`, validate it, then record it:

```sh
.agents/skills/unobin-terraform-port/scripts/validate-artifact audit <audit-path>
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml \
  set-audit <key> <PASS-or-FAIL-or-BLOCKED> <audit-path> <diff-hash>
```

For `PORT_GAP` findings, start a fresh porter session with the current worktree, spec, and audit.
For `SPEC_GAP` findings, start a fresh investigator session with the current spec and audit to produce
a complete corrected spec, then dispatch a porter only when code or tests must change. Start a
fresh auditor session for each full round.

Stop for user direction after three failed rounds, when the same delta survives two rounds, or
when a decision changes public behavior or construct scope.

## Record validation once per diff

Before final validation, refresh the worktree onto the current target `HEAD`:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml refresh-worktree <key> --onto HEAD
```

This keeps concurrent implementations from being validated against an old target commit. When the
target base advances, refresh clears validation results from the previous base. If the construct
diff also changes, it clears the evidence and audit and requests a porter correction; dispatch the
porter and auditor again. If the diff is unchanged, the independent audit remains valid and only
target validation reruns. If neither base nor diff changed, recorded results remain valid.

The coordinator then runs every command in `required_checks` from the manifest. Store complete
output under `<artifact_root>/checks/<key>/<check>.log`, then record the result:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml \
  set-check <key> <check> <PASS-or-FAIL-or-BLOCKED-or-SKIP> \
  <diff-hash> '<exact-command>' <log-path>
```

Only `PASS` satisfies a required check. Reuse the record while the diff hash is unchanged. Do not
retry a known missing environment dependency in a loop. Never run a live-provider integration tier
without explicit user authorization.

Use the manifest's environment for dependency and build caches. Use subdirectories of the configured
runtime cache directory for other compiled tools and large scenario scratch data. Do not place
these under the system temporary directory.

## Commit completed constructs

An item becomes `validated` only when its current diff has a `PASS` audit and every required check
is `PASS`. Confirm that no earlier integration made the validated base stale:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml assert-fresh <key>
```

Commit the isolated branch, integrate that commit into the target branch in permitted queue order,
then record the target commit:

```sh
.agents/skills/unobin-terraform-port/scripts/portctl.py \
  --manifest .codex/terraform-port.toml commit <key> <target-commit>
```

Use the `git-commit` skill for commit operations. Preserve unrelated target changes and never add
ledger artifacts, provider snapshots, caches, or protected credentials to a commit. If the user
asked for an uncommitted result, stop after `validated` and report that explicitly.
