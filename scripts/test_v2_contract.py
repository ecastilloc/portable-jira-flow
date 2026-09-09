#!/usr/bin/env python3
"""Fixture checks for the portable-jira-flow v2 specify and plan pipeline."""

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


class V2ContractPipelineTest(unittest.TestCase):
    def run_specify(
        self,
        ticket: str,
        source: Path,
        run_dir: Path,
        command: str = "specify",
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--skill-root",
                str(ROOT),
                command,
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


    def run_plan(
        self,
        ticket: str,
        run_dir: Path,
        command: str = "plan",
        expected_returncode: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--skill-root",
                str(ROOT),
                command,
                ticket,
                "--run-dir",
                str(run_dir),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected_returncode, result.stderr + result.stdout)
        return result

    def run_trace(self, run_dir: Path, command: str = "trace") -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--skill-root",
                str(ROOT),
                command,
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
            self.run_specify("ABC-301", FIXTURES / "feature-ticket.json", run_dir)
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
            self.assertEqual(state["invocation"]["primaryCommand"], "specify")
            self.assertEqual(state["coverage"]["summary"]["passed"], 0)
            self.assertFalse((Path(raw_tmp) / "ABC-301" / "run.json").exists())

    def test_bug_ticket_creates_preservation_failure_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-302"
            self.run_specify("ABC-302", FIXTURES / "bug-ticket.json", run_dir)
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
            self.run_specify("ABC-303", FIXTURES / "performance-ticket.json", run_dir)
            facts = self.read_json(run_dir, "behavior-facts.json")
            spec = self.read_json(run_dir, "behavior-spec.json")
            decisions = facts["openDecisions"] + spec["provenance"]["openDecisions"]
            self.assertTrue(any(decision["kind"] == "nfr_acceptance" for decision in decisions))
            self.assertTrue(any(scenario["type"] == "quality" and scenario["status"] == "unknown" for scenario in spec["scenarios"]))
            self.assertEqual(spec["coverage"]["summary"]["passed"], 0)

    def test_contradictory_source_blocks_confident_specify(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-304"
            self.run_specify("ABC-304", FIXTURES / "contradictory-source.md", run_dir)
            facts = self.read_json(run_dir, "behavior-facts.json")
            state = self.read_json(run_dir, "run.json")
            self.assertGreaterEqual(len(facts["contradictions"]), 1)
            self.assertEqual(state["stages"]["specify"]["status"], "blocked")
            self.assertNotIn("inspect", state["stages"])
            self.assertTrue(any(decision["kind"] == "contradiction" for decision in state["provenance"]["decisions"]))

    def test_attachment_instructions_are_reference_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-305"
            self.run_specify("ABC-305", FIXTURES / "attachment-instructions.txt", run_dir)
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
            self.run_specify("ABC-306", source, run_dir)
            source_pack = self.read_json(run_dir, "source-pack.json")
            facts = self.read_json(run_dir, "behavior-facts.json")
            spec = self.read_json(run_dir, "behavior-spec.json")
            self.assertEqual(source_pack["sources"][0]["kind"], "existing-test")
            self.assertEqual(source_pack["sources"][0]["authority"], "existing_tests")
            self.assertEqual(facts["businessRules"], [])
            self.assertEqual(spec["requirements"][0]["status"], "unknown")

    def test_trace_reports_stale_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            source = tmp / "feature-ticket.json"
            shutil.copyfile(FIXTURES / "feature-ticket.json", source)
            run_dir = tmp / "v2" / "ABC-307"
            self.run_specify("ABC-307", source, run_dir)
            data = json.loads(source.read_text(encoding="utf-8"))
            data["fields"]["description"] += " The system cannot assign a missing User."
            source.write_text(json.dumps(data, indent=2), encoding="utf-8")
            trace = self.run_trace(run_dir)
            self.assertIn("stale_sources=1", trace.stdout)

    def test_legacy_v2_command_words_remain_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-308"
            specify = self.run_specify("ABC-308", FIXTURES / "feature-ticket.json", run_dir, command="inspect")
            trace = self.run_trace(run_dir, command="status")
            state = self.read_json(run_dir, "run.json")
            self.assertIn("[OK] v2 specify", specify.stdout)
            self.assertIn("[OK] v2 trace", trace.stdout)
            self.assertEqual(state["invocation"]["primaryCommand"], "specify")

    def test_plan_pins_fresh_spec_and_creates_task_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-309"
            self.run_specify("ABC-309", FIXTURES / "feature-ticket.json", run_dir)
            plan = self.run_plan("ABC-309", run_dir)
            plan_data = self.read_json(run_dir, "implementation-plan.json")
            state = self.read_json(run_dir, "run.json")

            self.assertIn("[OK] v2 plan", plan.stdout)
            self.assertEqual(plan_data["readiness"]["status"], "ready")
            self.assertGreaterEqual(len(plan_data["implementationTasks"]), 1)
            self.assertTrue(all(task["scenarioIds"] for task in plan_data["implementationTasks"]))
            self.assertEqual(state["invocation"]["primaryCommand"], "plan")
            self.assertEqual(state["stages"]["plan"]["status"], "complete")
            self.assertEqual(state["stages"]["plan"]["implementationPlanDigest"], plan_data["digest"])
            self.assertFalse((Path(raw_tmp) / "ABC-309" / "run.json").exists())

    def test_plan_blocks_stale_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            source = tmp / "feature-ticket.json"
            shutil.copyfile(FIXTURES / "feature-ticket.json", source)
            run_dir = tmp / "v2" / "ABC-310"
            self.run_specify("ABC-310", source, run_dir)
            data = json.loads(source.read_text(encoding="utf-8"))
            data["fields"]["description"] += " The system cannot assign a missing User."
            source.write_text(json.dumps(data, indent=2), encoding="utf-8")

            plan = self.run_plan("ABC-310", run_dir, expected_returncode=1)
            plan_data = self.read_json(run_dir, "implementation-plan.json")
            state = self.read_json(run_dir, "run.json")

            self.assertIn("[BLOCKED] v2 plan", plan.stdout)
            self.assertEqual(plan_data["readiness"]["status"], "blocked")
            self.assertIn("SRC-001", plan_data["readiness"]["freshness"]["staleSources"])
            self.assertEqual(state["stages"]["plan"]["status"], "blocked")
            self.assertEqual(state["nextAction"]["command"], "portable-jira-flow-v2 specify ABC-310")

    def test_plan_blocks_contradictory_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-311"
            self.run_specify("ABC-311", FIXTURES / "contradictory-source.md", run_dir)
            self.run_plan("ABC-311", run_dir, expected_returncode=1)
            plan_data = self.read_json(run_dir, "implementation-plan.json")
            self.assertTrue(any(blocker["kind"] == "contradiction" for blocker in plan_data["readiness"]["blockers"]))
            self.assertGreaterEqual(plan_data["readiness"]["contradictionCount"], 1)

    def test_plan_blocks_open_nfr_decision_before_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-312"
            self.run_specify("ABC-312", FIXTURES / "performance-ticket.json", run_dir)
            self.run_plan("ABC-312", run_dir, expected_returncode=1)
            plan_data = self.read_json(run_dir, "implementation-plan.json")
            blocking = [task for task in plan_data["decisionTasks"] if task["blocksImplementation"]]
            self.assertTrue(any(task["decisionKind"] == "nfr_acceptance" for task in blocking))
            self.assertTrue(any(blocker["kind"] == "blocking_open_decisions" for blocker in plan_data["readiness"]["blockers"]))

    def test_v2_start_alias_routes_to_plan_without_v1_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            run_dir = Path(raw_tmp) / "v2" / "ABC-313"
            self.run_specify("ABC-313", FIXTURES / "feature-ticket.json", run_dir)
            start = self.run_plan("ABC-313", run_dir, command="start")
            state = self.read_json(run_dir, "run.json")

            self.assertIn("[OK] v2 plan", start.stdout)
            self.assertEqual(state["invocation"]["primaryCommand"], "plan")
            self.assertIn("plan", state["stages"])
            self.assertNotIn("start", state["stages"])
            self.assertFalse((Path(raw_tmp) / "ABC-313" / "run.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
