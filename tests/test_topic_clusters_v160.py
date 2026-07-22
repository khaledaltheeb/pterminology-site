import copy
import json
import unittest
from pathlib import Path

from scripts.validate_topic_clusters_v160 import extract_literal_assignment, validate_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / "data" / "topic-cluster-registry-v160.json").read_text(encoding="utf-8"))
DOMAINS = extract_literal_assignment(ROOT / "scripts" / "scale_site_v8.py", "DOMAINS")
FACETS = extract_literal_assignment(ROOT / "scripts" / "scale_site_v8.py", "FACETS")


class TopicClusterRegistryV160Tests(unittest.TestCase):
    def test_current_anxiety_registry_matches_legacy_generator(self):
        report = validate_registry(REGISTRY, DOMAINS, FACETS)
        self.assertEqual(report["error_count"], 0, report["errors"])
        self.assertEqual(report["clusters"], 1)
        self.assertEqual(report["nodes"], 14)
        self.assertEqual(report["legacy_concepts_mapped"], 15)
        self.assertTrue(report["policy"]["advisory_and_planning_only"])
        self.assertFalse(report["policy"]["automatic_url_changes"])

    def test_duplicate_intent_is_rejected(self):
        registry = copy.deepcopy(REGISTRY)
        registry["clusters"][0]["nodes"][1]["intent_key"] = registry["clusters"][0]["nodes"][0]["intent_key"]
        report = validate_registry(registry, DOMAINS, FACETS)
        self.assertIn("duplicate-intent", {item["code"] for item in report["errors"]})

    def test_legacy_range_and_hubs_are_derived_not_guessed(self):
        registry = copy.deepcopy(REGISTRY)
        registry["clusters"][0]["legacy_generation"]["concept_end"] = 29
        registry["clusters"][0]["legacy_generation"]["legacy_hubs"] = ["/pterminology-site/hubs/hub-001/"]
        report = validate_registry(registry, DOMAINS, FACETS)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("legacy-range-mismatch", codes)
        self.assertIn("legacy-hub-mismatch", codes)

    def test_high_risk_node_requires_source_and_review_plan(self):
        registry = copy.deepcopy(REGISTRY)
        node = registry["clusters"][0]["nodes"][2]
        node["minimum_source_ids"] = 1
        node["review_requirement"] = "needs-specialist-review"
        report = validate_registry(registry, DOMAINS, FACETS)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("insufficient-source-plan", codes)
        self.assertIn("insufficient-review-plan", codes)

    def test_premature_publication_or_canonical_change_is_rejected(self):
        registry = copy.deepcopy(REGISTRY)
        registry["clusters"][0]["pillar"]["publication_status"] = "published"
        registry["clusters"][0]["legacy_generation"]["canonical_policy"] = "replace-now"
        report = validate_registry(registry, DOMAINS, FACETS)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("premature-publication-claim", codes)
        self.assertIn("unsafe-canonical-policy", codes)

    def test_unassigned_legacy_concepts_must_match_exact_complement(self):
        registry = copy.deepcopy(REGISTRY)
        registry["clusters"][0]["unassigned_legacy_concepts"] = []
        report = validate_registry(registry, DOMAINS, FACETS)
        self.assertIn("unassigned-concept-mismatch", {item["code"] for item in report["errors"]})


if __name__ == "__main__":
    unittest.main()
