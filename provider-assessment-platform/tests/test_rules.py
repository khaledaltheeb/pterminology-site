import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.rules import (  # noqa: E402
    EvaluationContext,
    PathwayConfigurationError,
    PathwayEngine,
    RuleEvaluator,
    TruthValue,
)


BASE_PATHWAY = {
    "id": "developmental-intake",
    "entry": {"start_node": "safety-gate"},
    "global_rules": {"prohibit_single_tool_conclusion": True},
    "nodes": [
        {
            "id": "safety-gate",
            "required_roles": ["case_lead", "clinician"],
            "transitions": [
                {
                    "id": "continue-intake",
                    "priority": 1,
                    "condition": {
                        "all": [
                            {"eq": ["safety.level", "none_identified"]},
                            {"exists": "consent.obtained_at"},
                        ]
                    },
                    "destination": "multi-source-check",
                    "explanation": {
                        "ar": "تم اجتياز بوابة السلامة والموافقة للانتقال إلى فحص المصادر.",
                        "en": "Safety and consent gates passed; continue to source review.",
                    },
                    "source_ids": ["policy-safety-001"],
                    "requires_human_confirmation": False,
                    "blocks_automation": False,
                }
            ],
        },
        {
            "id": "multi-source-check",
            "required_roles": ["case_lead", "clinician"],
            "transitions": [
                {
                    "id": "send-team-review",
                    "priority": 1,
                    "condition": {
                        "all": [
                            {"count_gte": ["sources", 2]},
                            {"eq": ["assessment.validity", "valid"]},
                            {"confirmed": "multi-source-check:send-team-review"},
                        ]
                    },
                    "destination": "team-review",
                    "explanation": {
                        "ar": "توجد مصادر مستقلة ونتيجة صالحة؛ يلزم اعتماد المراجع البشري.",
                        "en": "Independent sources and a valid result are present; human review is required.",
                    },
                    "source_ids": ["policy-multisource-001"],
                    "requires_human_confirmation": True,
                    "blocks_automation": True,
                }
            ],
        },
        {
            "id": "team-review",
            "required_roles": ["clinical_reviewer"],
            "transitions": [],
        },
    ],
}


class RuleEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = RuleEvaluator()

    def test_missing_field_is_unknown_not_false(self) -> None:
        result = self.evaluator.evaluate(
            {"eq": ["assessment.score", 10]},
            EvaluationContext(data={}),
        )
        self.assertEqual(result.truth, TruthValue.UNKNOWN)
        self.assertEqual(result.evidence[0].path, "assessment.score")

    def test_all_propagates_unknown_when_no_false_exists(self) -> None:
        result = self.evaluator.evaluate(
            {"all": [{"eq": ["known", 1]}, {"eq": ["missing", 2]}]},
            EvaluationContext(data={"known": 1}),
        )
        self.assertEqual(result.truth, TruthValue.UNKNOWN)

    def test_any_returns_true_even_with_other_unknown_operand(self) -> None:
        result = self.evaluator.evaluate(
            {"any": [{"eq": ["known", 1]}, {"eq": ["missing", 2]}]},
            EvaluationContext(data={"known": 1}),
        )
        self.assertEqual(result.truth, TruthValue.TRUE)


class PathwayEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = PathwayEngine(BASE_PATHWAY)

    def test_urgent_safety_level_stops_routine_pathway(self) -> None:
        decision = self.engine.evaluate_node(
            "safety-gate",
            EvaluationContext(
                data={"safety": {"level": "urgent"}},
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.destination, "urgent-referral")
        self.assertTrue(decision.automation_blocked)
        self.assertTrue(decision.requires_human_confirmation)

    def test_valid_safety_and_consent_continue(self) -> None:
        decision = self.engine.evaluate_node(
            "safety-gate",
            EvaluationContext(
                data={
                    "safety": {"level": "none_identified"},
                    "consent": {"obtained_at": "2026-07-23T10:00:00+03:00"},
                },
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.truth, TruthValue.TRUE)
        self.assertEqual(decision.destination, "multi-source-check")
        self.assertFalse(decision.automation_blocked)

    def test_missing_consent_blocks_routing_and_lists_field(self) -> None:
        decision = self.engine.evaluate_node(
            "safety-gate",
            EvaluationContext(
                data={"safety": {"level": "none_identified"}},
                actor_roles=frozenset({"case_lead"}),
            ),
        )
        self.assertEqual(decision.truth, TruthValue.UNKNOWN)
        self.assertIn("consent.obtained_at", decision.missing_fields)
        self.assertTrue(decision.automation_blocked)

    def test_human_confirmation_is_required_for_team_review(self) -> None:
        context = EvaluationContext(
            data={
                "safety": {"level": "none_identified"},
                "sources": [{"id": "parent"}, {"id": "teacher"}],
                "assessment": {"validity": "valid"},
            },
            actor_roles=frozenset({"case_lead"}),
            human_confirmations=frozenset({"multi-source-check:send-team-review"}),
        )
        decision = self.engine.evaluate_node("multi-source-check", context)
        self.assertEqual(decision.destination, "team-review")
        self.assertTrue(decision.requires_human_confirmation)
        self.assertTrue(decision.automation_blocked)

    def test_actor_without_required_role_is_rejected(self) -> None:
        with self.assertRaises(PermissionError):
            self.engine.evaluate_node(
                "safety-gate",
                EvaluationContext(data={"safety": {"level": "none_identified"}}),
            )

    def test_pathway_without_single_tool_prohibition_is_invalid(self) -> None:
        invalid = dict(BASE_PATHWAY)
        invalid["global_rules"] = {"prohibit_single_tool_conclusion": False}
        with self.assertRaises(PathwayConfigurationError):
            PathwayEngine(invalid)


if __name__ == "__main__":
    unittest.main()
