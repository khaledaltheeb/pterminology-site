import json, tempfile, unittest
from datetime import date
from pathlib import Path
from scripts.audit_content_freshness_v180 import audit, write_reports

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.root=Path(self.t.name); (self.root/'content').mkdir()
    def tearDown(self): self.t.cleanup()
    def write(self,name,payload): (self.root/'content'/name).write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
    def test_high_risk_blocker(self):
        self.write('x.json',{'title':'ص','description':'م','status':'published','risk_level':'high','review_status':'needs-specialist-review','sources':[]})
        f=audit(self.root,date(2026,7,23))[0]; self.assertEqual(f.decision,'fix-before-publish'); self.assertIn('high_risk_without_structured_sources',f.codes)
    def test_current(self):
        self.write('x.json',{'title':'ص','description':'م','status':'reviewed','risk_level':'high','review_status':'internally-reviewed','reviewed_at':'2026-07-01','sources':[{'verified_at':'2026-06-01'}]})
        self.assertEqual(audit(self.root,date(2026,7,23))[0].decision,'current')
    def test_stale_needs_update(self):
        self.write('x.json',{'title':'ص','summary':'م','status':'reviewed','risk_level':'moderate','review_status':'internally-reviewed','reviewed_at':'2024-01-01','sources':[{'verified_at':'2022-01-01'}]})
        f=audit(self.root,date(2026,7,23))[0]; self.assertEqual(f.decision,'needs-update'); self.assertIn('review_overdue',f.codes)
    def test_html_uses_actual_path_and_reports_relative_path(self):
        site=self.root/'_site'; site.mkdir(); (site/'index.html').write_text('<html><head><title></title></head></html>',encoding='utf-8')
        f=audit(self.root,date(2026,7,23))[0]; self.assertEqual(f.source_file,'_site/index.html'); self.assertEqual(f.decision,'fix-before-publish')
    def test_reports_are_advisory(self):
        self.write('x.json',{'title':'ص','description':'م','status':'draft','risk_level':'low'})
        findings=audit(self.root,date(2026,7,23)); j=self.root/'r.json'; c=self.root/'r.csv'; write_reports(findings,j,c,date(2026,7,23),365,730)
        self.assertIn('never proves specialist review or live publication',json.loads(j.read_text(encoding='utf-8'))['publication_rule']); self.assertTrue(c.exists())
if __name__=='__main__': unittest.main()
