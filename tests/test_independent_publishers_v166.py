import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_independent_publishers_v166 import validate


ROOT = Path(__file__).resolve().parents[1]


class IndependentPublishersContractTests(unittest.TestCase):
    def test_repository_contract_is_valid(self):
        report = validate(ROOT)
        self.assertEqual(report["errors"], [], report)
        self.assertEqual(report["publisher_count"], 10)
        self.assertEqual(report["queue_item_count"], 10)
        self.assertEqual({item["issue"] for item in report["publishers"]}, set(range(96, 106)))

    def make_fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "data").mkdir(parents=True)
        shutil.copy2(ROOT / "data" / "independent-publishers-v166.json", root / "data" / "independent-publishers-v166.json")
        for queue in (ROOT / "content" / "publishers").glob("*/queue.json"):
            destination = root / queue.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(queue, destination)
        return temp, root

    def test_missing_queue_is_blocked(self):
        temp, root = self.make_fixture()
        try:
            (root / "content" / "publishers" / "women" / "queue.json").unlink()
            report = validate(root)
            self.assertIn("missing_queue:publisher-03-women", report["errors"])
        finally:
            temp.cleanup()

    def test_duplicate_slug_across_publishers_is_blocked(self):
        temp, root = self.make_fixture()
        try:
            article_path = root / "content" / "publishers" / "articles" / "queue.json"
            question_path = root / "content" / "publishers" / "questions" / "queue.json"
            article = json.loads(article_path.read_text(encoding="utf-8"))
            question = json.loads(question_path.read_text(encoding="utf-8"))
            question["items"][0]["slug"] = article["items"][0]["slug"]
            question_path.write_text(json.dumps(question, ensure_ascii=False, indent=2), encoding="utf-8")
            report = validate(root)
            self.assertIn(f"duplicate_slug:{article['items'][0]['slug']}", report["errors"])
        finally:
            temp.cleanup()

    def test_content_type_cannot_cross_publisher_boundary(self):
        temp, root = self.make_fixture()
        try:
            queue_path = root / "content" / "publishers" / "dictionary" / "queue.json"
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            queue["items"][0]["target_content_type"] = "article"
            queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
            report = validate(root)
            self.assertIn("content_type_outside_publisher:publisher-05-dictionary:article", report["errors"])
        finally:
            temp.cleanup()

    def test_published_status_requires_separate_live_evidence_warning(self):
        temp, root = self.make_fixture()
        try:
            queue_path = root / "content" / "publishers" / "guides" / "queue.json"
            queue = json.loads(queue_path.read_text(encoding="utf-8"))
            queue["items"][0]["status"] = "published"
            queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
            report = validate(root)
            self.assertIn(
                "published_item_requires_separate_live_evidence:guide-first-therapy-session-preparation",
                report["warnings"],
            )
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
