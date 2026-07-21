from __future__ import annotations
import json,re,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'content/v24/daily-tools-learning-paths-ar.json'
SITE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else None
BANNED=('يشخص','تشخيصك','يعالج نهائيًا','مضمون','بديل عن الطبيب','درجة الاكتئاب','درجة القلق')
NS='http://www.sitemaps.org/schemas/sitemap/0.9'
def norm(s): return re.sub(r'[\W_]+','',s,flags=re.UNICODE).lower()
def main():
 d=json.loads(DATA.read_text(encoding='utf-8'));tools=d['tools'];paths=d['paths']
 assert len(tools)==8 and len(paths)==4
 slugs=[x['slug'] for x in tools+paths];titles=[norm(x['title']) for x in tools+paths]
 assert len(slugs)==len(set(slugs));assert len(titles)==len(set(titles))
 assert all(re.fullmatch(r'[a-z0-9-]+',s) for s in slugs)
 blob=DATA.read_text(encoding='utf-8').lower();assert not any(x in blob for x in BANNED)
 assert all(len(t['steps'])>=4 and len(t['save_fields'])>=3 and t['safety'] for t in tools)
 tool_slugs={t['slug'] for t in tools}
 assert all(len(p['days'])>=5 and set(p['related_tools'])<=tool_slugs for p in paths)
 sources=d['sources'];assert len(sources)>=4 and all(s['url'].startswith('https://') for s in sources)
 assert len({s['publisher'] for s in sources})>=2
 if SITE:
  expected=[SITE/'daily-tools/index.html',SITE/'learning-paths/index.html']+[SITE/'daily-tools'/t['slug']/'index.html' for t in tools]+[SITE/'learning-paths'/p['slug']/'index.html' for p in paths]
  assert all(p.exists() for p in expected),[str(p) for p in expected if not p.exists()]
  for p in expected:
   text=p.read_text(encoding='utf-8');assert text.count('<h1>')==1 and 'rel="canonical"' in text and 'application/ld+json' in text and 'dir="rtl"' in text
   assert not any(x in text.lower() for x in BANNED)
  for t in tools:
   text=(SITE/'daily-tools'/t['slug']/'index.html').read_text(encoding='utf-8');assert 'localStorage' in text and 'لا تُرسل البيانات إلى خادم' in text
  report=json.loads((SITE/'api/daily-tools-v24.json').read_text(encoding='utf-8'));assert report=={'version':24,'tools':8,'paths':4,'pages':14,'local_only':True}
  child=ET.parse(SITE/'sitemap-tools-paths.xml').getroot()
  assert child.tag==f'{{{NS}}}urlset'
  child_urls=child.findall(f'{{{NS}}}url')
  assert len(child_urls)==14 and all(x.find(f'{{{NS}}}loc') is not None for x in child_urls)
  index=ET.parse(SITE/'sitemap.xml').getroot()
  assert index.tag==f'{{{NS}}}sitemapindex'
  target='https://khaledaltheeb.github.io/pterminology-site/sitemap-tools-paths.xml'
  matches=[x.text for x in index.findall(f'{{{NS}}}sitemap/{{{NS}}}loc') if x.text==target]
  assert len(matches)==1,matches
 print(json.dumps({'tools':8,'paths':4,'unique_slugs':True,'unique_titles':True,'non_diagnostic':True,'sources':len(sources),'production_checked':bool(SITE),'sitemap_namespaces_checked':bool(SITE)},ensure_ascii=False))
if __name__=='__main__': main()
