import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'content/v160/blog-anxiety-ar.json'
PUBLISHER=ROOT/'scripts/publish_blog_v160.py'
FINALIZER=ROOT/'scripts/finalize_blog_links_v160.py'

class BlogV160Tests(unittest.TestCase):
    def test_content_depth_safety_and_sources(self):
        payload=json.loads(DATA.read_text(encoding='utf-8')); article=payload['articles'][0]
        visible=' '.join(p for section in article['sections'] for p in section['paragraphs'])
        self.assertGreaterEqual(len(visible.split()),650)
        self.assertGreaterEqual(len(article['sections']),7)
        self.assertEqual(article['review_status'],'needs-specialist-review')
        self.assertGreaterEqual(len(article['sources']),2)
        for source in article['sources']:
            self.assertTrue(source['url'].startswith('https://www.who.int/'))
            self.assertTrue(source['id'] and source['publisher'] and source['year'])
            self.assertTrue(source['claims_supported'])
        for phrase in ['يشخّصك','أوقف الدواء','غيّر الجرعة','علاج مضمون','شفاء نهائي']:
            self.assertNotIn(phrase,visible)

    def test_generated_pages_metadata_schema_links_and_sitemap(self):
        with tempfile.TemporaryDirectory() as temp:
            site=Path(temp)
            site.joinpath('index.html').write_text('<nav><a href="hubs/">المراكز</a></nav><div><article class="card"><h3>المراكز الموضوعية</h3></article></div>',encoding='utf-8')
            site.joinpath('sitemap.xml').write_text('<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',encoding='utf-8')
            subprocess.run([sys.executable,str(PUBLISHER),str(site)],check=True)
            subprocess.run([sys.executable,str(FINALIZER),str(site)],check=True)
            article=site/'blog/normal-anxiety-vs-anxiety-disorder/index.html'
            text=article.read_text(encoding='utf-8'); home=(site/'index.html').read_text(encoding='utf-8')
            self.assertEqual(text.count('<h1>'),1)
            self.assertEqual(text.count('rel="canonical"'),1)
            self.assertIn('application/ld+json',text)
            self.assertIn('BlogPosting',text)
            self.assertIn('manifest.webmanifest',text)
            self.assertIn('sw.js',text)
            self.assertIn('needs-specialist-review',json.loads((site/'api/blog-v160.json').read_text())['review_status'])
            self.assertIn('data-blog-v160',home)
            root=ET.parse(site/'sitemap-blog.xml').getroot()
            self.assertEqual(root.tag.rsplit('}',1)[-1],'urlset')
            self.assertEqual(len(list(root)),2)

if __name__=='__main__': unittest.main()
