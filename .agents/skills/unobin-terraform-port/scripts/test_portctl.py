#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import portctl


class PortctlTestCase(unittest.TestCase):
    def setUp(self) -> None:
        test_root = (
            Path(__file__).resolve().parents[4]
            / "_output"
            / "terraform-port-tests"
        )
        test_root.mkdir(parents=True, exist_ok=True)
        self.tempdir = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.tempdir.name)
        self.provider = self.root / "terraform-provider-example"
        self.target = self.root / "target"
        self.provider.mkdir()
        self.target.mkdir()
        self.provider_source_env = "TEST_TERRAFORM_PROVIDER_SOURCE"
        self.old_provider_source = os.environ.get(self.provider_source_env)
        os.environ[self.provider_source_env] = str(self.provider)
        self.queue_path = self.target / "next-constructs.txt"
        self.queue_path.write_text(
            "\n".join(
                (
                    "resource example-big.cluster",
                    "resource example-small.widget",
                    "data-source example-small.widget-info",
                    "action example-other.restart",
                )
            )
            + "\n",
            encoding="utf-8",
        )
        self.manifest_path = self.target / ".codex" / "terraform-port.toml"
        self.manifest_path.parent.mkdir()
        self.manifest_path.write_text(
            "\n".join(
                (
                    "version = 2",
                    f'provider_source_env = "{self.provider_source_env}"',
                    'source_revision = "HEAD"',
                    f'runtime_root = "{self.root / "runtime"}"',
                    "max_porters = 3",
                    'implementation_skills = ["programmer", "go-programmer"]',
                    'required_checks = ["full-test", "full-vet"]',
                    "",
                    "[commands]",
                    'full-test = "make test"',
                    'full-vet = "go vet ./..."',
                )
            )
            + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        if self.old_provider_source is None:
            os.environ.pop(self.provider_source_env, None)
        else:
            os.environ[self.provider_source_env] = self.old_provider_source
        self.tempdir.cleanup()

    def open_queue(self) -> portctl.PortQueue:
        queue = portctl.PortQueue.open(self.manifest_path)
        queue.initialize()
        return queue

    def write_spec(self, key: str) -> Path:
        path = self.target / "_output" / "terraform-port" / "specs" / f"{key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# Terraform construct spec: `{key}`\n", encoding="utf-8")
        return path

    def write_artifact(self, name: str, content: str = "result\n") -> Path:
        path = self.target / "_output" / "terraform-port" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path


class ManifestTests(PortctlTestCase):
    def test_cli_initializes_from_project_configuration(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(portctl.__file__).resolve()), "init"],
            cwd=self.target,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout)
        self.assertEqual(state["manifest"], str(self.manifest_path))
        self.assertEqual(state["provider"], "example")
        self.assertEqual(state["target"], "target")
        self.assertEqual(
            state["order"],
            [
                "example-big.cluster",
                "example-small.widget",
                "example-small.widget-info",
                "example-other.restart",
            ],
        )

    def test_load_manifest_resolves_paths_from_manifest_directory(self) -> None:
        manifest = portctl.load_manifest(self.manifest_path)

        self.assertEqual(manifest.provider, "example")
        self.assertEqual(manifest.target, "target")
        self.assertEqual(manifest.target_root, self.target)
        self.assertEqual(manifest.queue_path, self.queue_path)
        self.assertEqual(
            manifest.artifact_root,
            self.target / "_output" / "terraform-port",
        )
        self.assertEqual(manifest.runtime_root, self.root / "runtime")
        self.assertEqual(manifest.required_checks, ("full-test", "full-vet"))
        self.assertEqual(
            manifest.implementation_skills,
            ("programmer", "go-programmer"),
        )
        self.assertEqual(
            manifest.worktree_root,
            self.root / "runtime" / "worktrees" / "target",
        )
        self.assertEqual(
            manifest.source_snapshot_root,
            self.root / "runtime" / "provider-sources" / "example",
        )
        self.assertEqual(
            manifest.cache_root,
            self.root / "runtime" / "cache" / "target",
        )

    def test_load_manifest_defaults_runtime_to_target_output(self) -> None:
        runtime_line = f'runtime_root = "{self.root / "runtime"}"\n'
        manifest_text = self.manifest_path.read_text(encoding="utf-8")
        self.manifest_path.write_text(
            manifest_text.replace(runtime_line, ""),
            encoding="utf-8",
        )

        manifest = portctl.load_manifest(self.manifest_path)

        self.assertEqual(
            manifest.runtime_root,
            self.target / "_output" / "terraform-port-runtime",
        )

    def test_load_manifest_rejects_runtime_under_system_temp(self) -> None:
        manifest_text = self.manifest_path.read_text(encoding="utf-8")
        old_runtime = f'runtime_root = "{self.root / "runtime"}"'
        self.manifest_path.write_text(
            manifest_text.replace(
                old_runtime,
                f'runtime_root = "{Path(tempfile.gettempdir()) / "terraform-port"}"',
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "runtime root.*system temporary"):
            portctl.load_manifest(self.manifest_path)

    def test_load_manifest_rejects_provider_checkout_under_system_temp(self) -> None:
        provider = Path(tempfile.gettempdir()) / "terraform-provider-example"
        os.environ[self.provider_source_env] = str(provider)

        with self.assertRaisesRegex(ValueError, "provider source.*system temporary"):
            portctl.load_manifest(self.manifest_path)

    def test_load_manifest_requires_provider_source_environment(self) -> None:
        os.environ.pop(self.provider_source_env)

        with self.assertRaisesRegex(ValueError, self.provider_source_env):
            portctl.load_manifest(self.manifest_path)

    def test_parse_queue_supports_all_categories_and_service_locks(self) -> None:
        items = portctl.parse_queue(self.queue_path)

        self.assertEqual(
            items,
            [
                {
                    "category": "resource",
                    "key": "example-big.cluster",
                    "lock": "example-big",
                },
                {
                    "category": "resource",
                    "key": "example-small.widget",
                    "lock": "example-small",
                },
                {
                    "category": "data-source",
                    "key": "example-small.widget-info",
                    "lock": "example-small",
                },
                {
                    "category": "action",
                    "key": "example-other.restart",
                    "lock": "example-other",
                },
            ],
        )

    def test_parse_queue_accepts_an_explicit_lock(self) -> None:
        self.queue_path.write_text(
            "resource example-one.thing shared-service\n",
            encoding="utf-8",
        )

        items = portctl.parse_queue(self.queue_path)

        self.assertEqual(items[0]["lock"], "shared-service")

    def test_parse_queue_rejects_an_unknown_category(self) -> None:
        self.queue_path.write_text("function example.echo\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "unknown category"):
            portctl.parse_queue(self.queue_path)


class QueueTests(PortctlTestCase):
    def test_initialize_persists_queue_items(self) -> None:
        queue = self.open_queue()

        state = queue.state()

        self.assertEqual(state["provider"], "example")
        self.assertEqual(state["order"][0], "example-big.cluster")
        self.assertEqual(state["items"]["example-other.restart"]["category"], "action")
        state_path = self.target / "_output" / "terraform-port" / "queue.json"
        self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), state)

    def test_blocked_head_item_does_not_stop_independent_porters(self) -> None:
        queue = self.open_queue()
        for key in (
            "example-big.cluster",
            "example-small.widget",
            "example-small.widget-info",
            "example-other.restart",
        ):
            queue.set_spec(key, "READY", self.write_spec(key))
        queue.block("example-big.cluster", "Needs a user decision")

        actions = queue.actions(porter_slots=2, audit_slots=0, investigator_slots=0)

        self.assertEqual(
            actions,
            [
                {
                    "action": "port",
                    "key": "example-small.widget",
                    "category": "resource",
                },
                {
                    "action": "port",
                    "key": "example-other.restart",
                    "category": "action",
                },
            ],
        )

    def test_actions_prioritize_corrections_then_audits_then_new_ports(self) -> None:
        queue = self.open_queue()
        for key in (
            "example-big.cluster",
            "example-small.widget",
            "example-other.restart",
        ):
            queue.set_spec(key, "READY", self.write_spec(key))
        evidence = self.target / "evidence.md"
        evidence.write_text("evidence\n", encoding="utf-8")
        queue.set_implementation("example-big.cluster", "diff-a", evidence)
        queue.set_audit(
            "example-big.cluster",
            "FAIL",
            self.write_artifact("audits/audit-a.md"),
            "diff-a",
        )
        queue.set_implementation("example-small.widget", "diff-b", evidence)

        actions = queue.actions(porter_slots=2, audit_slots=1, investigator_slots=0)

        self.assertEqual(actions[0]["action"], "correct")
        self.assertEqual(actions[0]["key"], "example-big.cluster")
        self.assertEqual(actions[1]["action"], "audit")
        self.assertEqual(actions[1]["key"], "example-small.widget")
        self.assertEqual(actions[2]["action"], "port")
        self.assertEqual(actions[2]["key"], "example-other.restart")

    def test_new_implementation_invalidates_old_audit_and_checks(self) -> None:
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        evidence = self.target / "evidence.md"
        evidence.write_text("evidence\n", encoding="utf-8")
        queue.set_implementation(key, "diff-a", evidence)
        queue.set_audit(key, "PASS", self.write_artifact("audits/audit.md"), "diff-a")
        queue.set_check(
            key,
            "full-test",
            "PASS",
            "diff-a",
            "make test",
            self.write_artifact("checks/full-test.log"),
        )
        queue.set_check(
            key,
            "full-vet",
            "PASS",
            "diff-a",
            "go vet ./...",
            self.write_artifact("checks/full-vet.log"),
        )
        self.assertEqual(queue.state()["items"][key]["stage"], "validated")

        queue.set_implementation(key, "diff-b", evidence)

        item = queue.state()["items"][key]
        self.assertEqual(item["stage"], "implemented")
        self.assertIsNone(item["audit"])
        self.assertEqual(item["checks"], {})

    def test_commit_requires_validation_and_queue_order(self) -> None:
        queue = self.open_queue()
        evidence = self.target / "evidence.md"
        evidence.write_text("evidence\n", encoding="utf-8")
        for key, diff in (
            ("example-big.cluster", "diff-a"),
            ("example-small.widget", "diff-b"),
        ):
            queue.set_spec(key, "READY", self.write_spec(key))
            queue.set_implementation(key, diff, evidence)
            queue.set_audit(
                key,
                "PASS",
                self.write_artifact(f"audits/{key}.audit.md"),
                diff,
            )
            queue.set_check(
                key,
                "full-test",
                "PASS",
                diff,
                "make test",
                self.write_artifact(f"checks/{key}-test.log"),
            )
            queue.set_check(
                key,
                "full-vet",
                "PASS",
                diff,
                "go vet ./...",
                self.write_artifact(f"checks/{key}-vet.log"),
            )

        with self.assertRaisesRegex(ValueError, "earlier queue item"):
            queue.commit("example-small.widget", "commit-b")

        queue.commit("example-big.cluster", "commit-a")
        queue.commit("example-small.widget", "commit-b")

        self.assertEqual(
            queue.state()["items"]["example-small.widget"]["commit"],
            "commit-b",
        )

    def test_start_porter_enforces_construct_lock(self) -> None:
        queue = self.open_queue()
        first = "example-small.widget"
        second = "example-small.widget-info"
        queue.set_spec(first, "READY", self.write_spec(first))
        queue.set_spec(second, "READY", self.write_spec(second))
        evidence = self.write_artifact("evidence/first.md")
        queue.set_implementation(first, "diff-a", evidence)

        with self.assertRaisesRegex(ValueError, "lock is held"):
            queue.start(second, "porter", "porter-2")

    def test_start_porter_enforces_manifest_capacity(self) -> None:
        manifest_text = self.manifest_path.read_text(encoding="utf-8")
        self.manifest_path.write_text(
            manifest_text.replace("max_porters = 3", "max_porters = 1"),
            encoding="utf-8",
        )
        queue = self.open_queue()
        first = "example-big.cluster"
        second = "example-small.widget"
        queue.set_spec(first, "READY", self.write_spec(first))
        queue.set_spec(second, "READY", self.write_spec(second))
        queue.start(first, "porter", "porter-1")

        with self.assertRaisesRegex(ValueError, "porter capacity"):
            queue.start(second, "porter", "porter-2")

    def test_start_rejects_a_worktree_outside_the_runtime_root(self) -> None:
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))

        with self.assertRaisesRegex(ValueError, "outside configured root"):
            queue.start(key, "porter", "porter-1", self.root / "outside")

    def test_audit_and_check_records_include_artifact_hashes(self) -> None:
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        queue.set_implementation(key, "diff-a", self.write_artifact("evidence/item.md"))

        with self.assertRaisesRegex(ValueError, "audit is missing"):
            queue.set_audit(key, "PASS", self.target / "missing-audit.md", "diff-a")

        audit = self.write_artifact("audits/item.md", "audit result\n")
        queue.set_audit(key, "PASS", audit, "diff-a")
        result = self.write_artifact("checks/item-test.log", "tests passed\n")
        queue.set_check(key, "full-test", "PASS", "diff-a", "make test", result)

        item = queue.state()["items"][key]
        self.assertEqual(item["audit"]["hash"], portctl.hash_file(audit))
        self.assertEqual(item["checks"]["full-test"]["result"]["path"], str(result))
        self.assertEqual(
            item["checks"]["full-test"]["result"]["hash"],
            portctl.hash_file(result),
        )

    def test_explicitly_deferred_item_does_not_block_later_commit(self) -> None:
        queue = self.open_queue()
        first = "example-big.cluster"
        second = "example-small.widget"
        queue.set_spec(first, "BLOCKED", self.write_spec(first))
        queue.defer(first, "Waiting for a provider source decision")
        queue.set_spec(second, "READY", self.write_spec(second))
        queue.set_implementation(second, "diff-b", self.write_artifact("evidence/second.md"))
        queue.set_audit(
            second,
            "PASS",
            self.write_artifact("audits/second.md"),
            "diff-b",
        )
        queue.set_check(
            second,
            "full-test",
            "PASS",
            "diff-b",
            "make test",
            self.write_artifact("checks/second-test.log"),
        )
        queue.set_check(
            second,
            "full-vet",
            "PASS",
            "diff-b",
            "go vet ./...",
            self.write_artifact("checks/second-vet.log"),
        )

        queue.commit(second, "commit-b")

        state = queue.state()
        self.assertEqual(state["items"][first]["stage"], "deferred")
        self.assertEqual(state["items"][second]["stage"], "committed")

    def test_audit_round_survives_a_changed_implementation(self) -> None:
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        evidence = self.write_artifact("evidence/item.md")
        queue.set_implementation(key, "diff-a", evidence)
        queue.set_audit(
            key,
            "FAIL",
            self.write_artifact("audits/round-1.md"),
            "diff-a",
        )
        queue.set_implementation(key, "diff-b", evidence)
        queue.set_audit(
            key,
            "PASS",
            self.write_artifact("audits/round-2.md"),
            "diff-b",
        )

        self.assertEqual(queue.state()["items"][key]["audit"]["round"], 2)

    def test_changed_spec_invalidates_implementation_results(self) -> None:
        queue = self.open_queue()
        key = "example-big.cluster"
        spec = self.write_spec(key)
        queue.set_spec(key, "READY", spec)
        queue.set_implementation(key, "diff-a", self.write_artifact("evidence/item.md"))
        queue.set_audit(
            key,
            "PASS",
            self.write_artifact("audits/item.md"),
            "diff-a",
        )
        queue.set_check(
            key,
            "full-test",
            "PASS",
            "diff-a",
            "make test",
            self.write_artifact("checks/item-test.log"),
        )

        spec.write_text(spec.read_text(encoding="utf-8") + "revision\n", encoding="utf-8")
        queue.set_spec(key, "READY", spec)

        item = queue.state()["items"][key]
        self.assertIsNone(item["evidence"])
        self.assertIsNone(item["audit"])
        self.assertEqual(item["checks"], {})

    def test_actions_subtract_active_porters_from_capacity(self) -> None:
        queue = self.open_queue()
        for key in (
            "example-big.cluster",
            "example-small.widget",
            "example-other.restart",
        ):
            queue.set_spec(key, "READY", self.write_spec(key))
        queue.start("example-big.cluster", "porter", "porter-1")

        actions = queue.actions(porter_slots=2, audit_slots=0, investigator_slots=0)

        self.assertEqual(
            actions,
            [
                {
                    "action": "port",
                    "key": "example-small.widget",
                    "category": "resource",
                }
            ],
        )

    def test_actions_do_not_dispatch_corrections_without_porter_capacity(self) -> None:
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        queue.set_implementation(key, "diff-a", self.write_artifact("evidence/item.md"))
        queue.set_audit(
            key,
            "FAIL",
            self.write_artifact("audits/item.md"),
            "diff-a",
        )

        actions = queue.actions(porter_slots=0, audit_slots=0, investigator_slots=0)

        self.assertEqual(actions, [])


class GitTests(PortctlTestCase):
    def git(self, root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def initialize_git_repo(self, root: Path) -> None:
        self.git(root, "init", "-q")
        self.git(root, "config", "user.name", "Test User")
        self.git(root, "config", "user.email", "test@example.com")
        (root / "tracked.txt").write_text("base\n", encoding="utf-8")
        self.git(root, "add", "tracked.txt")
        self.git(root, "commit", "-qm", "Initial commit")

    def test_prepare_source_snapshots_one_exact_revision(self) -> None:
        self.initialize_git_repo(self.provider)
        (self.provider / "untracked.txt").write_text("ignored\n", encoding="utf-8")
        manifest = portctl.load_manifest(self.manifest_path)

        snapshot, revision = portctl.prepare_source(manifest)

        self.assertEqual(revision, self.git(self.provider, "rev-parse", "HEAD"))
        self.assertEqual((snapshot / "tracked.txt").read_text(encoding="utf-8"), "base\n")
        self.assertFalse((snapshot / "untracked.txt").exists())

    def test_diff_hash_includes_tracked_and_untracked_changes(self) -> None:
        self.initialize_git_repo(self.target)
        clean_hash = portctl.diff_hash(self.target)
        (self.target / "tracked.txt").write_text("changed\n", encoding="utf-8")
        tracked_hash = portctl.diff_hash(self.target)
        (self.target / "new.txt").write_text("new\n", encoding="utf-8")
        untracked_hash = portctl.diff_hash(self.target)

        self.assertNotEqual(clean_hash, tracked_hash)
        self.assertNotEqual(tracked_hash, untracked_hash)

    def test_diff_hash_is_unchanged_when_the_same_content_is_staged(self) -> None:
        self.initialize_git_repo(self.target)
        (self.target / "tracked.txt").write_text("changed\n", encoding="utf-8")
        unstaged_hash = portctl.diff_hash(self.target)

        self.git(self.target, "add", "tracked.txt")

        self.assertEqual(portctl.diff_hash(self.target), unstaged_hash)

    def test_diff_hash_includes_an_untracked_executable_bit(self) -> None:
        self.initialize_git_repo(self.target)
        script = self.target / "new-script"
        script.write_text("#!/bin/sh\n", encoding="utf-8")
        os.chmod(script, 0o644)
        plain_hash = portctl.diff_hash(self.target)

        os.chmod(script, 0o755)

        self.assertNotEqual(portctl.diff_hash(self.target), plain_hash)

    def test_create_worktree_copies_agent_assets_but_not_credentials(self) -> None:
        self.initialize_git_repo(self.target)
        agents_file = self.target / ".agents" / "instructions.txt"
        agents_file.parent.mkdir(exist_ok=True)
        agents_file.write_text("instructions\n", encoding="utf-8")
        (self.target / "AGENTS.md").write_text("guidance\n", encoding="utf-8")
        (self.target / ".env").write_text("SECRET=value\n", encoding="utf-8")
        secrets = self.target / "secrets"
        secrets.mkdir()
        (secrets / "token").write_text("secret\n", encoding="utf-8")
        queue = self.open_queue()

        worktree = portctl.create_worktree(queue, "example-big.cluster", "HEAD")

        self.assertTrue((worktree / ".agents" / "instructions.txt").is_file())
        self.assertTrue((worktree / "AGENTS.md").is_file())
        self.assertFalse((worktree / ".env").exists())
        self.assertFalse((worktree / "secrets").exists())

    def test_default_runtime_creates_worktree_under_target_output(self) -> None:
        runtime_line = f'runtime_root = "{self.root / "runtime"}"\n'
        manifest_text = self.manifest_path.read_text(encoding="utf-8")
        self.manifest_path.write_text(
            manifest_text.replace(runtime_line, ""),
            encoding="utf-8",
        )
        self.initialize_git_repo(self.target)
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))

        worktree = portctl.create_worktree(queue, key, "HEAD")

        self.assertEqual(
            worktree,
            self.target
            / "_output"
            / "terraform-port-runtime"
            / "worktrees"
            / "target"
            / key,
        )
        self.assertTrue(worktree.is_dir())

    def test_refresh_worktree_preserves_diff_and_invalidates_old_checks(self) -> None:
        self.initialize_git_repo(self.target)
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        worktree = portctl.create_worktree(queue, key, "HEAD")
        (worktree / "tracked.txt").write_text("construct change\n", encoding="utf-8")
        current_diff = portctl.diff_hash(worktree)
        queue.set_implementation(key, current_diff, self.write_artifact("evidence/item.md"))
        queue.set_audit(
            key,
            "PASS",
            self.write_artifact("audits/item.md"),
            current_diff,
        )
        queue.set_check(
            key,
            "full-test",
            "PASS",
            current_diff,
            "make test",
            self.write_artifact("checks/item-test.log"),
        )
        queue.set_check(
            key,
            "full-vet",
            "PASS",
            current_diff,
            "go vet ./...",
            self.write_artifact("checks/item-vet.log"),
        )
        (self.target / "unrelated.txt").write_text("new base\n", encoding="utf-8")
        self.git(self.target, "add", "unrelated.txt")
        self.git(self.target, "commit", "-qm", "Advance target")
        new_base = self.git(self.target, "rev-parse", "HEAD")

        base, refreshed_diff = portctl.refresh_worktree(queue, key, "HEAD")

        item = queue.state()["items"][key]
        self.assertEqual(base, new_base)
        self.assertEqual(refreshed_diff, current_diff)
        self.assertEqual(item["base_commit"], new_base)
        self.assertEqual(item["checks"], {})
        self.assertEqual(item["stage"], "audited")
        self.assertEqual(
            (worktree / "tracked.txt").read_text(encoding="utf-8"),
            "construct change\n",
        )

    def test_refresh_worktree_reuses_checks_when_base_and_diff_are_current(self) -> None:
        self.initialize_git_repo(self.target)
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        worktree = portctl.create_worktree(queue, key, "HEAD")
        (worktree / "tracked.txt").write_text("construct change\n", encoding="utf-8")
        diff = portctl.diff_hash(worktree)
        queue.set_implementation(key, diff, self.write_artifact("evidence/item.md"))
        queue.set_audit(key, "PASS", self.write_artifact("audits/item.md"), diff)
        for name in ("full-test", "full-vet"):
            queue.set_check(
                key,
                name,
                "PASS",
                diff,
                name,
                self.write_artifact(f"checks/{name}.log"),
            )

        portctl.refresh_worktree(queue, key, "HEAD")

        item = queue.state()["items"][key]
        self.assertEqual(item["stage"], "validated")
        self.assertEqual(set(item["checks"]), {"full-test", "full-vet"})

    def test_assert_fresh_rejects_an_old_worktree_base(self) -> None:
        self.initialize_git_repo(self.target)
        queue = self.open_queue()
        key = "example-big.cluster"
        queue.set_spec(key, "READY", self.write_spec(key))
        worktree = portctl.create_worktree(queue, key, "HEAD")
        (worktree / "tracked.txt").write_text("construct change\n", encoding="utf-8")
        diff = portctl.diff_hash(worktree)
        queue.set_implementation(key, diff, self.write_artifact("evidence/item.md"))
        queue.set_audit(key, "PASS", self.write_artifact("audits/item.md"), diff)
        for name in ("full-test", "full-vet"):
            queue.set_check(
                key,
                name,
                "PASS",
                diff,
                name,
                self.write_artifact(f"checks/{name}.log"),
            )
        (self.target / "unrelated.txt").write_text("new base\n", encoding="utf-8")
        self.git(self.target, "add", "unrelated.txt")
        self.git(self.target, "commit", "-qm", "Advance target")

        with self.assertRaisesRegex(ValueError, "worktree base is stale"):
            queue.assert_fresh(key)


if __name__ == "__main__":
    unittest.main()
