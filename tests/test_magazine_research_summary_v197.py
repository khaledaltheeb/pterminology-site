import importlib.util
import json
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v197" / "magazine-phq-gad-instruction-emphasis-ar.json"
SCRIPT = ROOT / "scripts" / "publish_magazine_research_summary_v197.py"

spec = importlib.util.spec_from_file_location("magazine_v197", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def contrast_ratio(foreground: str, background: str) -> float:
    def luminance(value: str) -> float:
        value = value.lstrip("#")
        rgb = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in rgb]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)


class MagazineResearchSummaryV197Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(DATA.read_text(encoding="utf-8"))

    def fixture(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="magazine-v197-"))
        self.addCleanup(shutil.rmtree, site, True)
        (site / "magazine").mkdir(parents=True)
        (site / "api").mkdir()
        (site / "magazine" / "index.html").write_text(
            '''<!doctype html><html lang="ar" dir="rtl"><head><title>مجلة الصحة النفسية والبحث العلمي</title>
<meta name="description" content="منهج المجلة"></head><body><main>
<section class="institutional-card"><h2>حالة النشر الحالية</h2><p>لم تُنشر في هذه الحزمة ملخصات دراسات منفردة بعد. تبدأ المجلة بالمنهج والعقد التحريري، ثم تدخل كل دراسة في Queue مستقلة ولا تظهر كمنشورة قبل فحص المصدر والبوابات والنسخة الحية.</p></section>
<section class="notice"><h2>حالة الصفحة وحدودها</h2><p>مراجعة داخلية.</p></section>
</main></body></html>''',
            encoding="utf-8",
        )
        (site / "api" / "institutional-foundation-v192.json").write_text(
            json.dumps(
                {
                    "status": "built-not-published",
                    "published_research_summaries": 0,
                    "declared_partners": 0,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return site

    def test_content_contract_sources_and_editorial_transparency(self):
        data = module.load_content()
        self.assertEqual(data["version"], 197)
        self.assertEqual(data["publication_status"], "built-not-published")
        self.assertEqual(data["status"], "internally-reviewed")
        self.assertEqual(data["risk_level"], "moderate")
        self.assertGreaterEqual(len(data["sections"]), 9)
        self.assertGreaterEqual(len(data["key_numbers"]), 6)
        self.assertEqual(len(data["sources"]), 4)
        self.assertEqual(sum(source["type"] == "primary-study" for source in data["sources"]), 1)
        self.assertEqual(len({source["id"] for source in data["sources"]}), 4)
        self.assertEqual(len({source["url"] for source in data["sources"]}), 4)
        self.assertTrue(all(source["url"].startswith("https://") for source in data["sources"]))
        self.assertEqual(data["doi"], "10.1001/jamanetworkopen.2026.23952")
        self.assertEqual(data["pmid"], "42475096")
        self.assertEqual(data["trial_registration"], "NCT06956378")
        serialized = json.dumps(data, ensure_ascii=False)
        for phrase in [
            "لم يكن تحسنًا علاجيًا",
            "لا تقدم تشخيصًا",
            "لا تغيّر دواءً",
            "تعارض المصالح",
            "لا توجد مراجعة اختصاصية خارجية",
        ]:
            self.assertIn(phrase, serialized)
        for prohibited in [
            "يعالج الاكتئاب",
            "يشخص القلق نهائيًا",
            "يثبت أن المقياس غير صالح",
            "منشور حيًا",
        ]:
            self.assertNotIn(prohibited, serialized)

    def test_builds_long_accessible_article_with_complete_seo_and_schema(self):
        site = self.fixture()
        report = module.publish(site)
        page = site / "magazine" / self.data["slug"] / "index.html"
        self.assertTrue(page.is_file())
        text = page.read_text(encoding="utf-8")
        self.assertIn('<html lang="ar" dir="rtl">', text)
        self.assertEqual(text.count("<h1>"), 1)
        self.assertGreaterEqual(len(re.findall(r"<h2\b", text)), 14)
        self.assertEqual(text.count('rel="canonical"'), 1)
        self.assertIn('property="og:type" content="article"', text)
        self.assertIn('name="twitter:card" content="summary"', text)
        self.assertIn('rel="manifest"', text)
        self.assertIn('class="skip" href="#main"', text)
        self.assertIn("@media print", text)
        self.assertIn("@media(prefers-reduced-motion:reduce)", text)
        self.assertGreaterEqual(report["visible_words"], 1800)
        self.assertEqual(report["visible_words"], module.visible_word_count(text))

        schema_raw = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            text,
            re.S,
        ).group(1)
        schema = json.loads(schema_raw)
        graph = schema["@graph"]
        article = next(item for item in graph if item.get("@type") == "Article")
        breadcrumb = next(item for item in graph if item.get("@type") == "BreadcrumbList")
        self.assertEqual(article["headline"], self.data["title"])
        self.assertEqual(len(article["citation"]), 4)
        self.assertEqual(article["isBasedOn"], self.data["sources"][0]["url"])
        self.assertEqual(len(breadcrumb["itemListElement"]), 3)
        self.assertNotIn("datePublished", article)
        for link in self.data["internal_links"]:
            self.assertIn(f'href="{link["href"]}"', text)

    def test_numeric_results_are_precise_and_not_labeled_as_treatment_effects(self):
        site = self.fixture()
        module.publish(site)
        text = (site / "magazine" / self.data["slug"] / "index.html").read_text(encoding="utf-8")
        for expected in [
            "−2.60 نقطة",
            "−2.63 نقطة",
            "50% مقابل 9%",
            "65% مقابل 16%",
            "53% مقابل 12%",
            "55% مقابل 15%",
        ]:
            self.assertIn(expected, text)
        for required in [
            "لم يحدث علاج بين التطبيقين",
            "ليست بديلًا عن المقابلة",
            "لا ينبغي تعديل دواء",
            "التطبيق هاتفيًا",
            "النسخ العربية",
        ]:
            self.assertIn(required, text)
        for misleading in [
            "العلاج خفض PHQ-9",
            "تحسنت أعراض المشاركين خلال دقيقة",
            "أثبتت الدراسة بطلان PHQ-9",
            "ينبغي خفض الدرجات",
        ]:
            self.assertNotIn(misleading, text)

    def test_magazine_index_sitemap_and_reports_are_idempotent_and_truthful(self):
        site = self.fixture()
        first = module.publish(site)
        second = module.publish(site)
        index = (site / "magazine" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(index.count(module.CARD_START), 1)
        self.assertEqual(index.count(module.CARD_END), 1)
        self.assertEqual(index.count(f'/magazine/{self.data["slug"]}/'), 1)
        self.assertIn("لا يعد منشورًا حيًا", index)
        self.assertTrue(first["magazine_index_updated"])
        self.assertFalse(second["magazine_index_updated"])

        sitemap = ET.parse(site / module.SITEMAP_NAME).getroot()
        urls = [node.text for node in sitemap.findall("{*}url/{*}loc")]
        self.assertEqual(
            urls,
            [f'{module.BASE_URL}/magazine/{self.data["slug"]}/'],
        )
        report = json.loads(
            (site / "api" / "magazine-research-summary-v197.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "built-not-published")
        self.assertEqual(report["prepared_research_summaries"], 1)
        self.assertEqual(report["published_research_summaries"], 0)
        self.assertEqual(report["sitemap_urls"], 1)
        foundation = json.loads(
            (site / "api" / "institutional-foundation-v192.json").read_text(encoding="utf-8")
        )
        self.assertEqual(foundation["prepared_research_summaries"], 1)
        self.assertEqual(foundation["published_research_summaries"], 0)
        self.assertEqual(foundation["declared_partners"], 0)

    def test_visual_contrast_and_metadata_lengths(self):
        for foreground, background in [
            ("#173f45", "#f7fbfa"),
            ("#075d64", "#ffffff"),
            ("#7b2338", "#fff0f3"),
            ("#6a3d00", "#fff4db"),
        ]:
            self.assertGreaterEqual(
                contrast_ratio(foreground, background),
                4.5,
                (foreground, background),
            )
        self.assertGreaterEqual(len(self.data["description"]), 110)
        self.assertLessEqual(len(self.data["description"]), 180)
        self.assertLessEqual(len(self.data["seo_title"]), 65)


if __name__ == "__main__":
    unittest.main()
