#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Manifest:
    path: Path
    provider: str
    target: str
    target_root: Path
    queue_path: Path
    artifact_root: Path
    runtime_root: Path
    worktree_root: Path
    source_checkout: Path
    source_revision: str
    source_snapshot_root: Path
    cache_root: Path
    max_porters: int
    implementation_skills: tuple[str, ...]
    required_checks: tuple[str, ...]
    commands: dict[str, str]
    environment: dict[str, str]
    analysis_environment: dict[str, str]


def load_manifest(path: Path) -> Manifest:
    path = path.expanduser().resolve()
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    if data.get("version") != 2:
        raise ValueError("manifest version must be 2")

    target_root = path.parent.parent.resolve()
    target = target_root.name

    def text(name: str) -> str:
        value = data.get(name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"manifest field {name} must be a nonempty string")
        return value

    def resolved_value(value: str) -> Path:
        value = Path(value).expanduser()
        if not value.is_absolute():
            value = target_root / value
        return value.resolve()

    def reject_system_temp(label: str, value: Path) -> None:
        system_temp = Path(tempfile.gettempdir()).resolve()
        if value == system_temp or value.is_relative_to(system_temp):
            raise ValueError(f"{label} must not be under the system temporary directory")

    provider_source_env = text("provider_source_env")
    provider_source = os.environ.get(provider_source_env)
    if not provider_source:
        raise ValueError(
            f"provider source environment variable is not set: {provider_source_env}"
        )
    source_checkout = resolved_value(provider_source)
    reject_system_temp("provider source checkout", source_checkout)
    provider_prefix = "terraform-provider-"
    provider = source_checkout.name
    if provider.startswith(provider_prefix):
        provider = provider[len(provider_prefix) :]
    if not provider:
        raise ValueError(f"cannot derive provider name from: {source_checkout}")

    runtime_value = data.get("runtime_root", "_output/terraform-port-runtime")
    if not isinstance(runtime_value, str) or not runtime_value:
        raise ValueError("manifest field runtime_root must be a nonempty string")
    runtime_root = resolved_value(runtime_value)
    reject_system_temp("runtime root", runtime_root)
    provider_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", provider).strip("-.")
    target_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", target).strip("-.")

    max_porters = data.get("max_porters")
    if not isinstance(max_porters, int) or max_porters < 1:
        raise ValueError("manifest field max_porters must be a positive integer")

    def string_list(name: str) -> tuple[str, ...]:
        values = data.get(name)
        if not isinstance(values, list) or not values:
            raise ValueError(f"manifest field {name} must be a nonempty list")
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError(f"manifest {name} entries must be nonempty strings")
        if len(set(values)) != len(values):
            raise ValueError(f"manifest {name} entries must be unique")
        return tuple(values)

    implementation_skills = string_list("implementation_skills")
    required_checks = string_list("required_checks")
    commands = data.get("commands")
    if not isinstance(commands, dict):
        raise ValueError("manifest commands table is required")
    for check in required_checks:
        if not isinstance(commands.get(check), str) or not commands[check]:
            raise ValueError(f"manifest command {check} is required")

    def environment(name: str) -> dict[str, str]:
        values = data.get(name, {})
        if not isinstance(values, dict) or any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or not isinstance(value, str)
            for key, value in values.items()
        ):
            raise ValueError(f"manifest {name} must map environment variable names to strings")
        return values

    return Manifest(
        path=path,
        provider=provider,
        target=target,
        target_root=target_root,
        queue_path=target_root / "next-constructs.txt",
        artifact_root=target_root / "_output" / "terraform-port",
        runtime_root=runtime_root,
        worktree_root=runtime_root / "worktrees" / target_slug,
        source_checkout=source_checkout,
        source_revision=text("source_revision"),
        source_snapshot_root=runtime_root / "provider-sources" / provider_slug,
        cache_root=runtime_root / "cache" / target_slug,
        max_porters=max_porters,
        implementation_skills=implementation_skills,
        required_checks=required_checks,
        commands={str(name): str(command) for name, command in commands.items()},
        environment=environment("environment"),
        analysis_environment=environment("analysis_environment"),
    )


def parse_queue(path: Path) -> list[dict[str, str]]:
    categories = {"resource", "data-source", "action"}
    key_pattern = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) not in (2, 3):
            raise ValueError(f"invalid queue line {line_number}: expected 2 or 3 fields")
        category, key = parts[:2]
        if category not in categories:
            raise ValueError(f"unknown category on queue line {line_number}: {category}")
        if not key_pattern.fullmatch(key):
            raise ValueError(f"invalid construct key on queue line {line_number}: {key}")
        if key in seen:
            raise ValueError(f"duplicate construct key on queue line {line_number}: {key}")
        lock = parts[2] if len(parts) == 3 else key.rsplit(".", 1)[0]
        if not key_pattern.fullmatch(lock):
            raise ValueError(f"invalid lock on queue line {line_number}: {lock}")
        seen.add(key)
        items.append({"category": category, "key": key, "lock": lock})
    if not items:
        raise ValueError(f"queue is empty: {path}")
    return items


class PortQueue:
    def __init__(self, manifest: Manifest):
        self.manifest = manifest
        self.state_path = manifest.artifact_root / "queue.json"

    @classmethod
    def open(cls, manifest_path: Path) -> "PortQueue":
        return cls(load_manifest(manifest_path))

    def initialize(self) -> dict[str, Any]:
        queue_items = parse_queue(self.manifest.queue_path)
        if self.state_path.exists():
            state = self._read()
            wrong_provider = state["provider"] != self.manifest.provider
            wrong_target = state["target"] != self.manifest.target
            if wrong_provider or wrong_target:
                raise ValueError("queue state belongs to a different provider or target")
        else:
            state = {
                "version": 1,
                "provider": self.manifest.provider,
                "target": self.manifest.target,
                "manifest": str(self.manifest.path),
                "source": {
                    "checkout": str(self.manifest.source_checkout),
                    "requested_revision": self.manifest.source_revision,
                    "resolved_revision": None,
                    "snapshot": None,
                },
                "order": [],
                "items": {},
            }

        active_keys = {entry["key"] for entry in queue_items}
        for item in state["items"].values():
            item["active"] = False
            item.setdefault("audit_round", item["audit"]["round"] if item["audit"] else 0)
            item.setdefault("deferred_reason", None)
            item.setdefault("base_commit", None)
        for entry in queue_items:
            key = entry["key"]
            if key not in state["items"]:
                state["items"][key] = self._new_item(entry)
            else:
                state["items"][key]["category"] = entry["category"]
                state["items"][key]["lock"] = entry["lock"]
                state["items"][key]["active"] = True
        state["order"] = [entry["key"] for entry in queue_items]
        for key, item in state["items"].items():
            item["active"] = key in active_keys
        self._write(state)
        return state

    def set_spec(self, key: str, status: str, path: Path) -> None:
        if status not in {"READY", "BLOCKED"}:
            raise ValueError(f"invalid spec status: {status}")
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"spec is missing: {path}")
        state = self._read()
        item = self._item(state, key)
        spec_hash = hash_file(path)
        prior_spec = item["spec"]
        if prior_spec is not None and prior_spec["hash"] != spec_hash:
            item["evidence"] = None
            item["audit"] = None
            item["checks"] = {}
        item["spec"] = {
            "status": status,
            "path": str(path),
            "hash": spec_hash,
        }
        item["owner"] = None
        if status == "READY":
            item["stage"] = "ready"
            item["blocker"] = None
            item["deferred_reason"] = None
        else:
            item["stage"] = "blocked"
            item["blocker"] = "Specification is blocked"
        self._write(state)

    def start(self, key: str, role: str, owner: str, worktree: Path | None = None) -> None:
        if not owner:
            raise ValueError("owner must be nonempty")
        state = self._read()
        item = self._item(state, key)
        allowed = {
            "investigator": ({"queued", "blocked"}, "investigating"),
            "porter": ({"ready", "correction"}, None),
            "auditor": ({"implemented"}, "auditing"),
        }
        if role not in allowed:
            raise ValueError(f"invalid role: {role}")
        stages, next_stage = allowed[role]
        if item["stage"] not in stages:
            raise ValueError(f"cannot start {role} from stage {item['stage']}")
        if role == "porter":
            active_porters = sum(
                other["stage"] in {"porting", "correcting"}
                for other in state["items"].values()
                if other["active"]
            )
            if active_porters >= self.manifest.max_porters:
                raise ValueError("porter capacity is exhausted")
            lock_stages = {
                "porting",
                "implemented",
                "auditing",
                "correction",
                "correcting",
                "audited",
                "validated",
            }
            for other_key, other in state["items"].items():
                if other_key == key or not other["active"]:
                    continue
                if other["lock"] == item["lock"] and other["stage"] in lock_stages:
                    raise ValueError(
                        f"construct lock is held by {other_key}: {item['lock']}"
                    )
            next_stage = "correcting" if item["stage"] == "correction" else "porting"
        item["stage"] = next_stage
        item["owner"] = owner
        if worktree is not None:
            item["worktree"] = str(self._worktree_path(worktree))
        self._write(state)

    def set_implementation(self, key: str, diff_hash: str, evidence_path: Path) -> None:
        if not diff_hash:
            raise ValueError("diff hash must be nonempty")
        evidence_path = evidence_path.resolve()
        if not evidence_path.is_file():
            raise ValueError(f"evidence is missing: {evidence_path}")
        state = self._read()
        item = self._item(state, key)
        if item["spec"] is None or item["spec"]["status"] != "READY":
            raise ValueError("implementation requires a READY spec")
        if item["diff_hash"] != diff_hash:
            item["audit"] = None
            item["checks"] = {}
        item["diff_hash"] = diff_hash
        item["evidence"] = {
            "path": str(evidence_path),
            "hash": hash_file(evidence_path),
        }
        item["stage"] = "implemented"
        item["owner"] = None
        item["blocker"] = None
        self._reconcile(item)
        self._write(state)

    def set_audit(self, key: str, status: str, path: Path, diff_hash: str) -> None:
        if status not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError(f"invalid audit status: {status}")
        path = path.resolve()
        if not path.is_file():
            raise ValueError(f"audit is missing: {path}")
        state = self._read()
        item = self._item(state, key)
        self._require_diff(item, diff_hash)
        item["audit_round"] += 1
        item["audit"] = {
            "status": status,
            "path": str(path),
            "hash": hash_file(path),
            "diff_hash": diff_hash,
            "round": item["audit_round"],
        }
        item["owner"] = None
        if status == "PASS":
            item["stage"] = "audited"
            item["blocker"] = None
            self._reconcile(item)
        elif status == "FAIL":
            item["stage"] = "correction"
            item["blocker"] = None
        else:
            item["stage"] = "blocked"
            item["blocker"] = "Audit is blocked"
        self._write(state)

    def set_check(
        self,
        key: str,
        name: str,
        status: str,
        diff_hash: str,
        command: str,
        result_path: Path,
    ) -> None:
        if status not in {"PASS", "FAIL", "BLOCKED", "SKIP"}:
            raise ValueError(f"invalid check status: {status}")
        result_path = result_path.resolve()
        if not result_path.is_file():
            raise ValueError(f"check result is missing: {result_path}")
        state = self._read()
        item = self._item(state, key)
        self._require_diff(item, diff_hash)
        item["checks"][name] = {
            "status": status,
            "diff_hash": diff_hash,
            "command": command,
            "result": {
                "path": str(result_path),
                "hash": hash_file(result_path),
            },
        }
        self._reconcile(item)
        self._write(state)

    def block(self, key: str, reason: str) -> None:
        if not reason:
            raise ValueError("blocker reason must be nonempty")
        state = self._read()
        item = self._item(state, key)
        item["stage"] = "blocked"
        item["owner"] = None
        item["blocker"] = reason
        self._write(state)

    def defer(self, key: str, reason: str) -> None:
        if not reason:
            raise ValueError("defer reason must be nonempty")
        state = self._read()
        item = self._item(state, key)
        if item["stage"] != "blocked":
            raise ValueError(f"cannot defer from stage {item['stage']}")
        item["stage"] = "deferred"
        item["owner"] = None
        item["deferred_reason"] = reason
        self._write(state)

    def actions(
        self,
        porter_slots: int,
        audit_slots: int,
        investigator_slots: int,
    ) -> list[dict[str, str]]:
        state = self._read()
        porter_slots = min(max(porter_slots, 0), self.manifest.max_porters)
        audit_slots = max(audit_slots, 0)
        investigator_slots = max(investigator_slots, 0)
        porter_slots = max(
            porter_slots
            - sum(
                item["stage"] in {"porting", "correcting"}
                for item in state["items"].values()
                if item["active"]
            ),
            0,
        )
        audit_slots = max(
            audit_slots
            - sum(
                item["stage"] == "auditing"
                for item in state["items"].values()
                if item["active"]
            ),
            0,
        )
        investigator_slots = max(
            investigator_slots
            - sum(
                item["stage"] == "investigating"
                for item in state["items"].values()
                if item["active"]
            ),
            0,
        )
        actions: list[dict[str, str]] = []

        locked_stages = {
            "porting",
            "implemented",
            "auditing",
            "correction",
            "correcting",
            "audited",
            "validated",
        }
        locked = {
            item["lock"]
            for item in state["items"].values()
            if item["active"] and item["stage"] in locked_stages
        }

        correction_locks: set[str] = set()
        correction_count = 0
        if porter_slots:
            for key in state["order"]:
                item = state["items"][key]
                if item["stage"] != "correction" or item["lock"] in correction_locks:
                    continue
                actions.append(self._action("correct", key, item))
                correction_locks.add(item["lock"])
                correction_count += 1
                if correction_count == porter_slots:
                    break
        porter_slots -= correction_count

        audits = [
            key for key in state["order"] if state["items"][key]["stage"] == "implemented"
        ]
        for key in audits[:audit_slots]:
            actions.append(self._action("audit", key, state["items"][key]))

        selected_locks: set[str] = set()
        if porter_slots:
            for key in state["order"]:
                item = state["items"][key]
                if item["stage"] != "ready":
                    continue
                if item["lock"] in locked or item["lock"] in selected_locks:
                    continue
                actions.append(self._action("port", key, item))
                selected_locks.add(item["lock"])
                if len(selected_locks) == porter_slots:
                    break

        investigations = [
            key for key in state["order"] if state["items"][key]["stage"] == "queued"
        ]
        for key in investigations[:investigator_slots]:
            actions.append(self._action("investigate", key, state["items"][key]))
        return actions

    def commit(self, key: str, commit: str) -> None:
        if not commit:
            raise ValueError("commit must be nonempty")
        state = self._read()
        item = self._item(state, key)
        if item["stage"] != "validated":
            raise ValueError(f"cannot commit from stage {item['stage']}")
        position = state["order"].index(key)
        for prior_key in state["order"][:position]:
            prior = state["items"][prior_key]
            if prior["active"] and prior["stage"] not in {"committed", "deferred"}:
                raise ValueError(f"earlier queue item is not committed: {prior_key}")
        item["stage"] = "committed"
        item["commit"] = commit
        item["owner"] = None
        self._write(state)

    def state(self) -> dict[str, Any]:
        return self._read()

    def set_worktree(
        self,
        key: str,
        worktree: Path,
        branch: str,
        base_commit: str,
    ) -> None:
        state = self._read()
        item = self._item(state, key)
        item["worktree"] = str(self._worktree_path(worktree))
        item["branch"] = branch
        item["base_commit"] = base_commit
        self._write(state)

    def refresh_base(self, key: str, base_commit: str, refreshed_diff: str) -> None:
        state = self._read()
        item = self._item(state, key)
        base_changed = item["base_commit"] != base_commit
        diff_changed = item["diff_hash"] is not None and item["diff_hash"] != refreshed_diff
        if not base_changed and not diff_changed:
            return
        item["base_commit"] = base_commit
        item["owner"] = None
        item["checks"] = {}
        if diff_changed:
            item["diff_hash"] = refreshed_diff
            item["evidence"] = None
            item["audit"] = None
            item["stage"] = "correction"
        elif item["audit"] and item["audit"]["status"] == "PASS":
            item["stage"] = "audited"
        elif item["audit"] and item["audit"]["status"] == "FAIL":
            item["stage"] = "correction"
        elif item["evidence"]:
            item["stage"] = "implemented"
        self._write(state)

    def assert_fresh(self, key: str) -> None:
        state = self._read()
        item = self._item(state, key)
        if item["stage"] != "validated":
            raise ValueError(f"cannot integrate from stage {item['stage']}")
        current_base = run_git(
            self.manifest.target_root,
            "rev-parse",
            "HEAD",
        ).strip()
        if item["base_commit"] != current_base:
            raise ValueError("worktree base is stale; refresh it before integration")
        if not item["worktree"]:
            raise ValueError("construct has no worktree")
        current_diff = diff_hash(Path(item["worktree"]))
        if item["diff_hash"] != current_diff:
            raise ValueError("worktree diff changed after validation")

    def set_source_snapshot(self, snapshot: Path, revision: str) -> None:
        state = self._read()
        state["source"]["snapshot"] = str(snapshot.resolve())
        state["source"]["resolved_revision"] = revision
        self._write(state)

    def _new_item(self, entry: dict[str, str]) -> dict[str, Any]:
        return {
            "active": True,
            "category": entry["category"],
            "lock": entry["lock"],
            "stage": "queued",
            "spec": None,
            "worktree": None,
            "branch": None,
            "base_commit": None,
            "owner": None,
            "diff_hash": None,
            "evidence": None,
            "audit": None,
            "audit_round": 0,
            "checks": {},
            "blocker": None,
            "deferred_reason": None,
            "next_action": "investigate",
            "commit": None,
        }

    def _read(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            raise ValueError("queue is not initialized")
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _write(self, state: dict[str, Any]) -> None:
        for item in state["items"].values():
            item["next_action"] = self._next_action(item["stage"])
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_path.with_name(f".{self.state_path.name}.{os.getpid()}.tmp")
        temp_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp_path, self.state_path)

    def _item(self, state: dict[str, Any], key: str) -> dict[str, Any]:
        try:
            item = state["items"][key]
        except KeyError as error:
            raise ValueError(f"unknown construct: {key}") from error
        if not item["active"]:
            raise ValueError(f"construct is not active: {key}")
        return item

    def _require_diff(self, item: dict[str, Any], diff_hash: str) -> None:
        if not diff_hash or item["diff_hash"] != diff_hash:
            raise ValueError("result does not match the current diff")

    def _worktree_path(self, worktree: Path) -> Path:
        worktree = worktree.resolve()
        root = self.manifest.worktree_root.resolve()
        if not worktree.is_relative_to(root):
            raise ValueError(f"worktree is outside configured root: {worktree}")
        return worktree

    def _reconcile(self, item: dict[str, Any]) -> None:
        audit = item["audit"]
        if not audit or audit["status"] != "PASS" or audit["diff_hash"] != item["diff_hash"]:
            return
        checks_pass = all(
            name in item["checks"]
            and item["checks"][name]["status"] == "PASS"
            and item["checks"][name]["diff_hash"] == item["diff_hash"]
            for name in self.manifest.required_checks
        )
        item["stage"] = "validated" if checks_pass else "audited"

    def _action(self, name: str, key: str, item: dict[str, Any]) -> dict[str, str]:
        return {"action": name, "key": key, "category": item["category"]}

    def _next_action(self, stage: str) -> str:
        return {
            "queued": "investigate",
            "investigating": "wait",
            "ready": "port",
            "porting": "wait",
            "implemented": "audit",
            "auditing": "wait",
            "correction": "correct",
            "correcting": "wait",
            "audited": "validate",
            "validated": "commit",
            "blocked": "resolve",
            "deferred": "none",
            "committed": "none",
        }[stage]


def prepare_source(manifest: Manifest) -> tuple[Path, str]:
    revision = run_git(manifest.source_checkout, "rev-parse", manifest.source_revision).strip()
    snapshot = manifest.source_snapshot_root / revision
    if snapshot.is_dir():
        return snapshot, revision
    manifest.source_snapshot_root.mkdir(parents=True, exist_ok=True)
    archive_data = subprocess.run(
        [
            "git",
            "-C",
            str(manifest.source_checkout),
            "archive",
            "--format=tar",
            revision,
        ],
        check=True,
        capture_output=True,
    ).stdout
    temp = Path(tempfile.mkdtemp(prefix=f".{revision}.", dir=manifest.source_snapshot_root))
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_data), mode="r:") as archive:
            archive.extractall(temp, filter="data")
        (temp / ".terraform-port-revision").write_text(revision + "\n", encoding="utf-8")
        try:
            os.replace(temp, snapshot)
        except FileExistsError:
            shutil.rmtree(temp)
    except BaseException:
        if temp.exists():
            shutil.rmtree(temp)
        raise
    return snapshot, revision


def create_worktree(queue: PortQueue, key: str, base: str) -> Path:
    state = queue.state()
    item = queue._item(state, key)
    root = queue.manifest.worktree_root.resolve()
    if item["worktree"]:
        worktree = Path(item["worktree"]).resolve()
        if not worktree.is_relative_to(root):
            raise ValueError("recorded worktree is outside configured root")
        if worktree.is_dir():
            return worktree
        raise ValueError(f"recorded worktree is missing: {worktree}")

    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", key).strip("-.")
    worktree = (root / slug).resolve()
    if not worktree.is_relative_to(root):
        raise ValueError(f"worktree escapes configured root: {worktree}")
    if worktree.exists():
        raise ValueError(f"worktree path already exists: {worktree}")
    root.mkdir(parents=True, exist_ok=True)
    branch = f"terraform-port/{slug}"
    target_root = queue.manifest.target_root
    branch_exists = subprocess.run(
        ["git", "-C", str(target_root), "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
    ).returncode == 0
    command = ["git", "-C", str(target_root), "worktree", "add"]
    if not branch_exists:
        command.extend(["-b", branch])
    base_commit = run_git(target_root, "rev-parse", base).strip()
    command.extend([str(worktree), branch if branch_exists else base_commit])
    subprocess.run(command, check=True, capture_output=True, text=True)

    for relative in (Path(".agents"), Path(".codex")):
        source = target_root / relative
        if source.is_dir():
            shutil.copytree(source, worktree / relative, dirs_exist_ok=True)
    guidance = target_root / "AGENTS.md"
    if guidance.is_file():
        shutil.copy2(guidance, worktree / guidance.name)
    spec = item["spec"]
    if spec:
        source_spec = Path(spec["path"])
        try:
            relative_spec = source_spec.relative_to(target_root)
        except ValueError:
            relative_spec = Path("_output") / "terraform-port" / "specs" / source_spec.name
        destination_spec = worktree / relative_spec
        destination_spec.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_spec, destination_spec)
        override = source_spec.with_name(f"{source_spec.stem}.overrides{source_spec.suffix}")
        if override.is_file():
            shutil.copy2(override, destination_spec.with_name(override.name))
    worktree_base = run_git(worktree, "rev-parse", "HEAD").strip()
    queue.set_worktree(key, worktree, branch, worktree_base)
    return worktree


def refresh_worktree(queue: PortQueue, key: str, onto: str) -> tuple[str, str]:
    state = queue.state()
    item = queue._item(state, key)
    if not item["worktree"] or not item["base_commit"]:
        raise ValueError("construct has no recorded worktree base")
    worktree = Path(item["worktree"])
    if not worktree.is_dir():
        raise ValueError(f"recorded worktree is missing: {worktree}")
    worktree_head = run_git(worktree, "rev-parse", "HEAD").strip()
    if worktree_head != item["base_commit"]:
        raise ValueError("worktree contains commits; refresh requires uncommitted changes")
    target_base = run_git(queue.manifest.target_root, "rev-parse", onto).strip()
    if target_base != item["base_commit"]:
        subprocess.run(
            ["git", "-C", str(worktree), "rebase", "--autostash", target_base],
            check=True,
            capture_output=True,
            text=True,
        )
    refreshed_diff = diff_hash(worktree)
    queue.refresh_base(key, target_base, refreshed_diff)
    return target_base, refreshed_diff


def diff_hash(worktree: Path) -> str:
    worktree = worktree.resolve()
    digest = hashlib.sha256()
    digest.update(run_git_bytes(worktree, "diff", "--binary", "--no-ext-diff", "HEAD"))
    output = run_git_bytes(worktree, "ls-files", "--others", "--exclude-standard", "-z")
    excluded = {".agents", ".codex", "_output"}
    for raw_path in sorted(path for path in output.split(b"\0") if path):
        relative = Path(os.fsdecode(raw_path))
        if relative.parts and relative.parts[0] in excluded:
            continue
        if relative == Path("AGENTS.md"):
            continue
        path = worktree / relative
        digest.update(raw_path)
        digest.update(b"\0")
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(b"executable\0" if path.stat().st_mode & 0o111 else b"file\0")
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Control a Terraform construct port queue.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(".codex/terraform-port.toml"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    subparsers.add_parser("status")

    actions = subparsers.add_parser("actions")
    actions.add_argument("--porter-slots", type=int, required=True)
    actions.add_argument("--audit-slots", type=int, required=True)
    actions.add_argument("--investigator-slots", type=int, required=True)

    spec = subparsers.add_parser("set-spec")
    spec.add_argument("key")
    spec.add_argument("status", choices=("READY", "BLOCKED"))
    spec.add_argument("path", type=Path)

    start = subparsers.add_parser("start")
    start.add_argument("key")
    start.add_argument("role", choices=("investigator", "porter", "auditor"))
    start.add_argument("owner")
    start.add_argument("--worktree", type=Path)

    implementation = subparsers.add_parser("set-implementation")
    implementation.add_argument("key")
    implementation.add_argument("diff_hash")
    implementation.add_argument("evidence", type=Path)

    audit = subparsers.add_parser("set-audit")
    audit.add_argument("key")
    audit.add_argument("status", choices=("PASS", "FAIL", "BLOCKED"))
    audit.add_argument("path", type=Path)
    audit.add_argument("diff_hash")

    check = subparsers.add_parser("set-check")
    check.add_argument("key")
    check.add_argument("name")
    check.add_argument("status", choices=("PASS", "FAIL", "BLOCKED", "SKIP"))
    check.add_argument("diff_hash")
    check.add_argument("command_text")
    check.add_argument("result", type=Path)

    blocked = subparsers.add_parser("block")
    blocked.add_argument("key")
    blocked.add_argument("reason")

    deferred = subparsers.add_parser("defer")
    deferred.add_argument("key")
    deferred.add_argument("reason")

    committed = subparsers.add_parser("commit")
    committed.add_argument("key")
    committed.add_argument("commit_hash")

    subparsers.add_parser("prepare-source")
    worktree = subparsers.add_parser("create-worktree")
    worktree.add_argument("key")
    worktree.add_argument("--base", default="HEAD")

    refreshed = subparsers.add_parser("refresh-worktree")
    refreshed.add_argument("key")
    refreshed.add_argument("--onto", default="HEAD")

    fresh = subparsers.add_parser("assert-fresh")
    fresh.add_argument("key")

    hashed = subparsers.add_parser("diff-hash")
    hashed.add_argument("worktree", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        queue = PortQueue.open(args.manifest)
        if args.command == "init":
            print(json.dumps(queue.initialize(), indent=2, sort_keys=True))
        elif args.command == "status":
            state = queue.state()
            for key in state["order"]:
                item = state["items"][key]
                print(f"{item['stage']}\t{item['next_action']}\t{item['category']}\t{key}")
        elif args.command == "actions":
            print(
                json.dumps(
                    queue.actions(
                        args.porter_slots,
                        args.audit_slots,
                        args.investigator_slots,
                    ),
                    indent=2,
                )
            )
        elif args.command == "set-spec":
            queue.set_spec(args.key, args.status, args.path)
        elif args.command == "start":
            queue.start(args.key, args.role, args.owner, args.worktree)
        elif args.command == "set-implementation":
            queue.set_implementation(args.key, args.diff_hash, args.evidence)
        elif args.command == "set-audit":
            queue.set_audit(args.key, args.status, args.path, args.diff_hash)
        elif args.command == "set-check":
            queue.set_check(
                args.key,
                args.name,
                args.status,
                args.diff_hash,
                args.command_text,
                args.result,
            )
        elif args.command == "block":
            queue.block(args.key, args.reason)
        elif args.command == "defer":
            queue.defer(args.key, args.reason)
        elif args.command == "commit":
            queue.commit(args.key, args.commit_hash)
        elif args.command == "prepare-source":
            snapshot, revision = prepare_source(queue.manifest)
            queue.initialize()
            queue.set_source_snapshot(snapshot, revision)
            print(f"{revision}\t{snapshot}")
        elif args.command == "create-worktree":
            print(create_worktree(queue, args.key, args.base))
        elif args.command == "refresh-worktree":
            base, refreshed_diff = refresh_worktree(queue, args.key, args.onto)
            print(f"{base}\t{refreshed_diff}")
        elif args.command == "assert-fresh":
            queue.assert_fresh(args.key)
        elif args.command == "diff-hash":
            print(diff_hash(args.worktree))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"portctl: {error}", file=sys.stderr)
        return 1


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def run_git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    ).stdout


if __name__ == "__main__":
    raise SystemExit(main())
