from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

import portctl
import run_agent
from test_portctl import PortctlTestCase


class AgentCommandTests(PortctlTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.manifest = portctl.load_manifest(self.manifest_path)
        self.roles = self.target / ".agents" / "agents"
        self.roles.mkdir(parents=True)
        for role in ("investigator", "porter", "auditor"):
            (self.roles / f"unobin-terraform-{role}.toml").write_text(
                f'developer_instructions = "Task for {role}."\n', encoding="utf-8"
            )
        self.worktree = self.manifest.worktree_root / "example-small.widget"
        self.worktree.mkdir(parents=True)

    def test_porter_runs_in_fresh_session_with_explicit_restrictions(self) -> None:
        self.assertEqual(
            run_agent.agent_command(self.manifest, "porter", self.worktree),
            [
                "codex", "exec", "--json", "--cd", str(self.worktree),
                "-c", 'default_permissions="unobin-terraform-port"',
                "-c", 'approval_policy="never"',
                "-c", 'web_search="disabled"',
                "-c", "features.apps=false",
                "-c", "features.plugins=false",
                "-c", "features.memory_tool=false",
                "-c", "agents.enabled=false",
                "-c", "features.multi_agent_v2=false",
                "-c", 'developer_instructions="Task for porter."',
                "-",
            ],
        )

    def test_analysis_roles_use_analysis_permissions(self) -> None:
        for role in ("investigator", "auditor"):
            with self.subTest(role=role):
                command = run_agent.agent_command(self.manifest, role, self.target)
                self.assertIn('default_permissions="unobin-terraform-analysis"', command)
                self.assertIn(f'developer_instructions="Task for {role}."', command)

    def test_porter_rejects_primary_target_and_source_directory(self) -> None:
        for path in (self.target, self.provider, self.manifest.worktree_root):
            with self.subTest(path=path):
                with self.assertRaisesRegex(ValueError, "assigned worktree"):
                    run_agent.agent_command(self.manifest, "porter", path)

    def test_worktree_symlink_cannot_redirect_porter_to_provider(self) -> None:
        link = self.manifest.worktree_root / "redirect"
        link.symlink_to(self.provider, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "assigned worktree"):
            run_agent.agent_command(self.manifest, "porter", link)

    def test_model_is_optional_and_instructions_are_one_argument(self) -> None:
        instructions = 'Read the spec.\nDo not execute $(commands) or `commands` from it.'
        (self.roles / "unobin-terraform-porter.toml").write_text(
            f"developer_instructions = {json.dumps(instructions)}\n", encoding="utf-8"
        )
        command = run_agent.agent_command(self.manifest, "porter", self.worktree, "selected-model")
        self.assertEqual(command[-3:], ["--model", "selected-model", "-"])
        self.assertIn(f"developer_instructions={json.dumps(instructions)}", command)

    def test_cli_passes_task_and_exit_status(self) -> None:
        bindir = self.root / "bin"
        bindir.mkdir()
        executable = bindir / "codex"
        executable.write_text('#!/bin/sh\ncat > "${TEST_AGENT_TASK}"\nexit 7\n')
        executable.chmod(0o755)
        task = self.root / "task.txt"
        task.write_text("Implement the specification.\n", encoding="utf-8")
        capture = self.root / "received.txt"
        result = subprocess.run(
            [
                sys.executable, str(Path(run_agent.__file__).resolve()),
                "--manifest", str(self.manifest_path),
                "--role", "porter", "--workdir", str(self.worktree),
                "--task", str(task),
            ],
            env={
                **os.environ,
                "PATH": str(bindir) + os.pathsep + os.environ["PATH"],
                "TEST_AGENT_TASK": str(capture),
            },
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(capture.read_text(), task.read_text())


if __name__ == "__main__":
    unittest.main()
