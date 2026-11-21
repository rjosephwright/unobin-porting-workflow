#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

from portctl import Manifest, load_manifest


def agent_command(
    manifest: Manifest, role: str, workdir: Path, model: str | None = None
) -> list[str]:
    if role not in {"investigator", "porter", "auditor"}:
        raise ValueError(f"unknown role: {role}")
    workdir = workdir.resolve()
    worktree_root = manifest.worktree_root.resolve()
    if role == "porter" and (
        workdir == worktree_root or not workdir.is_relative_to(worktree_root)
    ):
        raise ValueError("porter must run inside its assigned worktree")
    if not workdir.is_dir():
        raise ValueError(f"working directory is missing: {workdir}")
    role_path = manifest.target_root / ".agents" / "agents" / f"unobin-terraform-{role}.toml"
    with role_path.open("rb") as stream:
        instructions = tomllib.load(stream).get("developer_instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"role instructions are empty: {role_path}")
    profile = "unobin-terraform-port" if role == "porter" else "unobin-terraform-analysis"
    command = [
        "codex", "exec", "--json", "--cd", str(workdir),
        "-c", f"default_permissions={json.dumps(profile)}",
        "-c", 'approval_policy="never"',
        "-c", 'web_search="disabled"',
        "-c", "features.apps=false",
        "-c", "features.plugins=false",
        "-c", "features.memory_tool=false",
        "-c", "agents.enabled=false",
        "-c", "features.multi_agent_v2=false",
        "-c", f"developer_instructions={json.dumps(instructions)}",
    ]
    if model is not None:
        command.extend(["--model", model])
    command.append("-")
    return command


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one porting role in a separate Codex session."
    )
    parser.add_argument("--manifest", type=Path, default=Path(".codex/terraform-port.toml"))
    parser.add_argument("--role", choices=("investigator", "porter", "auditor"), required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--model")
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        command = agent_command(manifest, args.role, args.workdir, args.model)
        task = args.task.read_text(encoding="utf-8")
        if not task.strip():
            raise ValueError("task must not be empty")
        environment = {**os.environ, **manifest.environment}
        if args.role != "porter":
            environment.update(manifest.analysis_environment)
        return subprocess.run(
            command, input=task, text=True, env=environment, check=False
        ).returncode
    except (OSError, ValueError) as error:
        print(f"run-agent: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
