from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v18" / "care-guides-autism-ar.json"
PUBLISHER = ROOT / "scripts" / "publish_care_guides_v21.py"
LINKER = ROOT / "scripts" / "link_care_guides_v21.py"


class AutismFamilyGuideV73Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads(DATA.read_text(encoding="utf-8"))
        cls.payload = payload
        cls.guide = payload["guides"][0]
        cls.serialized = json.dumps(cls.guide, ensure_ascii=False)

    def test_identity_review_status_and_depth(self) -> None:
        guide = self.guide
        self.assertEqual(self.payload["version"], 73)
        self.assertEqual(self.payload["language"], "ar")
        self.assertEqual(guide["id"], "guide.autism.family-practical")
        self.assertEqual(guide["slug"], "autism-family-practical-guide")
        self.assertEqual(guide["review_status"], "needs-specialist-review")
        required = {
            "understanding",
            "what_the_person_may_feel",
            "strengths_and_differences",
            "communication_plan",
            "sensory_plan",
            "do",
            "avoid",
            "home_plan",
            "school_plan",
            "transition_protocol",
            "meltdown_protocol",
            "wandering_protocol",
            "sleep_plan",
            "food_plan",
            "medication_awareness",
            "when_to_seek_help",
            "caregiver_plan",
        }
        self.assertTrue(required.issubset(guide))
        self.assertGreaterEqual(sum(len(guide[key]) for key in required), 80)
        self.assertGreaterEqual(len(guide["sources"]), 4)

    def test_situation_protocols_are_actionable(self) -> None:
        for key in ("transition_protocol", "meltdown_protocol", "wandering_protocol"):
            text = " ".join(self.guide[key])
            self.assertIn("ماذا أرى", text)
            self.assertIn("ماذا أفعل", text)
            self.assertIn("أتجنب", text)
            self.assertIn("مختص", text)
            self.assertIn("طارئة", text)

    def test_safety_non_diagnostic_and_dignity_language(self) -> None:
        text = self.serialized
        required_phrases = (
            "التشخيص مهني",
            "لا توقف الدواء",
            "خدمات الطوارئ المحلية",
            "يشفي التوحد",
            "راجع الألم",
            "احترم رفض التواصل البصري",
            "الهدف ليس جعل الشخص يبدو غير متوحد",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, text)
        forbidden = (
            "جرعة موصى بها",
            "يعالج التوحد نهائيًا",
            "تشخيصك هو",
            "اضبطه بالقوة",
        )
        for phrase in forbidden:
            self.assertNotIn(phrase, text)

    def test_sources_are_unique_https_and_institutional(self) -> None:
        sources = self.guide["sources"]
        urls = [source["url"] for source in sources]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith("https://") for url in urls))
        hosts = " ".join(urls)
        for host in ("who.int", "nice.org.uk", "cdc.gov"):
            self.assertIn(host, hosts)

    def test_publisher_and_linker_integrate_the_guide(self) -> None:
        publisher = PUBLISHER.read_text(encoding="utf-8")
        linker = LINKER.read_text(encoding="utf-8")
        self.assertIn("care-guides-autism-ar.json", publisher)
        self.assertIn("Expected 8 validated guides", publisher)
        self.assertIn('"autism_guide_sections"', publisher)
        self.assertIn("autism-family-practical-guide", linker)
        self.assertIn("autism-family-journey-v73", linker)
        self.assertIn("autism-encyclopedia-journey-v73", linker)
        self.assertIn("autism-related-journey-v73", linker)
        self.assertIn("اضطراب%20طيف%20التوحد", linker)
        self.assertIn("@media print", publisher)
        self.assertEqual(len(re.findall(r'ROOT / "content/v18/care-guides-[^"]+\.json"', publisher)), 2)


if __name__ == "__main__":
    unittest.main()
