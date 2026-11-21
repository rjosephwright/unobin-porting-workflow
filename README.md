# Unobin porting workflow

Reusable agents and tools for porting Terraform provider constructs into Unobin libraries. An
investigator derives a behavior specification from a pinned provider snapshot; a porter implements
that specification without provider source access; an independent auditor compares the result with
the provider and specification.

## Contents

```text
install                               Installer for a destination repository
.agents/
  README.md                           Runtime setup and permission isolation
  agents/                             Investigator, porter, and auditor roles
  skills/unobin-terraform-port/
    SKILL.md                          Coordinator workflow
    agents/                           Skill discovery metadata
    references/                       Specification, implementation, and audit contracts
    scripts/                          Queue controller, session launcher, and validators
    testdata/                         Validator fixtures
templates/
  config.toml.example                 Host permission and agent registration template
  terraform-port.toml.example         Target configuration example for a Go library
```

## Install in a provider library

Run the installer with the destination repository and the required host directories:

```sh
./install /absolute/path/to/unobin-library-example \
  --provider-source /absolute/path/to/terraform-provider-example \
  --unobin-root /absolute/path/to/unobin \
  --skills-root /absolute/path/to/skills
```

All required directories must already exist. Relative paths are resolved from the current working
directory. The installer copies `.agents/`, fills both templates, preserves executable permissions,
creates the target cache directories, and prints the provider-source export command to use before
running the workflow. It discovers Codex through `PATH`, resolves symlinks, and uses the npm package
root for npm installations or the executable's directory for native installations.

Optional arguments:

- `--codex-runtime PATH`: override the detected Codex runtime directory.
- `--runtime-root PATH`: runtime directory, relative to the destination repository unless absolute;
  defaults to `_output/terraform-port-runtime`.
- `--source-revision REVISION`: provider revision to snapshot; defaults to `HEAD`.
- `--overwrite`: replace differing installed workflow files and both `.codex` files. This replaces
  the complete TOML files, including any custom settings; it does not merge them.

Identical files can be installed again. If any installed file differs, the installer stops before
writing files unless `--overwrite` is set. Files outside the installed paths are preserved. For an
existing project with custom Codex settings, review and merge those settings with the templates
instead of replacing them. Use `./install --help` for the full argument list.

Keep `.agents/` unchanged across libraries; put target commands, implementation skill choices,
and host paths in `.codex/`. The installer expands these template markers and escapes values for
TOML; Codex itself does not expand them:

| Marker | Replacement |
| --- | --- |
| `@TARGET_ROOT@` | Absolute path to the destination provider library. |
| `@RUNTIME_ROOT@` | Absolute path corresponding to the manifest's `runtime_root`. |
| `@TARGET_SLUG@` | Destination directory name, with runs outside `A-Za-z0-9._-` changed to `-`, then leading and trailing `-` and `.` removed. |
| `@PROVIDER_CHECKOUT@` | Absolute path to the Terraform provider checkout. |
| `@CODEX_RUNTIME@` | Detected Codex runtime directory, or the explicit override. |
| `@SKILLS_ROOT@` | Absolute directory containing the implementation skills named by the manifest. |
| `@UNOBIN_ROOT@` | Absolute path to the Unobin runtime dependency. |
| `@SOURCE_REVISION@` | Provider revision selected with `--source-revision`. |
| `@GO_ENV@` | Shell-quoted Go cache assignments for validation commands. |

For example, a target named `unobin-library-example` uses that same target slug, and the default
runtime directory is `<target-root>/_output/terraform-port-runtime`. These values must agree between
the permission template and manifest. Keep provider sources separate from target dependencies.
Add read entries for any additional required tools or dependencies,
and porter denials for every alternate provider source copy, including copies inside dependencies.

The manifest template uses Go tools and Make targets. Adjust its skills and commands to the
destination, implement its required checks, and choose the provider revision. Set the named source
environment variable to the checkout path. The target needs an initial Git commit before worktrees
can be created. Add `/_output/` to the target's `.gitignore`.

Read [.agents/README.md](.agents/README.md) for session setup, source isolation, queue preparation,
and launching roles. The implementation skills named by the manifest must be installed on the host;
they are not bundled here. Use Python 3.12 or newer, Git, and Codex. The configuration targets
Codex 0.169.0; verify configuration and effective permissions on each destination host.

## Dependency and build caches

The target uses `_output/go` for `GOPATH`, `_output/go/pkg/mod` for `GOMODCACHE`, and
`_output/gocache` for `GOCACHE`. These paths are rooted in the destination repository and shared by
its implementation worktrees. The generated permission profiles, session environment, and validation
commands use those same paths. The installer creates empty cache directories; it does not download
dependencies.

Populate the module cache from the target repository before starting offline sessions:

```sh
GOPATH="${PWD}/_output/go" \
GOMODCACHE="${PWD}/_output/go/pkg/mod" \
GOCACHE="${PWD}/_output/gocache" \
go mod download
```

Investigators and auditors use private Go caches under the runtime's `cache/<target-slug>/analysis/`
directory. Prepare any dependencies they need there. Keep Terraform provider code out of the
target caches. The generated porter profile denies modules named `terraform-provider-*` in the
target module cache, including downloaded archives.

## Update an installed workflow

For a destination using generated configuration, rerun the installer from the chosen workflow
revision with the same arguments and `--overwrite`, then review the diff. For a destination with
custom `.codex` settings, copy `.agents/` separately and merge template changes into its configuration.
Review obsolete files that may need removal. Run validation and commit the updated workflow with
that library.

## Validate this package

From this repository's root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v \
  -s .agents/skills/unobin-terraform-port/scripts
PYTHONDONTWRITEBYTECODE=1 .agents/skills/unobin-terraform-port/scripts/test-validate-artifact.sh
```

Tests use temporary Git repositories under `_output/`, which is excluded from Git. They do not
launch model sessions. Verify actual source-access restrictions separately before starting a porter.
