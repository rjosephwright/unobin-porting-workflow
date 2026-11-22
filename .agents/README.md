# Portable Terraform construct porting

Copy `.agents/` unchanged into an Unobin provider library. It contains the investigator, porter,
and auditor roles; the transfer contracts; the queue controller; the session launcher; and tests.
Provider behavior comes from a pinned source snapshot. The implementer receives a specification
and target contracts, with no direct access to Terraform provider code.

## Target configuration

Keep the following files in the destination project's `.codex/` directory:

- `terraform-port.toml`: provider-source environment variable, revision, runtime directory,
  concurrency, implementation skills, session environment, and target validation commands.
- `config.toml`: relative agent registrations and named permission profiles for this host.

The controller defaults to `.codex/terraform-port.toml`; `--manifest` selects another file.
The target root is the manifest's grandparent directory. The queue is `next-constructs.txt` in that
root. Artifacts and runtime directories are derived from the target root. A different provider only
needs a different value for the environment variable named by `provider_source_env`.

Agent registrations use paths relative to `.codex/config.toml`, for example:

```toml
[agents."unobin-terraform-porter"]
description = "Implement one construct specification in an isolated target worktree."
config_file = "../.agents/agents/unobin-terraform-porter.toml"
```

No role selects a model or reasoning effort. Custom-role use inherits those settings. Fresh sessions
use the local Codex configuration; the launcher accepts `--model` for an explicitly selected model.

Before a queue run, the target needs a Git repository with an initial commit, pinned dependencies,
implementation guidance, working validation commands, and an accessible provider checkout. An
unavailable integration environment must not count as a passing check. Configure the validation
commands for each target before starting resource ports.

## Native input constraints

Investigator, porter, and auditor follow
[the native input contract](skills/unobin-terraform-port/references/input-constraints.md).
Input rules belong to native constraints in each construct entry file, without duplicate validation
callbacks. Specs identify rule coverage and SDK gaps; compiled fixtures and plan/apply tests prove
known, pending, unchanged and saved-plan enforcement. Use the target repository's porting guidance
for decisions specific to that library.

## Session modes

Follow the target's porting guidance. Targets that authorize built-in roles can launch the three
named roles through `collaboration.spawn_agent` with `fork_turns: "none"`. Use the returned agent
name as the controller owner. These roles inherit the coordinator's filesystem permissions.
Built-in mode uses fresh conversations, separate Git worktrees, the porter's instruction to use
only the spec and target, and independent audit. A repository can set its choice in
`.agents/repository-porting-guidance.md`.

### Standalone sessions with separate filesystem permissions

Use `skills/unobin-terraform-port/scripts/run_agent.py` when the workflow requires separate
permission profiles or the target has no authorized built-in mode. It starts a fresh `codex exec`
process with role instructions and an explicit permission selection:

- `unobin-terraform-analysis`: target and snapshot reads, analysis scratch writes.
- `unobin-terraform-port`: target and dependency reads, implementation worktree and cache writes,
  provider source reads denied.

The launcher disables approvals, web search, apps, plugins, memory, and further delegation. Role
instructions also prohibit browser and MCP tools. Inspect the effective environment before use;
do not configure a connected tool that exposes source outside the filesystem restrictions.
The launcher requires an assigned worktree for a porter and does not resume existing conversations.
It applies the manifest's optional `[environment]` table to each session, then applies
`[analysis_environment]` overrides for investigators and auditors. Both tables map environment
variable names to string values. Use them to keep target dependency and build caches separate from
provider analysis caches. Target validation commands must use the same cache paths as the porter.

Permission paths belong in `.codex/config.toml`. Set these for each destination host:

- Codex executables, skills, pinned runtime, and required dependency directories.
- The target repository and its implementation worktrees.
- The configured provider snapshot directory and every additional provider checkout or copy.
- Separate `analysis/` and `porter/` directories beneath the controller-derived `cache_root`.

Keep analysis scratch inaccessible to the porter. Do not place provider sources or investigator
transcripts in an implementation cache. Inspect shared dependency caches for provider copies;
prefer a task-owned cache containing only target dependencies. Apply source denials to alternate
copies too. Permission profiles must be updated if `runtime_root` or host paths change.

Verify the effective profile before starting a porter: target inputs must be readable, its
worktree writable, and provider sources unreadable. Probe access without printing source contents.
If the selected profile is absent or cannot be enforced, stop that dispatch. A prompt to avoid
source is not a filesystem restriction.

Restart sessions after changing active configuration. Validate the installed Codex configuration:

```sh
codex --strict-config doctor --summary --no-color --ascii
```

This diagnoses configuration; it does not prove a porter's filesystem isolation.

## Run one standalone role

Prepare a task file with the inputs required by the role's contract. For a porter, include only the
construct, specification, target and worktree paths, validation commands, and relevant audit
requirements. Keep provider excerpts and investigator conversation history out of that task.

```sh
python3 .agents/skills/unobin-terraform-port/scripts/run_agent.py \
  --role porter --workdir "${worktree}" --task "${task_file}"
```

Use the target root for an investigator or auditor. The command emits Codex JSON events, including
the session identifier for the controller's `start` command. The coordinator validates and saves
the returned artifact, then updates queue state. It alone integrates commits.

## Validate the portable package

Use Python 3.12 or newer and Git. The scripts use only the Python standard library.

```sh
cd .agents/skills/unobin-terraform-port/scripts
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_portctl test_run_agent
./test-validate-artifact.sh
```

The controller tests use real temporary Git repositories under the target's `_output/` directory.
Launcher tests check session arguments and worktree restrictions without starting model sessions.
They do not substitute for a permission check on the deployment host.
