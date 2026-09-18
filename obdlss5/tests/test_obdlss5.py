from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from obdlss5.tools.obdlss5 import (
    FrameHistory,
    build_stage_plan,
    canonical_digest,
    classify_live_evidence,
    check_existing_conflicts,
    copy_with_journal,
    flat_key_value_merge,
    interpret_result_code,
    parse_consumer_log,
    profile_config_texts,
    sectioned_ini_merge,
    sha256_file,
    inspect_executable,
    validate_frame_request,
    validate_stage_destination
)


def fake_pe(path: Path, machine: int, optional_magic: int) -> Path:
    data = bytearray(128)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, machine)
    struct.pack_into("<H", data, 88, optional_magic)
    path.write_bytes(data)
    return path


def minimal_profile(role: str = "client") -> dict:
    return {
        "id": "fixture-profile",
        "scope": "classic-oblivion-flat-only",
        "view_count": 1,
        "files": [
            {
                "role": role,
                "component": "fixture",
                "destination": "client.dll",
                "architecture": "I386",
                "required": True,
            }
        ],
        "ini_updates": {},
        "flat_key_updates": {},
    }


class TestProductionValidators(unittest.TestCase):
    def test_stage_rejects_wrong_architecture_before_destination_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            artifact = fake_pe(root / "client.dll", 0x8664, 0x20B)
            profile = minimal_profile()
            lock = {"components": [{"name": "fixture", "observed_deployed_sha256": sha256_file(artifact)}]}
            plan, _, errors = build_stage_plan(profile, lock, {"client": artifact})
            self.assertEqual(plan, [])
            self.assertTrue(any("architecture mismatch" in error for error in errors))
            self.assertFalse((root / "destination").exists())

    def test_stage_rejects_mismatched_hash_before_destination_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            artifact = fake_pe(root / "client.dll", 0x014C, 0x10B)
            profile = minimal_profile()
            lock = {"components": [{"name": "fixture", "observed_deployed_sha256": "0" * 64}]}
            plan, _, errors = build_stage_plan(profile, lock, {"client": artifact})
            self.assertEqual(plan, [])
            self.assertTrue(any("observed hash mismatch" in error for error in errors))
            self.assertFalse((root / "destination").exists())

    def test_stage_rejects_missing_required_dependency_assignment(self) -> None:
        profile = minimal_profile()
        lock = {"components": [{"name": "fixture", "observed_deployed_sha256": "0" * 64}]}
        plan, _, errors = build_stage_plan(profile, lock, {})
        self.assertEqual(plan, [])
        self.assertIn("missing required artifact assignment: client", errors)

    def test_sectioned_ini_merge_preserves_unrelated_sections_and_keys(self) -> None:
        original = "; keep comment\n[GENERAL]\nEnabled=false\nKeep=one\n\n[Other]\nEnabled=false\n"
        merged = sectioned_ini_merge(original, {"GENERAL": {"Enabled": "true"}})
        self.assertIn("Enabled=true", merged)
        self.assertIn("Keep=one", merged)
        self.assertIn("[Other]\nEnabled=false", merged)
        self.assertIn("; keep comment", merged)

    def test_flat_key_merge_changes_only_named_keys(self) -> None:
        original = "enabled=0\nmode=1\n# preserve\nother=value\n"
        merged = flat_key_value_merge(original, {"mode": 2, "async_home": 0})
        self.assertIn("enabled=0", merged)
        self.assertIn("mode=2", merged)
        self.assertIn("# preserve", merged)
        self.assertIn("other=value", merged)
        self.assertIn("async_home=0", merged)

    def test_unicode_path_and_profile_digest_are_supported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="obdlss5-测试-") as raw:
            path = Path(raw) / "配置" / "profile.json"
            path.parent.mkdir()
            path.write_text('{"id":"unicode"}', encoding="utf-8")
            self.assertTrue(path.is_file())
            self.assertEqual(len(canonical_digest({"path": str(path)})), 64)

    def test_inventory_accepts_classic_pe32_and_rejects_pe32_plus(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            classic = fake_pe(root / "Oblivion.exe", 0x014C, 0x10B)
            remastered = fake_pe(root / "OblivionRemastered.exe", 0x8664, 0x20B)
            self.assertEqual(inspect_executable(classic)["status"], "INVENTORIED")
            self.assertEqual(inspect_executable(remastered)["status"], "FAILED")

    def test_existing_proxy_requires_explicit_backup_and_replace(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            destination = root / "game"
            destination.mkdir()
            target = destination / "dxgi.dll"
            source = root / "new.dll"
            target.write_bytes(b"old")
            source.write_bytes(b"new")
            plan = [{"destination": "dxgi.dll", "source": str(source)}]
            self.assertTrue(check_existing_conflicts(plan, destination, False))
            self.assertEqual(check_existing_conflicts(plan, destination, True), [])

    def test_root_ini_updates_stay_before_the_first_section(self) -> None:
        original = "Techniques=Old\n\n[DLSS5_Feed.fx]\nOther=one\n"
        merged = sectioned_ini_merge(original, {"": {"Techniques": "New", "TechniqueSorting": "New"}})
        self.assertTrue(merged.startswith("Techniques=New\nTechniqueSorting=New\n"))
        self.assertIn("[DLSS5_Feed.fx]\nOther=one", merged)

    def test_stage_refuses_obvious_game_root_without_apply(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw)
            (destination / "Oblivion.exe").write_bytes(b"marker")
            self.assertTrue(validate_stage_destination(destination, False))
            self.assertEqual(validate_stage_destination(destination, True), [])
    def test_profile_configuration_merges_existing_destination_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "ReShade.ini").write_text("[GENERAL]\nKeep=one\nEnabled=false\n[Other]\nEnabled=false\n", encoding="utf-8")
            profile = {"ini_updates": {"ReShade.ini": {"GENERAL": {"Enabled": "true"}}}, "flat_key_updates": {}}
            result = profile_config_texts(profile, root)
            self.assertIn("Keep=one", result["ReShade.ini"])
            self.assertIn("Enabled=true", result["ReShade.ini"])
            self.assertIn("[Other]\nEnabled=false", result["ReShade.ini"])
    def test_log_fixtures_distinguish_dlaa_armed_nr_stale_and_init_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            dlaa = root / "dlaa.log"
            dlaa.write_text("DLAA evaluation success; NGX result=0x1\n", encoding="utf-8")
            self.assertEqual(parse_consumer_log(dlaa)["status"], "DLAA_OK")

            armed = root / "armed.log"
            armed.write_text("DFC ARMED\n", encoding="utf-8")
            self.assertEqual(parse_consumer_log(armed)["status"], "UNKNOWN")

            nr = root / "nr.log"
            nr.write_text("DFC ARMED\nNR evaluation frame=42\n", encoding="utf-8")
            self.assertEqual(parse_consumer_log(nr)["status"], "NR_ACTIVE")

            stale = root / "stale.log"
            stale.write_text("NR evaluation frame=1\n", encoding="utf-8")
            old = 1000.0
            os.utime(stale, (old, old))
            self.assertEqual(parse_consumer_log(stale, run_started=2000.0)["status"], "UNKNOWN")

            failure = root / "failure.log"
            failure.write_text("initialization failed: CreateFeature\n", encoding="utf-8")
            self.assertEqual(parse_consumer_log(failure)["status"], "FAILED")

    def test_api_result_codes_are_interpreted_in_their_own_domains(self) -> None:
        self.assertEqual(interpret_result_code("NGX", "0x1"), "SUCCESS")
        self.assertEqual(interpret_result_code("NGX", "0"), "FAILURE")
        self.assertEqual(interpret_result_code("HRESULT", "0"), "SUCCESS")
        self.assertEqual(interpret_result_code("unknown", "0"), "UNKNOWN")

    def test_frame_contract_rejects_stale_missing_and_incompatible_requests(self) -> None:
        base = {
            "frame_id": 7,
            "resource_generation": 2,
            "input_dimensions": [1920, 1080],
            "output_dimensions": [1920, 1080],
            "resources": {"color": "c", "depth": "d", "motion": "m", "output": "o"},
            "ready": True,
        }
        self.assertEqual(validate_frame_request(base, 2)["status"], "VALID")
        self.assertIn("stale resource generation", validate_frame_request({**base, "resource_generation": 1}, 2)["errors"])
        self.assertIn("missing required input/resource: depth", validate_frame_request({**base, "resources": {"color": "c"}}, 2)["errors"])
        mismatch = validate_frame_request({**base, "output_dimensions": [1280, 720]}, 2)
        self.assertTrue(any("incompatible input/output dimensions" in error for error in mismatch["errors"]))

    def test_frame_history_resets_only_after_rebuild_and_rejects_old_results(self) -> None:
        history = FrameHistory()
        self.assertTrue(history.accept_result(0, 1))
        history.rebuild(1, "resize")
        self.assertEqual(history.reset_count, 1)
        self.assertIsNone(history.last_frame_id)
        self.assertFalse(history.accept_result(0, 2))
        self.assertTrue(history.accept_result(1, 3))
        with self.assertRaises(RuntimeError):
            history.rebuild(1, "duplicate")



    def test_live_evidence_classifier_reports_complete_neural_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feed = root / "feed.log"
            host = root / "host.log"
            consumer = root / "consumer.log"
            screenshot = root / "nr-on.png"
            feed.write_text("frame 12 delivered (2560x1440)\n", encoding="utf-8")
            host.write_text("frame 12 evaluated (DLSS GPU 6.2 ms/frame)\n", encoding="utf-8")
            consumer.write_text("standalone neural frame succeeded\n", encoding="utf-8")
            screenshot.write_bytes(b"image")
            result = classify_live_evidence(feed, host, consumer, [screenshot], run_id="complete")
            self.assertEqual(result["status"], "NR_ACTIVE")
            self.assertTrue(all(item["pass"] for item in result["checks"].values() if "pass" in item))

    def test_live_evidence_classifier_separates_execution_from_missing_capture(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feed = root / "feed.log"
            host = root / "host.log"
            consumer = root / "consumer.log"
            feed.write_text("frame 12 delivered\n", encoding="utf-8")
            host.write_text("frame 12 evaluated DLSS GPU 6.2 ms/frame\n", encoding="utf-8")
            consumer.write_text("standalone neural frame succeeded\n", encoding="utf-8")
            result = classify_live_evidence(feed, host, consumer)
            self.assertEqual(result["status"], "NR_ACTIVE_NO_SCREENSHOTS")
            self.assertIn("screenshots_present", result["checks"])

    def test_live_evidence_classifier_reports_partial_when_only_some_signals_exist(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feed = root / "feed.log"
            host = root / "host.log"
            consumer = root / "consumer.log"
            feed.write_text("frame 12 delivered\n", encoding="utf-8")
            result = classify_live_evidence(feed, host, consumer)
            self.assertEqual(result["status"], "PARTIAL")
            self.assertFalse(result["checks"]["consumer_nr_active"]["pass"])

    def test_live_evidence_classifier_reports_not_run_when_nothing_exists(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = classify_live_evidence(root / "feed.log", root / "host.log", root / "consumer.log")
            self.assertEqual(result["status"], "NOT_RUN")
            self.assertFalse(result["checks"]["feed_delivered"]["pass"])

    def test_live_evidence_classifier_rejects_stale_logs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feed = root / "feed.log"
            host = root / "host.log"
            consumer = root / "consumer.log"
            screenshot = root / "nr-on.png"
            for path, content in (
                (feed, "frame 12 delivered\n"),
                (host, "frame 12 evaluated DLSS GPU 6.2 ms/frame\n"),
                (consumer, "standalone neural frame succeeded\n"),
            ):
                path.write_text(content, encoding="utf-8")
            screenshot.write_bytes(b"image")
            future = max(path.stat().st_mtime for path in (feed, host, consumer)) + 10
            result = classify_live_evidence(feed, host, consumer, [screenshot], run_started=future)
            self.assertEqual(result["status"], "PARTIAL")
            self.assertFalse(result["checks"]["logs_fresh"]["pass"])
            self.assertEqual(result["consumer"]["status"], "UNKNOWN")
class TestStagingAndRollbackIntegration(unittest.TestCase):
    def test_install_and_rollback_round_trip_restores_original(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            destination = root / "game"
            destination.mkdir()
            target = destination / "ReShade.ini"
            target.write_text("[GENERAL]\nOld=1\n", encoding="utf-8")
            source = root / "new.dll"
            source.write_bytes(b"new artifact")
            journal = root / "journal.json"
            copy_with_journal(
                [{"destination": "new.dll", "source": str(source)}],
                {"ReShade.ini": "[GENERAL]\nNew=2\n"},
                destination,
                journal,
                True,
            )
            self.assertEqual((destination / "new.dll").read_bytes(), b"new artifact")
            self.assertEqual((destination / "ReShade.ini").read_text(encoding="utf-8"), "[GENERAL]\nNew=2\n")
            from obdlss5.tools.obdlss5 import cmd_rollback

            result = SimpleNamespace(journal=str(journal), output=str(root / "rollback.json"))
            self.assertEqual(cmd_rollback(result), 0)
            self.assertEqual(target.read_text(encoding="utf-8"), "[GENERAL]\nOld=1\n")
            self.assertFalse((destination / "new.dll").exists())

    def test_rollback_preserves_user_modified_file_and_reports_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            destination = root / "game"
            destination.mkdir()
            source = root / "new.dll"
            source.write_bytes(b"new artifact")
            journal = root / "journal.json"
            copy_with_journal(
                [{"destination": "new.dll", "source": str(source)}],
                {},
                destination,
                journal,
                True,
            )
            (destination / "new.dll").write_bytes(b"user change")
            from obdlss5.tools.obdlss5 import cmd_rollback

            result = SimpleNamespace(journal=str(journal), output=str(root / "rollback.json"))
            self.assertEqual(cmd_rollback(result), 1)
            self.assertEqual((destination / "new.dll").read_bytes(), b"user change")
            report = json.loads((root / "rollback.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "CONFLICTS")
            self.assertTrue(report["conflicts"])

