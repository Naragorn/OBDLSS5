#!/usr/bin/env python3
"""Offline-first OBDLSS5 inventory, staging, verification and test harness.

The tool deliberately does not download or execute third-party runtime files.
It validates a user-supplied, locked candidate and fails closed when a live
requirement is not evidenced.  The Windows game harness is intentionally
separate from the offline validators so an offline result cannot be mistaken
for a Flat PoC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_ROOT = REPO_ROOT / "obdlss5" / "profiles"
DEFAULT_PROFILE = "flat-d3d11"
DEFAULT_LOCK = REPO_ROOT / "obdlss5" / "dependencies.lock.json"
STATE_ORDER = (
    "NOT_RUN",
    "INVENTORIED",
    "WRAPPER_OK",
    "GUIDES_OK",
    "TRANSPORT_OK",
    "DLAA_OK",
    "NR_ACTIVE",
    "POC_VERIFIED",
)
TERMINAL_STATES = {
    "BLOCKED_ENVIRONMENT",
    "BLOCKED_DEPENDENCY",
    "BLOCKED_RUNTIME",
    "FAILED",
    "UNKNOWN",
}
PE_MACHINES = {0x014C: "I386", 0x8664: "AMD64", 0xAA64: "ARM64"}
PE_MAGIC = {0x10B: "PE32", 0x20B: "PE32+"}
PROXY_NAMES = {"d3d9.dll", "dxgi.dll", "d3d11.dll", "winmm.dll"}
FORBIDDEN_COLLECT_PARTS = {
    "saves",
    "save",
    "credentials",
    "credential",
    "secrets",
    "password",
    "tokens",
}


class CliError(RuntimeError):
    """A user-correctable validation or command error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_run_id(prefix: str = "run") -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:10]}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, value: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"Required JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid JSON in {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise CliError(f"Path escapes the installation root: {value}")
    return path


def parse_assignment(value: str, label: str) -> tuple[str, Path]:
    if "=" not in value:
        raise CliError(f"{label} must use NAME=PATH: {value}")
    name, raw_path = value.split("=", 1)
    if not name or not raw_path:
        raise CliError(f"{label} must use a non-empty NAME=PATH: {value}")
    return name, Path(raw_path).expanduser().resolve()


def parse_pe(path: Path) -> dict[str, Any]:
    """Read only the PE headers required for architecture validation."""

    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "valid": False,
        "machine": None,
        "machine_name": None,
        "optional_magic": None,
        "format": None,
        "error": None,
    }
    if not path.is_file():
        result["error"] = "missing"
        return result
    try:
        with path.open("rb") as stream:
            dos = stream.read(64)
            if len(dos) < 64 or dos[:2] != b"MZ":
                result["error"] = "missing MZ signature"
                return result
            pe_offset = struct.unpack_from("<I", dos, 0x3C)[0]
            stream.seek(pe_offset)
            header = stream.read(26)
    except OSError as exc:
        result["error"] = str(exc)
        return result
    if len(header) < 26 or header[:4] != b"PE\0\0":
        result["error"] = "missing PE signature"
        return result
    machine = struct.unpack_from("<H", header, 4)[0]
    optional_magic = struct.unpack_from("<H", header, 24)[0]
    result.update(
        {
            "valid": True,
            "machine": f"0x{machine:04X}",
            "machine_name": PE_MACHINES.get(machine, "UNKNOWN"),
            "optional_magic": f"0x{optional_magic:03X}",
            "format": PE_MAGIC.get(optional_magic, "UNKNOWN"),
        }
    )
    return result


def architecture_for(path: Path) -> str | None:
    parsed = parse_pe(path)
    if not parsed["valid"]:
        return None
    return parsed["machine_name"]


def is_remastered_executable(path: Path) -> bool:
    name = path.name.lower().replace("_", "").replace("-", "")
    return "oblivionremastered" in name


def inspect_executable(path: Path) -> dict[str, Any]:
    pe = parse_pe(path)
    if is_remastered_executable(path):
        status = "FAILED"
        reason = "Remastered executable is outside the classic Oblivion scope"
    elif not pe["valid"]:
        status = "UNKNOWN"
        reason = pe["error"] or "Executable signature could not be validated"
    elif pe["machine_name"] == "AMD64":
        status = "FAILED"
        reason = "PE32+ executable is not a classic x86 Oblivion executable"
    elif pe["machine_name"] != "I386":
        status = "FAILED"
        reason = "Executable is not PE32/I386"
    else:
        status = "INVENTORIED"
        reason = "PE32/I386 signature validated; classic game identity remains user-selected"
    return {
        "path": str(path),
        "file_name": path.name,
        "sha256": sha256_file(path) if path.is_file() else None,
        "pe": pe,
        "status": status,
        "reason": reason,
        "identity": "classic-oblivion-user-selected" if status == "INVENTORIED" else "unverified",
    }


def host_identity() -> dict[str, Any]:
    uname = platform.uname()
    return {
        "os": platform.platform(),
        "system": uname.system,
        "release": uname.release,
        "version": uname.version,
        "machine": uname.machine,
        "processor": uname.processor,
        "gpu": None,
        "driver": None,
        "gpu_evidence": "NOT_AVAILABLE_FROM_STANDARD_LIBRARY",
    }


def load_lock(path: Path) -> dict[str, Any]:
    lock = read_json(path)
    if not isinstance(lock, dict) or lock.get("schema_version") != 1:
        raise CliError(f"Unsupported dependency lock schema in {path}; expected schema_version 1")
    components = lock.get("components")
    if not isinstance(components, list):
        raise CliError(f"Dependency lock must contain a components list: {path}")
    names: set[str] = set()
    for component in components:
        if not isinstance(component, dict) or not component.get("name"):
            raise CliError(f"Each dependency lock component needs a name: {path}")
        name = str(component["name"])
        if name in names:
            raise CliError(f"Duplicate dependency lock component: {name}")
        names.add(name)
    return lock


def lock_components(lock: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in lock["components"]}


def resolve_profile(profile: str | Path) -> tuple[Path, dict[str, Any]]:
    candidate = Path(profile)
    if not candidate.exists():
        direct = PROFILE_ROOT / str(profile) / "profile.json"
        if direct.is_file():
            candidate = direct
        else:
            matches = []
            for path in PROFILE_ROOT.glob("*/profile.json"):
                try:
                    value = read_json(path)
                except CliError:
                    continue
                if isinstance(value, dict) and value.get("id") == str(profile):
                    matches.append((path, value))
            if len(matches) == 1:
                return matches[0]
            candidate = direct
    if candidate.is_dir():
        candidate = candidate / "profile.json"
    data = read_json(candidate)
    if not isinstance(data, dict) or not data.get("id"):
        raise CliError(f"Invalid OBDLSS5 profile: {candidate}")
    return candidate, data


def validate_profile(profile: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get("scope") != "classic-oblivion-flat-only":
        errors.append("profile scope is not classic-oblivion-flat-only")
    if profile.get("view_count") != 1:
        errors.append("profile must implement exactly one view")
    files = profile.get("files")
    if not isinstance(files, list) or not files:
        errors.append("profile files must be a non-empty list")
    else:
        destinations: set[str] = set()
        roles: set[str] = set()
        for item in files:
            if not isinstance(item, dict):
                errors.append("each profile file entry must be an object")
                continue
            role = str(item.get("role", ""))
            destination = str(item.get("destination", ""))
            if not role or not destination:
                errors.append("profile file entries need role and destination")
                continue
            if role in roles:
                errors.append(f"duplicate profile role: {role}")
            if destination in destinations:
                errors.append(f"duplicate profile destination: {destination}")
            roles.add(role)
            destinations.add(destination)
            try:
                safe_relative_path(destination)
            except CliError as exc:
                errors.append(str(exc))
    if not isinstance(profile.get("ini_updates", {}), dict):
        errors.append("ini_updates must be an object")
    if not isinstance(profile.get("flat_key_updates", {}), dict):
        errors.append("flat_key_updates must be an object")
    return errors


def parse_artifacts(values: Iterable[str]) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for value in values:
        name, path = parse_assignment(value, "--artifact")
        if name in artifacts:
            raise CliError(f"Duplicate artifact role: {name}")
        artifacts[name] = path
    return artifacts


def expected_deployed_hash(component: Mapping[str, Any], role: str | None = None) -> str | None:
    files = component.get("expected_deployed_files_sha256") or component.get("expected_deployed_files")
    if role and isinstance(files, Mapping) and files.get(role):
        return str(files[role]).lower()
    value = component.get("expected_deployed_sha256")
    return str(value).lower() if value else None


def observed_deployed_hash(component: Mapping[str, Any], role: str | None = None) -> str | None:
    files = component.get("observed_deployed_files_sha256") or component.get("observed_deployed_files")
    if role and isinstance(files, Mapping) and files.get(role):
        return str(files[role]).lower()
    value = component.get("observed_deployed_sha256")
    return str(value).lower() if value else None


def validate_artifact(
    role: str,
    entry: Mapping[str, Any],
    artifact: Path,
    component: Mapping[str, Any] | None,
) -> dict[str, Any]:
    errors: list[str] = []
    if not artifact.is_file():
        errors.append(f"missing artifact: {artifact}")
        return {"role": role, "path": str(artifact), "status": "FAIL", "errors": errors}
    digest = sha256_file(artifact)
    expected_arch = entry.get("architecture")
    parsed = parse_pe(artifact) if expected_arch else None
    if expected_arch:
        actual_arch = parsed.get("machine_name") if parsed else None
        if actual_arch != expected_arch:
            errors.append(f"architecture mismatch: expected {expected_arch}, got {actual_arch or 'not PE'}")
    if component is None:
        errors.append(f"profile role {role} references an unknown lock component")
    else:
        expected = expected_deployed_hash(component, role)
        observed = observed_deployed_hash(component, role)
        if not expected and not observed:
            errors.append(f"lock has no observed or expected deployed hash for required component {component['name']}")
        if expected and digest != expected:
            errors.append(f"deployed hash mismatch for {component['name']}: expected {expected}, got {digest}")
        if observed and digest != observed:
            errors.append(f"observed hash mismatch for {component['name']}: lock {observed}, got {digest}")
    return {
        "role": role,
        "path": str(artifact),
        "sha256": digest,
        "pe": parsed,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
    }


def sectioned_ini_merge(text: str, updates: Mapping[str, Mapping[str, Any]]) -> str:
    """Update named INI sections and root keys while retaining unrelated lines."""

    lines = text.splitlines(keepends=True)
    if text and not text.endswith(("\n", "\r")):
        lines[-1] += "\n"

    def header_positions() -> dict[str, int]:
        positions: dict[str, int] = {}
        for index, line in enumerate(lines):
            match = re.match(r"^\s*\[([^]]+)\]\s*(?:\r?\n)?$", line)
            if match:
                positions.setdefault(match.group(1), index)
        return positions

    root_updates = updates.get("")
    if root_updates is not None:
        if not isinstance(root_updates, Mapping):
            raise CliError("INI root updates must be an object")
        first_header = len(lines)
        for index, line in enumerate(lines):
            if re.match(r"^\s*\[[^]]+\]", line):
                first_header = index
                break
        present: dict[str, int] = {}
        for index in range(first_header):
            match = re.match(r"^\s*([^=;#\s][^=]*)=(.*?)(\r?\n)?$", lines[index])
            if match:
                present[match.group(1).strip()] = index
        insert_at = first_header
        while insert_at > 0 and not lines[insert_at - 1].strip():
            insert_at -= 1
        for key, value in root_updates.items():
            rendered = f"{key}={value}\n"
            if str(key) in present:
                lines[present[str(key)]] = rendered
            else:
                lines.insert(insert_at, rendered)
                insert_at += 1

    for section, section_updates in updates.items():
        if section == "":
            continue
        if not isinstance(section_updates, Mapping):
            raise CliError(f"INI updates for [{section}] must be an object")
        header_index = header_positions().get(section)
        if header_index is None:
            if lines and not lines[-1].endswith(("\n", "\r")):
                lines[-1] += "\n"
            lines.append(f"[{section}]\n")
            for key, value in section_updates.items():
                lines.append(f"{key}={value}\n")
            continue
        next_header = len(lines)
        for index in range(header_index + 1, len(lines)):
            if re.match(r"^\s*\[[^]]+\]", lines[index]):
                next_header = index
                break
        present: dict[str, int] = {}
        for index in range(header_index + 1, next_header):
            match = re.match(r"^\s*([^=;#\s][^=]*)=(.*?)(\r?\n)?$", lines[index])
            if match:
                present[match.group(1).strip()] = index
        insert_at = next_header
        for key, value in section_updates.items():
            key = str(key)
            rendered = f"{key}={value}\n"
            if key in present:
                lines[present[key]] = rendered
            else:
                lines.insert(insert_at, rendered)
                insert_at += 1
    return "".join(lines)

def flat_key_value_merge(text: str, updates: Mapping[str, Any]) -> str:
    """Update exact flat key/value entries without touching INI sections."""

    lines = text.splitlines(keepends=True)
    if text and not text.endswith(("\n", "\r")):
        lines[-1] += "\n"
    positions: dict[str, int] = {}
    for index, line in enumerate(lines):
        match = re.match(r"^\s*([^#=\s][^=]*)=(.*?)(\r?\n)?$", line)
        if match:
            positions[match.group(1).strip()] = index
    for key, value in updates.items():
        key = str(key)
        rendered = f"{key}={value}\n"
        if key in positions:
            lines[positions[key]] = rendered
        else:
            lines.append(rendered)
    return "".join(lines)


def profile_config_texts(profile: Mapping[str, Any], existing_root: Path | None = None) -> dict[str, str]:
    config_texts: dict[str, str] = {}
    for destination, updates in profile.get("ini_updates", {}).items():
        relative = safe_relative_path(destination)
        current = ""
        if existing_root is not None:
            source = existing_root / relative
            if source.is_file():
                current = source.read_text(encoding="utf-8")
        config_texts[str(relative)] = sectioned_ini_merge(current, updates)
    for destination, updates in profile.get("flat_key_updates", {}).items():
        relative = safe_relative_path(destination)
        current = ""
        if existing_root is not None:
            source = existing_root / relative
            if source.is_file():
                current = source.read_text(encoding="utf-8")
        config_texts[str(relative)] = flat_key_value_merge(current, updates)
    return config_texts


def destination_root_for(relative: Path, game_dir: Path, host_dir: Path | None) -> Path:
    if relative.parts and relative.parts[0].lower() == "host64" and host_dir is not None:
        return host_dir / Path(*relative.parts[1:])
    return game_dir / relative


def build_stage_plan(
    profile: Mapping[str, Any], lock: Mapping[str, Any], artifacts: Mapping[str, Path]
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    profile_errors = validate_profile(profile)
    if profile_errors:
        return [], {}, profile_errors
    components = lock_components(lock)
    validations: list[dict[str, Any]] = []
    errors: list[str] = []
    plan: list[dict[str, Any]] = []
    for entry in profile["files"]:
        role = str(entry["role"])
        required = bool(entry.get("required", True))
        artifact = artifacts.get(role)
        if artifact is None:
            if required:
                errors.append(f"missing required artifact assignment: {role}")
            continue
        component_name = entry.get("component")
        component = components.get(str(component_name)) if component_name else None
        validation = validate_artifact(role, entry, artifact, component)
        validations.append(validation)
        errors.extend(f"{role}: {item}" for item in validation["errors"])
        if validation["status"] == "PASS":
            plan.append({"role": role, "source": str(artifact), "destination": str(entry["destination"])})
    config_texts = profile_config_texts(profile)
    return plan, config_texts, errors


def check_existing_conflicts(plan: Sequence[Mapping[str, Any]], destination: Path, allow_backup: bool) -> list[str]:
    errors: list[str] = []
    for item in plan:
        target = destination / safe_relative_path(str(item["destination"]))
        source = Path(str(item["source"]))
        if not target.is_file():
            continue
        if sha256_file(target) == sha256_file(source):
            continue
        if target.name.lower() in PROXY_NAMES and not allow_backup:
            errors.append(f"conflicting proxy exists; pass --backup-and-replace: {target}")
    return errors


def copy_with_journal(
    plan: Sequence[Mapping[str, Any]],
    config_texts: Mapping[str, str],
    destination: Path,
    journal_path: Path,
    allow_backup: bool,
) -> dict[str, Any]:
    """Apply a fully validated plan and record only paths owned by this install."""

    destination.mkdir(parents=True, exist_ok=True)
    backup_root = destination / ".obdlss5-backups" / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    entries: list[dict[str, Any]] = []
    all_files = [(Path(str(item["destination"])), Path(str(item["source"])), None) for item in plan]
    all_files.extend((Path(relative), None, text) for relative, text in config_texts.items())
    for relative, source, text in all_files:
        relative = safe_relative_path(str(relative))
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        prior_exists = target.is_file()
        prior_hash = sha256_file(target) if prior_exists else None
        backup_path: str | None = None
        if prior_exists:
            backup = backup_root / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            backup_path = str(backup)
        if source is not None:
            shutil.copy2(source, target)
        else:
            target.write_text(text or "", encoding="utf-8")
        entries.append(
            {
                "path": str(relative),
                "prior_exists": prior_exists,
                "prior_sha256": prior_hash,
                "backup_path": backup_path,
                "installed_sha256": sha256_file(target),
            }
        )
    journal = {
        "schema_version": 1,
        "installed_at": utc_now(),
        "destination": str(destination),
        "backup_root": str(backup_root) if backup_root.exists() else None,
        "entries": entries,
    }
    write_json(journal_path, journal)
    return journal


def cmd_inventory(args: argparse.Namespace) -> int:
    executable = Path(args.executable).expanduser().resolve()
    game_dir = Path(args.game_dir).expanduser().resolve() if args.game_dir else executable.parent
    modules = []
    for raw in args.module:
        path = Path(raw).expanduser().resolve()
        modules.append({"path": str(path), "sha256": sha256_file(path) if path.is_file() else None, "pe": parse_pe(path)})
    artifact_reports = []
    for role, path in parse_artifacts(args.artifact).items():
        artifact_reports.append({"role": role, "path": str(path), "sha256": sha256_file(path) if path.is_file() else None, "pe": parse_pe(path)})
    report = {
        "schema_version": 1,
        "run_id": new_run_id("inventory"),
        "collected_at": utc_now(),
        "executable": inspect_executable(executable),
        "game_dir": str(game_dir),
        "modules": modules,
        "artifacts": artifact_reports,
        "host": host_identity(),
        "writable_paths": {
            "game_dir_exists": game_dir.is_dir(),
            "game_dir_writable": os.access(game_dir, os.W_OK) if game_dir.exists() else os.access(game_dir.parent, os.W_OK),
            "host_dir": str(Path(args.host_dir).expanduser().resolve()) if args.host_dir else None,
        },
        "evidence": {
            "pe_identity": "VERIFIED" if inspect_executable(executable)["status"] == "INVENTORIED" else "UNKNOWN",
            "gpu": "UNKNOWN",
            "driver": "UNKNOWN",
            "live_behavior": "NOT_RUN",
        },
    }
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["executable"]["status"] == "INVENTORIED" else 1


def validate_stage_destination(destination: Path, apply: bool) -> list[str]:
    if apply:
        return []
    markers = [destination / "Oblivion.exe", destination / "OblivionRemastered.exe"]
    if any(marker.is_file() for marker in markers):
        return ["destination looks like a game root; pass --apply explicitly before modifying it"]
    return []

def cmd_stage(args: argparse.Namespace) -> int:
    profile_path, profile = resolve_profile(args.profile)
    lock = load_lock(Path(args.lock).expanduser().resolve())
    artifacts = parse_artifacts(args.artifact)
    plan, _, errors = build_stage_plan(profile, lock, artifacts)
    config_texts = profile_config_texts(profile, Path(args.destination).expanduser().resolve())
    destination = Path(args.destination).expanduser().resolve()
    errors.extend(validate_stage_destination(destination, args.apply))
    errors.extend(check_existing_conflicts(plan, destination, args.backup_and_replace))
    result: dict[str, Any] = {
        "schema_version": 1,
        "run_id": new_run_id("stage"),
        "profile": profile["id"],
        "profile_path": str(profile_path),
        "lock_path": str(Path(args.lock).expanduser().resolve()),
        "lock_digest": canonical_digest(lock),
        "destination": str(destination),
        "apply": bool(args.apply),
        "status": "FAILED" if errors else "VALIDATED",
        "errors": errors,
        "planned_artifacts": plan,
        "planned_configurations": sorted(config_texts),
    }
    if errors:
        if args.output:
            write_json(Path(args.output).expanduser().resolve(), result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    journal_path = Path(args.journal).expanduser().resolve() if args.journal else destination / "obdlss5-install-journal.json"
    if args.apply:
        journal = copy_with_journal(plan, config_texts, destination, journal_path, args.backup_and_replace)
    else:
        destination.mkdir(parents=True, exist_ok=True)
        journal = copy_with_journal(plan, config_texts, destination, journal_path, args.backup_and_replace)
    result.update({"status": "APPLIED" if args.apply else "STAGED", "journal": journal})
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def target_for_profile_path(relative: Path, game_dir: Path, host_dir: Path | None) -> Path:
    return destination_root_for(relative, game_dir, host_dir)


def read_evidence_state(path: Path | None) -> tuple[str, list[str]]:
    if path is None or not path.is_file():
        return "NOT_RUN", ["live evidence index is absent"]
    data = read_json(path)
    state = str(data.get("state", "UNKNOWN"))
    return state, list(data.get("limitations", []))


def cmd_verify(args: argparse.Namespace) -> int:
    profile_path, profile = resolve_profile(args.profile)
    lock_path = Path(args.lock).expanduser().resolve()
    lock = load_lock(lock_path)
    components = lock_components(lock)
    game_dir = Path(args.game_dir).expanduser().resolve()
    host_dir = Path(args.host_dir).expanduser().resolve() if args.host_dir else None
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    executable = Path(args.executable).expanduser().resolve() if args.executable else game_dir / "Oblivion.exe"
    exe_report = inspect_executable(executable)
    checks.append({"name": "classic_executable", "status": "PASS" if exe_report["status"] == "INVENTORIED" else "FAIL", "detail": exe_report})
    if exe_report["status"] != "INVENTORIED":
        failures.append("classic executable validation failed")
    for entry in profile["files"]:
        relative = safe_relative_path(str(entry["destination"]))
        target = target_for_profile_path(relative, game_dir, host_dir)
        component = components.get(str(entry.get("component")))
        expected_arch = entry.get("architecture")
        present = target.is_file()
        digest = sha256_file(target) if present else None
        arch = architecture_for(target) if present and expected_arch else None
        errors: list[str] = []
        if not present and entry.get("required", True):
            errors.append(f"missing required file: {target}")
        if expected_arch and present and arch != expected_arch:
            errors.append(f"architecture mismatch: expected {expected_arch}, got {arch}")
        if component is not None and present:
            expected = expected_deployed_hash(component, str(entry.get("role"))) or observed_deployed_hash(component, str(entry.get("role")))
            if not expected:
                errors.append(f"no locked deployed hash for component {component['name']}")
            elif digest != expected:
                errors.append(f"hash mismatch for {target}")
        status = "PASS" if not errors else "FAIL"
        checks.append({"name": f"placement:{relative}", "status": status, "path": str(target), "sha256": digest, "errors": errors})
        failures.extend(errors)
    evidence_path = Path(args.evidence_index).expanduser().resolve() if args.evidence_index else None
    live_state, limitations = read_evidence_state(evidence_path)
    checks.append({"name": "live_behavior", "status": "NOT_RUN" if live_state == "NOT_RUN" else live_state, "limitations": limitations})
    state = "FAILED" if failures else ("INVENTORIED" if live_state == "NOT_RUN" else live_state)
    report = {
        "schema_version": 1,
        "run_id": new_run_id("verify"),
        "collected_at": utc_now(),
        "profile": profile["id"],
        "profile_path": str(profile_path),
        "lock_digest": canonical_digest(lock),
        "state": state,
        "state_order": list(STATE_ORDER),
        "checks": checks,
        "failures": failures,
        "evidence": {
            "wrapper": "NOT_RUN",
            "guides": "NOT_RUN",
            "transport": "NOT_RUN",
            "dlaa": "NOT_RUN",
            "neural_rendering": live_state,
            "live_behavior": live_state,
        },
        "host": host_identity(),
    }
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if failures else 0


def source_is_allowed(path: Path) -> tuple[bool, str | None]:
    lowered = {part.lower() for part in path.parts}
    if lowered & FORBIDDEN_COLLECT_PARTS:
        return False, "path contains a forbidden sensitive-data directory"
    if path.suffix.lower() in {".ess", ".sav", ".save"}:
        return False, "save files are not collectible evidence"
    if any(token in path.name.lower() for token in ("password", "credential", "secret", "token")):
        return False, "credential-like file name is not collectible evidence"
    return True, None


def cmd_collect(args: argparse.Namespace) -> int:
    root = Path(args.output_root).expanduser().resolve()
    run_id = args.run_id or new_run_id("collect")
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    selected = []
    errors: list[str] = []
    for label, source in (parse_assignment(item, "--source") for item in args.source):
        allowed, reason = source_is_allowed(source)
        if not allowed:
            errors.append(f"{label}: {reason}")
            continue
        if not source.is_file():
            errors.append(f"{label}: missing source {source}")
            continue
        selected.append((label, source))
    if errors:
        shutil.rmtree(run_dir)
        result = {"schema_version": 1, "run_id": run_id, "status": "FAILED", "errors": errors}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    entries = []
    for label, source in selected:
        target = run_dir / safe_relative_path(label)
        if target.suffix == "" or target.name in {".", ".."}:
            target = target / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        entries.append({"label": label, "source": str(source), "target": str(target.relative_to(run_dir)), "sha256": sha256_file(target)})
    index = {
        "schema_version": 1,
        "run_id": run_id,
        "collected_at": utc_now(),
        "status": "COLLECTED",
        "entries": entries,
        "limitations": ["Only explicitly selected files were copied; game saves and credentials were excluded."],
    }
    write_json(run_dir / "index.json", index)
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), index)
    print(json.dumps(index, indent=2, sort_keys=True))
    return 0



def cmd_live_evidence(args: argparse.Namespace) -> int:
    run_id = args.run_id or new_run_id("live-evidence")
    result = classify_live_evidence(
        Path(args.feed_log).expanduser().resolve(),
        Path(args.host_log).expanduser().resolve(),
        Path(args.consumer_log).expanduser().resolve(),
        [Path(item).expanduser().resolve() for item in args.screenshot],
        run_started=args.run_started_epoch,
        run_id=run_id,
    )
    result["profile"] = args.profile
    result["collected_at"] = utc_now()
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "NR_ACTIVE" else 1

def cmd_rollback(args: argparse.Namespace) -> int:
    journal_path = Path(args.journal).expanduser().resolve()
    journal = read_json(journal_path)
    destination = Path(str(journal.get("destination", ""))).resolve()
    if not destination.is_dir():
        raise CliError(f"Journal destination does not exist: {destination}")
    restored: list[str] = []
    conflicts: list[str] = []
    for entry in journal.get("entries", []):
        target = destination / safe_relative_path(str(entry["path"]))
        if not target.exists():
            conflicts.append(f"missing installed path; preserved nothing: {target}")
            continue
        current_hash = sha256_file(target) if target.is_file() else None
        if current_hash != entry.get("installed_sha256"):
            conflicts.append(f"user-modified path preserved: {target}")
            continue
        if entry.get("prior_exists"):
            backup_path = Path(str(entry.get("backup_path", "")))
            if not backup_path.is_file():
                conflicts.append(f"backup missing; preserved installed path: {target}")
                continue
            shutil.copy2(backup_path, target)
        else:
            target.unlink()
            if target.parent != destination and not any(target.parent.iterdir()):
                target.parent.rmdir()
        restored.append(str(target))
    result = {
        "schema_version": 1,
        "rolled_back_at": utc_now(),
        "journal": str(journal_path),
        "status": "ROLLED_BACK" if not conflicts else "CONFLICTS",
        "restored": restored,
        "conflicts": conflicts,
    }
    output = Path(args.output).expanduser().resolve() if args.output else journal_path.with_name("rollback-result.json")
    write_json(output, result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if conflicts else 0


def interpret_result_code(api: str, code: str | int) -> str:
    """Interpret codes in their producing API domain, never with code==0 globally."""

    normalized = str(code).strip().upper()
    if api.upper() == "NGX":
        return "SUCCESS" if normalized in {"0X1", "1", "NVSDK_NGX_RESULT_SUCCESS"} else "FAILURE"
    if api.upper() in {"HRESULT", "D3D", "WIN32"}:
        return "SUCCESS" if normalized in {"0", "0X0", "S_OK", "ERROR_SUCCESS"} else "FAILURE"
    return "UNKNOWN"


def parse_consumer_log(path: Path, run_started: float | None = None, run_id: str | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "NOT_RUN", "path": str(path), "reason": "log missing"}
    stat = path.stat()
    stale = run_started is not None and stat.st_mtime < run_started
    text = path.read_text(encoding="utf-8", errors="replace")
    upper = text.upper()
    armed = bool(re.search(r"\b(?:DFC|CHICKEN|CONSUMER)\b[^\n]*(?:ARMED|READY)|\bARMED\b", upper))
    dlaa = bool(re.search(r"\bDLAA\b[^\n]*(?:EVALUAT|PASS|SUCCESS)|(?:EVALUAT|PASS|SUCCESS)[^\n]*\bDLAA\b", upper))
    nr = bool(re.search(r"\b(?:NR|NEURAL)\b[^\n]*(?:EVALUAT|FRAME|PASS|ACTIVE|SUCCESS)|(?:EVALUAT|FRAME|PASS|SUCCESS)[^\n]*\b(?:NR|NEURAL)\b", upper))
    init_failure = bool(re.search(r"(?:INITIALI[ZS]ATION|CREATEFEATURE|INIT)[^\n]*(?:FAIL|ERROR)|\bFAILED TO INITIALI[ZS]E\b", upper))
    codes = []
    for match in re.finditer(r"\b(NGX|HRESULT|D3D)\b[^\n]*?(?:RESULT|CODE)\s*[=:]\s*(0x[0-9A-Fa-f]+|\d+|S_OK)", text, re.I):
        api, code = match.groups()
        codes.append({"api": api.upper(), "code": code, "interpretation": interpret_result_code(api, code)})
    if stale:
        status = "UNKNOWN"
        reason = "log predates this run"
    elif init_failure:
        status = "FAILED"
        reason = "consumer initialization failure observed"
    elif nr:
        status = "NR_ACTIVE"
        reason = "neural evaluation evidence observed in this log"
    elif dlaa:
        status = "DLAA_OK"
        reason = "DLAA evidence without independent NR evidence"
    elif armed:
        status = "UNKNOWN"
        reason = "consumer armed but no evaluation evidence"
    else:
        status = "NOT_RUN"
        reason = "no recognized consumer evidence"
    return {
        "path": str(path),
        "run_id": run_id,
        "stale": stale,
        "armed": armed,
        "dlaa_evidence": dlaa,
        "nr_evidence": nr,
        "initialization_failure": init_failure,
        "api_codes": codes,
        "status": status,
        "reason": reason,
    }



def classify_live_evidence(
    feed_log: Path,
    host_log: Path,
    consumer_log: Path,
    screenshots: Sequence[Path] = (),
    run_started: float | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Classify independently observable live-path evidence.

    This is deliberately an evidence classifier: it never treats a
    screenshot as proof of neural execution and never treats DLAA/host
    evaluation as proof of NR. The caller may supply a run start epoch so
    stale logs are rejected consistently with parse_consumer_log.
    """

    def read(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""

    def fresh(path: Path) -> bool:
        return path.is_file() and (run_started is None or path.stat().st_mtime >= run_started)

    feed_text = read(feed_log)
    host_text = read(host_log)
    feed_delivered = bool(re.search(r"\bframe\s+\d+\s+delivered\b", feed_text, re.I))
    host_evaluated = bool(re.search(r"\bframe\s+\d+\s+evaluated\b", host_text, re.I))
    host_gpu_timing = bool(re.search(r"\bDLSS\s+GPU\s+[0-9.]+\s+ms/frame\b", host_text, re.I))
    consumer = parse_consumer_log(consumer_log, run_started=run_started, run_id=run_id)
    screenshot_reports = [
        {"path": str(path), "present": path.is_file(), "sha256": sha256_file(path) if path.is_file() else None}
        for path in screenshots
    ]
    checks = {
        "feed_delivered": {"pass": feed_delivered, "path": str(feed_log)},
        "host_evaluated": {"pass": host_evaluated, "path": str(host_log)},
        "host_gpu_timing": {"pass": host_gpu_timing, "path": str(host_log)},
        "consumer_nr_active": {"pass": consumer["status"] == "NR_ACTIVE", "path": str(consumer_log)},
        "screenshots_present": {
            "pass": bool(screenshot_reports) and all(item["present"] for item in screenshot_reports),
            "count": len(screenshot_reports),
        },
        "logs_fresh": {
            "pass": all(fresh(path) for path in (feed_log, host_log, consumer_log)),
            "run_started_epoch": run_started,
        },
    }
    limitations: list[str] = []
    for name, check in checks.items():
        if not check["pass"]:
            limitations.append(f"live evidence check failed: {name}")
    if run_started is None:
        limitations.append("run start epoch was not supplied; freshness is limited to same-capture inspection")
    execution_pass = all(
        checks[name]["pass"]
        for name in ("feed_delivered", "host_evaluated", "host_gpu_timing", "consumer_nr_active", "logs_fresh")
    )
    screenshot_pass = checks["screenshots_present"]["pass"]
    if execution_pass and screenshot_pass:
        status = "NR_ACTIVE"
    elif execution_pass:
        status = "NR_ACTIVE_NO_SCREENSHOTS"
    elif any(check["pass"] for check in checks.values()):
        status = "PARTIAL"
    else:
        status = "NOT_RUN"
    return {
        "schema_version": 1,
        "run_id": run_id,
        "status": status,
        "checks": checks,
        "consumer": consumer,
        "screenshots": screenshot_reports,
        "limitations": limitations,
    }

def validate_frame_request(request: Mapping[str, Any], current_generation: int) -> dict[str, Any]:
    errors: list[str] = []
    if request.get("resource_generation") != current_generation:
        errors.append("stale resource generation")
    dimensions = request.get("input_dimensions")
    output_dimensions = request.get("output_dimensions")
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 2 or min(dimensions) <= 0:
        errors.append("invalid input dimensions")
    if not isinstance(output_dimensions, (list, tuple)) or len(output_dimensions) != 2 or min(output_dimensions) <= 0:
        errors.append("invalid output dimensions")
    if isinstance(dimensions, (list, tuple)) and isinstance(output_dimensions, (list, tuple)) and tuple(dimensions) != tuple(output_dimensions):
        errors.append("incompatible input/output dimensions for native DLAA profile")
    for field in ("color", "depth", "motion", "output"):
        if not request.get("resources", {}).get(field):
            errors.append(f"missing required input/resource: {field}")
    if not request.get("ready"):
        errors.append("frame readiness/completion mechanism is absent")
    return {
        "status": "VALID" if not errors else "INVALID",
        "frame_id": request.get("frame_id"),
        "resource_generation": request.get("resource_generation"),
        "errors": errors,
    }


@dataclass
class FrameHistory:
    generation: int = 0
    reset_reason: str = "initial"
    reset_count: int = 0
    last_frame_id: int | None = None

    def rebuild(self, generation: int, reason: str) -> None:
        if generation <= self.generation:
            raise CliError("resource generation must increase on rebuild")
        self.generation = generation
        self.reset_reason = reason
        self.reset_count += 1
        self.last_frame_id = None

    def accept_result(self, generation: int, frame_id: int) -> bool:
        if generation != self.generation:
            return False
        self.last_frame_id = frame_id
        return True


def scenario_definitions() -> list[dict[str, Any]]:
    common = "run identity, profile digest, build identity and selected evidence paths are recorded"
    return [
        {"id": "A01", "name": "Baseline", "preconditions": "validated PE32/I386 Oblivion executable", "actions": "launch native baseline", "timeout_seconds": 120, "expected": "playable native run", "assertions": ["process is the selected executable", "no baseline crash"], "evidence": ["inventory.json", "baseline.png"]},
        {"id": "A02", "name": "Host H0", "preconditions": "host64 and user-supplied runtimes are locked", "actions": "run --test --hide with NR off and on", "timeout_seconds": 180, "expected": "synthetic evaluation plus independent consumer NR evidence", "assertions": ["consumer evidence is not inferred from DLAA"], "evidence": ["host-test.log", "consumer.log"]},
        {"id": "A03", "name": "Wrapper", "preconditions": "isolated game install", "actions": "run dgVoodoo-only profile through interior/exterior/menus", "timeout_seconds": 300, "expected": "correct D3D11 wrapper rendering", "assertions": ["watermark and actual API activation observed"], "evidence": ["wrapper.log", "wrapper-interior.png"]},
        {"id": "A04", "name": "Guides", "preconditions": "ReShade and guides enabled, feed disabled", "actions": "capture depth and motion scenarios", "timeout_seconds": 600, "expected": "aligned raw depth and coherent motion with limitations recorded", "assertions": ["non-empty near/far depth", "motion direction inspected"], "evidence": ["guides.json", "depth.png", "motion.mp4"]},
        {"id": "A05", "name": "Transport", "preconditions": "mode=1 and async_home=0", "actions": "round-trip controlled frames", "timeout_seconds": 300, "expected": "correct dimensions/channels/orientation and no stale output", "assertions": ["protocol and fence progress match", "host loss cannot block indefinitely"], "evidence": ["transport.json"]},
        {"id": "A06", "name": "Neural proof", "preconditions": "DFC armed and DLAA control passes", "actions": "matched NR OFF/ON static and motion captures", "timeout_seconds": 600, "expected": "actual consumer NR activity plus visible qualified effect", "assertions": ["NR evidence is same-run", "visual review separate from execution evidence"], "evidence": ["nr-off.png", "nr-on.png", "motion.mp4", "consumer.log"]},
        {"id": "A07", "name": "Toggle", "preconditions": "live game path passes", "actions": "perform ten OFF/ON cycles", "timeout_seconds": 600, "expected": "no crash/hang", "assertions": ["history warm-up documented"], "evidence": ["toggle.json"]},
        {"id": "A08", "name": "Gameplay", "preconditions": "controlled save/scene fixtures", "actions": "thirty-minute mixed gameplay", "timeout_seconds": 2100, "expected": "no reproducible crash or indefinite freeze", "assertions": ["all named activities covered"], "evidence": ["gameplay.json", "failure-captures/"]},
        {"id": "A09", "name": "Lifecycle", "preconditions": "isolated test installation", "actions": "five save/load, five alt-tabs, resize and return", "timeout_seconds": 1200, "expected": "recovery or safe disabled state", "assertions": ["no invalid texture reuse"], "evidence": ["lifecycle.json"]},
        {"id": "A10", "name": "Host failure", "preconditions": "game path active", "actions": "stop helper, observe recovery, restart", "timeout_seconds": 300, "expected": "rendering continues or effect disables within five seconds", "assertions": ["no stale handle reuse", "no indefinite wait"], "evidence": ["host-loss.json", "host-loss.log"]},
        {"id": "A11", "name": "Reinstall/rollback", "preconditions": "journal and clean baseline", "actions": "reinstall exact lock then rollback", "timeout_seconds": 600, "expected": "hash/profile reproduction and owned-only restore", "assertions": ["user-modified file preserved"], "evidence": ["install-journal.json", "rollback.json"]},
        {"id": "A12", "name": "Performance", "preconditions": "each pipeline stage independently ready", "actions": "two scenes, warm-up and three 60-second repetitions", "timeout_seconds": 2400, "expected": "metrics recorded or explicitly unavailable", "assertions": ["mean FPS formula and percentile definition recorded", "no extrapolation from 640x360 H0"], "evidence": ["performance.json"]},
    ]


def run_live_harness(args: argparse.Namespace) -> dict[str, Any]:
    run_id = args.run_id or new_run_id("game")
    started_at = utc_now()
    results_root = Path(args.results_root).expanduser().resolve()
    run_dir = results_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    limitations: list[str] = []
    preflight: dict[str, Any] = {}
    launch_performed = False
    process_exit: int | None = None
    ready_observed = False
    _, profile = resolve_profile(args.profile)
    lock = load_lock(Path(args.lock).expanduser().resolve())
    preflight["profile"] = profile["id"]
    preflight["profile_digest"] = canonical_digest(profile)
    preflight["lock_digest"] = canonical_digest(lock)
    game_dir: Path | None = None
    if not args.game_dir or not args.executable:
        limitations.append("game directory and executable are required for live harness preflight")
    else:
        game_dir = Path(args.game_dir).expanduser().resolve()
        exe = Path(args.executable).expanduser().resolve()
        preflight["inventory"] = inspect_executable(exe)
        if preflight["inventory"]["status"] != "INVENTORIED":
            limitations.append("classic executable validation did not pass")
        if not game_dir.is_dir():
            limitations.append("selected game directory does not exist")
    if not limitations:
        if not args.launch_command:
            limitations.append("an explicit --launch-command is required; launcher readiness cannot be inferred")
        elif not args.ready_file:
            limitations.append("an explicit --ready-file readiness marker is required; fixed sleep is not readiness")
        else:
            try:
                command = shlex.split(args.launch_command, posix=False)
            except ValueError as exc:
                limitations.append(f"launch command could not be parsed: {exc}")
                command = []
            if not command:
                limitations.append("launch command is empty")
            else:
                ready = Path(args.ready_file).expanduser()
                if not ready.is_absolute():
                    ready = game_dir / ready
                stdout_path = run_dir / "game-process.log"
                with stdout_path.open("w", encoding="utf-8") as log:
                    process = subprocess.Popen(command, cwd=game_dir, stdout=log, stderr=subprocess.STDOUT)
                    launch_performed = True
                    deadline = time.monotonic() + max(1.0, float(args.timeout))
                    while time.monotonic() < deadline:
                        if ready.is_file():
                            ready_observed = True
                            break
                        process_exit = process.poll()
                        if process_exit is not None:
                            break
                        time.sleep(min(0.1, max(0.01, deadline - time.monotonic())))
                    if not ready_observed and process_exit is None:
                        limitations.append("bounded readiness timeout expired without an observed marker")
                    elif not ready_observed:
                        limitations.append(f"game process exited before readiness marker (exit={process_exit})")
                    if ready_observed:
                        limitations.append("game readiness was observed, but scenario driver, lossless capture and visual verdict inputs are not supplied")
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                            limitations.append("test-owned game process required forced cleanup")
                    process_exit = process.returncode
    limitations.append("DFC/NVIDIA runtime validation, scenario input driving, screenshots and visual review remain unavailable in this checkout")
    limitations.append("no live acceptance result is inferred from offline unit or integration tests")
    reason = "live prerequisites are unavailable"
    if ready_observed:
        reason = "readiness observed, but required scenario/capture/visual evidence is absent"
    scenarios = [{**scenario, "status": "BLOCKED_ENVIRONMENT", "result": "NOT_RUN", "reason": reason} for scenario in scenario_definitions()]
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": utc_now(),
        "status": "BLOCKED_ENVIRONMENT",
        "profile": profile["id"],
        "profile_digest": canonical_digest(profile),
        "lock_digest": canonical_digest(lock),
        "build_identity": None,
        "preflight": preflight,
        "process_exit": process_exit,
        "ready_observed": ready_observed,
        "scenarios": scenarios,
        "screenshots": [],
        "visual_verdicts": [],
        "limitations": limitations,
        "launch_performed": launch_performed,
        "two_consecutive_final_runs": False,
    }
    write_json(run_dir / "game-suite.json", result)
    return result

def load_test_module() -> Any:
    tests_dir = REPO_ROOT / "obdlss5" / "tests"
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import importlib.util

    path = tests_dir / "test_obdlss5.py"
    spec = importlib.util.spec_from_file_location("obdlss5_test_module", path)
    if spec is None or spec.loader is None:
        raise CliError(f"Unable to load test module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_unittest_suite(suite_name: str, output_path: Path | None) -> tuple[int, dict[str, Any]]:
    import unittest

    module = load_test_module()
    loader = unittest.TestLoader()
    if suite_name == "unit":
        suite = loader.loadTestsFromTestCase(module.TestProductionValidators)
    elif suite_name == "integration":
        suite = loader.loadTestsFromTestCase(module.TestStagingAndRollbackIntegration)
    else:
        suite = unittest.TestSuite([
            loader.loadTestsFromTestCase(module.TestProductionValidators),
            loader.loadTestsFromTestCase(module.TestStagingAndRollbackIntegration),
        ])
    stream = __import__("io").StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)
    report = {
        "suite": suite_name,
        "status": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun,
        "failures": [str(item[1]) for item in result.failures],
        "errors": [str(item[1]) for item in result.errors],
        "output": stream.getvalue(),
    }
    if output_path:
        write_json(output_path, report)
    return (0 if result.wasSuccessful() else 1), report


def cmd_test(args: argparse.Namespace) -> int:
    reports: list[dict[str, Any]] = []
    exit_code = 0
    if args.suite in {"unit", "integration", "all"}:
        suite_names = ["unit", "integration"] if args.suite == "all" else [args.suite]
        for name in suite_names:
            code, report = run_unittest_suite(name, None)
            reports.append(report)
            exit_code = max(exit_code, code)
    if args.suite in {"game", "all"}:
        game = run_live_harness(args)
        reports.append({"suite": "game", **game})
        exit_code = 1
    result = {
        "schema_version": 1,
        "run_id": new_run_id("test"),
        "profile": args.profile,
        "status": "PASS" if exit_code == 0 else "FAILED_OR_BLOCKED",
        "reports": reports,
    }
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


def cmd_release_check(args: argparse.Namespace) -> int:
    evidence_path = Path(args.evidence_index).expanduser().resolve()
    failures: list[str] = []
    if not evidence_path.is_file():
        failures.append(f"evidence index is missing: {evidence_path}")
        evidence: dict[str, Any] = {}
    else:
        evidence = read_json(evidence_path)
    if evidence.get("profile") != args.profile:
        failures.append("evidence profile does not match selected profile")
    if not evidence.get("final_build_hash") or not evidence.get("profile_lock_hash"):
        failures.append("final build/profile hashes are missing")
    acceptance = evidence.get("acceptance", {})
    for scenario in scenario_definitions():
        item = acceptance.get(scenario["id"], {}) if isinstance(acceptance, dict) else {}
        if item.get("status") != "PASS":
            failures.append(f"{scenario['id']} is not PASS")
        if not item.get("evidence"):
            failures.append(f"{scenario['id']} has no evidence paths")
    visual = evidence.get("visual_verdicts", [])
    if not visual:
        failures.append("visual verdicts are missing")
    runs = evidence.get("final_live_runs", [])
    if len(runs) < 2 or runs[0] == runs[1]:
        failures.append("two consecutive final live-run IDs are required")
    if evidence.get("state") not in {"POC_VERIFIED", "FLAT_CORE_VERIFIED"}:
        failures.append("overall evidence state is not releasable")
    result = {
        "schema_version": 1,
        "checked_at": utc_now(),
        "profile": args.profile,
        "status": "PASS" if not failures else "FAIL_CLOSED",
        "failures": failures,
        "evidence_index": str(evidence_path),
    }
    if args.output:
        write_json(Path(args.output).expanduser().resolve(), result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obdlss5.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inventory = sub.add_parser("inventory", help="Inspect PE identity, modules and host metadata")
    inventory.add_argument("--executable", required=True)
    inventory.add_argument("--game-dir")
    inventory.add_argument("--host-dir")
    inventory.add_argument("--module", action="append", default=[])
    inventory.add_argument("--artifact", action="append", default=[])
    inventory.add_argument("--output")
    inventory.set_defaults(func=cmd_inventory)

    stage = sub.add_parser("stage", help="Validate and stage/apply a locked profile")
    stage.add_argument("--profile", default=DEFAULT_PROFILE)
    stage.add_argument("--lock", default=str(DEFAULT_LOCK))
    stage.add_argument("--destination", required=True)
    stage.add_argument("--artifact", action="append", default=[])
    stage.add_argument("--apply", action="store_true")
    stage.add_argument("--backup-and-replace", action="store_true")
    stage.add_argument("--journal")
    stage.add_argument("--output")
    stage.set_defaults(func=cmd_stage)

    verify = sub.add_parser("verify", help="Verify placement, hashes and evidence state")
    verify.add_argument("--profile", default=DEFAULT_PROFILE)
    verify.add_argument("--lock", default=str(DEFAULT_LOCK))
    verify.add_argument("--game-dir", required=True)
    verify.add_argument("--host-dir")
    verify.add_argument("--executable")
    verify.add_argument("--evidence-index")
    verify.add_argument("--output")
    verify.set_defaults(func=cmd_verify)

    collect = sub.add_parser("collect", help="Collect explicitly selected evidence files")
    collect.add_argument("--output-root", required=True)
    collect.add_argument("--source", action="append", default=[])
    collect.add_argument("--run-id")
    collect.add_argument("--output")
    collect.set_defaults(func=cmd_collect)

    live = sub.add_parser("live-evidence", help="Classify captured live feed/host/consumer evidence")
    live.add_argument("--profile", default=DEFAULT_PROFILE)
    live.add_argument("--feed-log", required=True)
    live.add_argument("--host-log", required=True)
    live.add_argument("--consumer-log", required=True)
    live.add_argument("--screenshot", action="append", default=[])
    live.add_argument("--run-started-epoch", type=float)
    live.add_argument("--run-id")
    live.add_argument("--output")
    live.set_defaults(func=cmd_live_evidence)
    rollback = sub.add_parser("rollback", help="Restore only paths owned by an install journal")
    rollback.add_argument("--journal", required=True)
    rollback.add_argument("--output")
    rollback.set_defaults(func=cmd_rollback)

    test = sub.add_parser("test", help="Run unit, integration or live game harness suites")
    test.add_argument("--suite", choices=("unit", "integration", "game", "all"), required=True)
    test.add_argument("--profile", default=DEFAULT_PROFILE)
    test.add_argument("--lock", default=str(DEFAULT_LOCK))
    test.add_argument("--game-dir")
    test.add_argument("--host-dir")
    test.add_argument("--executable")
    test.add_argument("--launch-command")
    test.add_argument("--ready-file")
    test.add_argument("--timeout", type=float, default=120.0)
    test.add_argument("--results-root", default=str(REPO_ROOT / "obdlss5" / "results"))
    test.add_argument("--run-id")
    test.add_argument("--output")
    test.set_defaults(func=cmd_test)

    release = sub.add_parser("release-check", help="Fail closed unless final evidence is complete")
    release.add_argument("--profile", default=DEFAULT_PROFILE)
    release.add_argument("--evidence-index", default=str(REPO_ROOT / "obdlss5" / "results" / "evidence-index.json"))
    release.add_argument("--output")
    release.set_defaults(func=cmd_release_check)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CliError as exc:
        error = {"status": "FAILED", "error": str(exc)}
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    except OSError as exc:
        error = {"status": "FAILED", "error": str(exc)}
        print(json.dumps(error, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

