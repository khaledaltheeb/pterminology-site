import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.runtime import EvaluationContext, PathwayEngine  # noqa: E402


class AllPathwaysSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pathway_files = sorted((PROJECT_ROOT / "pathways").glob("*.json"))
        cls.pathways = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in cls.pathway_files
        ]

    def test_expected_foundation_pathways_are_present(self) -> None:
        ids = {pathway["id"] for pathway in self.pathways}
        self.assertTrue(
            {
                "developmental-intake",
                "autism-under19",
                "intellectual-disability",
                "adhd",
                "spoken-language-3-21",
                "reading-writing-learning",
            }.issubset(ids)
        )

    def test_emergency_state_overrides_each_pathway_start(self) -> None:
        for pathway in self.pathways:
            with self.subTest(pathway=pathway["id"]):
                engine = PathwayEngine(pathway)
                start_id = pathway["entry"]["start_node"]
                start_node = next(node for node in pathway["nodes"] if node["id"] == start_id)
                role = start_node["required_roles"][0]
                decision = engine.evaluate_node(
                    start_id,
                    EvaluationContext(
                        data={"safety": {"level": "emergency"}},
                        actor_roles=frozenset({role}),
                    ),
                )
                self.assertEqual(decision.destination, "urgent-referral")
                self.assertEqual(decision.transition_id, "system-safety-hold")
                self.assertTrue(decision.automation_blocked)
                self.assertTrue(decision.requires_human_confirmation)

    def test_empty_evidence_never_reaches_report_or_closure(self) -> None:
        for pathway in self.pathways:
            with self.subTest(pathway=pathway["id"]):
                engine = PathwayEngine(pathway)
                node = next(node for node in pathway["nodes"] if node["id"] == "evidence-collection")
                role = node["required_roles"][0]
                decision = engine.evaluate_node(
                    "evidence-collection",
                    EvaluationContext(data={}, actor_roles=frozenset({role})),
                )
                self.assertNotIn(decision.destination, {"professional-report", "closed"})
                self.assertTrue(decision.automation_blocked)

    def test_all_high_impact_transitions_are_human_gated(self) -> None:
        high_impact = {"multidisciplinary-review", "professional-report", "closed"}
        for pathway in self.pathways:
            for node in pathway["nodes"]:
                for transition in node["transitions"]:
                    if transition["destination"] not in high_impact:
                        continue
                    with self.subTest(
                        pathway=pathway["id"],
                        node=node["id"],
                        transition=transition["id"],
                    ):
                        self.assertTrue(transition["requires_human_confirmation"])
                        self.assertTrue(transition["blocks_automation"])

    def test_no_pathway_embeds_score_cutoffs(self) -> None:
        prohibited_keys = {"diagnostic_cutoff", "automatic_diagnosis", "auto_eligibility"}
        for pathway in self.pathways:
            serialized = json.dumps(pathway, ensure_ascii=False)
            for key in prohibited_keys:
                with self.subTest(pathway=pathway["id"], key=key):
                    self.assertNotIn(f'"{key}"', serialized)


if __name__ == "__main__":
    unittest.main()
