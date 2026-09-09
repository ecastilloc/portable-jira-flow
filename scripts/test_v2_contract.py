#!/usr/bin/env python3
"""Fixture checks for the portable-jira-flow v2 inspect pipeline."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "v2_contract.py"
FIXTURES = ROOT / "evals" / "fixtures" / "v2"


class V2InspectTest(unittest.TestCase):
    def run_inspect(self, ticket: str, source: Path, run_dir: Path) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--skill-root",
                str(ROOT),
                "inspect",
                ticket,
                "--run-dir",
                str(run_dir),
                "--source",
                str(source),
                "--force",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def run_status(self, run_dir: Path) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--skill-root",
                str(ROOT),
                "status",
                "--run-dir",
                str(run_dir),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def read_json(self, run_dir: Path, name: str) -> dict:
        path = run_dir / name
        self.assertTrue(path.exists(), f"missing {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_feature_ticket_creates_main_scenario_and_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-301"
            self.run_inspect("ABC-301", FIXTURES / "feature-ticket.json", run_dir)
            source_pack = self.read_json(run_dir, "source-pack.json")
            facts = self.read_json(run_dir, "behavior-facts.json")
            spec = self.read_json(run_dir, "behavior-spec.json")
            state = self.read_json(run_dir, "run.json")

            self.assertEqual(source_pack["schemaVersion"], "1.0.0")
            self.assertEqual(facts["sourcePackDigest"], source_pack["digest"])
            self.assertGreaterEqual(len(spec["requirements"]), 1)
            self.assertTrue(any(scenario["id"].endswith("-MAIN") for scenario in spec["scenarios"]))
            self.assertEqual(state["schemaVersion"], "2.0.0")
            self.assertEqual(state["workflowVersion"], "v2")
            self.assertEqual(state["coverage"]["summary"]["passed"], 0)
            self.assertFalse((Path(raw_tmp) / "ABC-301" / "run.json").exists())

    def test_bug_ticket_creates_preservation_failure_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-302"
            self.run_inspect("ABC-302", FIXTURES / "bug-ticket.json", run_dir)
            spec = self.read_json(run_dir, "behavior-spec.json")
            alternatives = [scenario for scenario in spec["scenarios"] if scenario["type"] == "alternative"]
            self.assertTrue(alternatives)
            combined = "\n".join(
                f"{scenario.get('expectedResult', '')}\n{scenario.get('failureGuarantee', '')}" for scenario in alternatives
            ).lower()
            self.assertTrue("preserv" in combined or "unchanged" in combined, combined)
            self.assertEqual(spec["coverage"]["summary"]["passed"], 0)

    def test_performance_ticket_without_threshold_keeps_nfr_open(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-303"
            self.run_inspect("ABC-303", FIXTURES / "performance-ticket.json", run_dir)
            facts = self.read_json(run_dir, "behavior-facts.json")
            spec = self.read_json(run_dir, "behavior-spec.json")
            decisions = facts["openDecisions"] + spec["provenance"]["openDecisions"]
            self.assertTrue(any(decision["kind"] == "nfr_acceptance" for decision in decisions))
            self.assertTrue(any(scenario["type"] == "quality" and scenario["status"] == "unknown" for scenario in spec["scenarios"]))
            self.assertEqual(spec["coverage"]["summary"]["passed"], 0)

    def test_contradictory_source_blocks_confident_inspect(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-304"
            self.run_inspect("ABC-304", FIXTURES / "contradictory-source.md", run_dir)
            facts = self.read_json(run_dir, "behavior-facts.json")
            state = self.read_json(run_dir, "run.json")
            self.assertGreaterEqual(len(facts["contradictions"]), 1)
            self.assertEqual(state["stages"]["inspect"]["status"], "blocked")
            self.assertTrue(any(decision["kind"] == "contradiction" for decision in state["provenance"]["decisions"]))

    def test_attachment_instructions_are_reference_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-305"
            self.run_inspect("ABC-305", FIXTURES / "attachment-instructions.txt", run_dir)
            source_pack = self.read_json(run_dir, "source-pack.json")
            self.assertEqual(source_pack["sources"][0]["kind"], "attachment")
            self.assertEqual(source_pack["sources"][0]["instructionPolicy"], "reference-only")
            self.assertIs(source_pack["sources"][0]["executableInstructions"], False)
            self.assertIn("deploy the application", source_pack["sources"][0]["content"])

    def test_existing_tests_are_current_behavior_evidence_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            source = tmp / "existing-test.spec"
            source.write_text(
                "The test should allow archived Tasks to be reassigned when the fixture is active.",
                encoding="utf-8",
            )
            run_dir = tmp / "v2" / "ABC-306"
            self.run_inspect("ABC-306", source, run_dir)
            source_pack = self.read_json(run_dir, "source-pack.json")
            facts = self.read_json(run_dir, "behavior-facts.json")
            spec = self.read_json(run_dir, "behavior-spec.json")
            self.assertEqual(source_pack["sources"][0]["kind"], "existing-test")
            self.assertEqual(source_pack["sources"][0]["authority"], "existing_tests")
            self.assertEqual(facts["businessRules"], [])
            self.assertEqual(spec["requirements"][0]["status"], "unknown")

    def test_status_reports_stale_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            source = tmp / "feature-ticket.json"
            shutil.copyfile(FIXTURES / "feature-ticket.json", source)
            run_dir = tmp / "v2" / "ABC-307"
            self.run_inspect("ABC-307", source, run_dir)
            data = json.loads(source.read_text(encoding="utf-8"))
            data["fields"]["description"] += " The system cannot assign a missing User."
            source.write_text(json.dumps(data, indent=2), encoding="utf-8")
            status = self.run_status(run_dir)
            self.assertIn("stale_sources=1", status.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
