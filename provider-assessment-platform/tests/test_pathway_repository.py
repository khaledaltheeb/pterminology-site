import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.rules import EvaluationContext, PathwayEngine, TruthValue  # noqa: E402
from tools.validate_repository import validate_catalog, validate_pathway  # noqa: E402


PATHWAY_PATH = PROJECT_ROOT / "pathways" / "developmental-intake.v0.1.0.json"
CATALOG_PATH = PROJECT_ROOT / "registry" / "assessment-catalog.v0.1.0.json"


class GovernedRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pathway = json.loads(PATHWAY_PATH.read_text(encoding="utf-8"))
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        cls.engine = PathwayEngine(cls.pathway)

    def test_repository_validator_accepts_current_drafts(self) -> None:
        validate_catalog(CATALOG_PATH)
        validate_pathway(PATHWAY_PATH)

    def test_all_catalog_entries_are_disabled_by_default(self) -> None:
        self.assertFalse(self.catalog["rules"]["default_enabled"])
        self.assertTrue(self.catalog["entries"])
        self.assertTrue(all(entry["enabled"] is False for entry in self.catalog["entries"]))

    def test_routine_safety_gate_requires_consent(self) -> None:
        decision = self.engine.evaluate_node(
            "safety-gate",
            EvaluationContext(
                data={
                    "safety": {"level": "none_identified"},
                    "consent": {
                        "obtained_at": "2026-07-23T12:00:00+03:00",
                        "withdrawal_explained": True,
                    },
                },
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.truth, TruthValue.TRUE)
        self.assertEqual(decision.destination, "intake-completeness")

    def test_missing_consent_is_unknown_and_blocks_progress(self) -> None:
        decision = self.engine.evaluate_node(
            "safety-gate",
            EvaluationContext(
                data={"safety": {"level": "none_identified"}},
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.truth, TruthValue.UNKNOWN)
        self.assertIn("consent.obtained_at", decision.missing_fields)
        self.assertIn("consent.withdrawal_explained", decision.missing_fields)
        self.assertTrue(decision.automation_blocked)

    def test_system_safety_override_precedes_normal_rules(self) -> None:
        decision = self.engine.evaluate_node(
            "intake-completeness",
            EvaluationContext(
                data={"safety": {"level": "emergency"}},
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.destination, "urgent-referral")
        self.assertEqual(decision.transition_id, "system-safety-hold")
        self.assertTrue(decision.automation_blocked)

    def test_sensory_access_signal_routes_to_specialist_review(self) -> None:
        decision = self.engine.evaluate_node(
            "sensory-access-gate",
            EvaluationContext(
                data={
                    "safety": {"level": "none_identified"},
                    "subject": {
                        "sensory_access": {
                            "hearing_status": "suspected_difficulty",
                            "vision_status": "typical",
                            "motor_access": "independent",
                        }
                    },
                },
                actor_roles=frozenset({"clinician"}),
            ),
        )
        self.assertEqual(decision.destination, "sensory-access-assessment")
        self.assertTrue(decision.requires_human_confirmation)
        self.assertTrue(decision.automation_blocked)

    def test_multidomain_plan_needs_multiple_domains_and_tools(self) -> None:
        decision = self.engine.evaluate_node(
            "multidomain-plan",
            EvaluationContext(
                data={
                    "safety": {"level": "none_identified"},
                    "assessment_plan": {
                        "domains": ["language", "adaptive"],
                        "tools": ["tool-a", "tool-b"],
                        "approved_by": "reviewer-1",
                    },
                },
                actor_roles=frozenset({"case_lead"}),
                human_confirmations=frozenset({"multidomain-plan:plan-approved"}),
            ),
        )
        self.assertEqual(decision.destination, "evidence-collection")
        self.assertTrue(decision.automation_blocked)

    def test_unresolved_material_conflict_routes_to_conflict_review(self) -> None:
        decision = self.engine.evaluate_node(
            "evidence-collection",
            EvaluationContext(
                data={
                    "safety": {"level": "none_identified"},
                    "sources": [{"id": "parent"}, {"id": "teacher"}],
                    "completed_assessments": [{"id": "a"}, {"id": "b"}],
                    "direct_observation": {"completed": True},
                    "quality": {"material_conflict_unresolved": True},
                },
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.destination, "conflict-review")
        self.assertTrue(decision.automation_blocked)

    def test_single_assessment_cannot_reach_team_review(self) -> None:
        decision = self.engine.evaluate_node(
            "evidence-collection",
            EvaluationContext(
                data={
                    "safety": {"level": "none_identified"},
                    "sources": [{"id": "parent"}, {"id": "teacher"}],
                    "completed_assessments": [{"id": "only-one"}],
                    "direct_observation": {"completed": True},
                    "quality": {"material_conflict_unresolved": False},
                },
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertIsNone(decision.destination)
        self.assertNotEqual(decision.truth, TruthValue.TRUE)
        self.assertTrue(decision.automation_blocked)


if __name__ == "__main__":
    unittest.main()
