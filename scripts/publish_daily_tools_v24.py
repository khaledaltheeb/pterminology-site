from __future__ import annotations
import html, json, sys, xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve()
DATA=ROOT/'content/v24/daily-tools-learning-paths-ar.json'
BASE='https://khaledaltheeb.github.io/pterminology-site/'
PATH='/pterminology-site/'
TODAY=date.today().isoformat()

def e(v): return html.escape(str(v),quote=True)
def shell(title,desc,canonical,schema,body):
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | مصطلحات علم النفس</title><meta name="description" content="{e(desc)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(canonical)}"><script type="application/ld+json">{json.dumps(schema,ensure_ascii=False).replace('</','<\\/')}</script><style>*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:linear-gradient(140deg,#fff8fb,#e7fbf7,#eeeaff)}}main{{width:min(1050px,92%);margin:auto;padding:28px 0 60px}}header,section,article{{background:#fff;border:1px solid #cbe9e5;border-radius:24px;padding:clamp(18px,4vw,36px);margin:16px 0;box-shadow:0 14px 40px rgba(40,100,100,.08)}}header{{background:linear-gradient(135deg,#ffe7f0,#dffaf7,#eee9ff)}}h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.3}}h2{{color:#7d3658}}a{{color:#086e69}}nav{{display:flex;gap:10px;flex-wrap:wrap}}nav a,.button{{display:inline-block;padding:9px 14px;border:1px solid #bfe2de;border-radius:14px;text-decoration:none;background:#fff;font-weight:700}}label{{font-weight:700}}input,textarea{{width:100%;padding:12px;border:1px solid #9fcfc9;border-radius:12px;font:inherit}}textarea{{min-height:100px}}.note{{border-right:5px solid #c7476e;background:#fff0f3}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}@media(max-width:640px){{nav{{display:grid}}}}</style></head><body>{body}</body></html>'''

def nav(): return f'<nav aria-label="التنقل"><a href="{PATH}">الرئيسية</a><a href="{PATH}daily-tools/">الأدوات اليومية</a><a href="{PATH}learning-paths/">مسارات التعلم</a><a href="{PATH}care-guides/">أدلة التعامل</a></nav>'
def source_list(data): return '<ul>'+''.join(f'<li><a rel="noopener noreferrer" href="{e(s["url"])}">{e(s["publisher"])} — {e(s["title"])} ({s["year"]})</a></li>' for s in data['sources'])+'</ul>'
def save_form(tool):
    fields=''.join(f'<p><label>{e(f)}<input data-field="{e(f)}"></label></p>' for f in tool['save_fields'])
    return f'''<section><h2>سجل شخصي على هذا الجهاز</h2><p>لا تُرسل البيانات إلى خادم. احفظ أقل قدر ممكن وتجنب كتابة معلومات تعريفية حساسة.</p><form data-tool="{e(tool['slug'])}">{fields}<button type="button" class="button" onclick="saveTool(this.form)">حفظ محلي</button> <button type="button" class="button" onclick="clearTool(this.form)">مسح</button><p aria-live="polite" class="status"></p></form></section><script>function key(f){{return 'pt-v24-'+f.dataset.tool}}function saveTool(f){{let o={{}};f.querySelectorAll('[data-field]').forEach(x=>o[x.dataset.field]=x.value);localStorage.setItem(key(f),JSON.stringify(o));f.querySelector('.status').textContent='تم الحفظ على هذا الجهاز.'}}function clearTool(f){{localStorage.removeItem(key(f));f.reset();f.querySelector('.status').textContent='تم المسح.'}}document.querySelectorAll('form[data-tool]').forEach(f=>{{try{{let o=JSON.parse(localStorage.getItem(key(f))||'{{}}');f.querySelectorAll('[data-field]').forEach(x=>x.value=o[x.dataset.field]||'')}}catch(e){{}}}})</script>'''
def publish(data):
    out=SITE/'daily-tools';out.mkdir(parents=True,exist_ok=True)
    cards=''.join(f'<article><h2>{e(t["title"])}</h2><p>{e(t["intent"])}</p><p><strong>المدة:</strong> {e(t["duration"])}</p><a class="button" href="{PATH}daily-tools/{e(t["slug"])}/">فتح الأداة</a></article>' for t in data['tools'])
    schema={'@context':'https://schema.org','@type':'CollectionPage','name':'الأدوات النفسية اليومية','inLanguage':'ar','url':BASE+'daily-tools/','hasPart':[{'@type':'WebApplication','name':t['title'],'url':BASE+'daily-tools/'+t['slug']+'/'} for t in data['tools']]}
    (out/'index.html').write_text(shell('أدوات نفسية يومية عملية','أدوات تنظيمية عربية غير تشخيصية للتوتر والنوم والأسرة والفقد والحدود.',BASE+'daily-tools/',schema,f'<main>{nav()}<header><h1>أدوات نفسية يومية</h1><p>{e(data["disclaimer"])}</p></header><div class="grid">{cards}</div><section><h2>المصادر</h2>{source_list(data)}</section></main>'),encoding='utf-8')
    for t in data['tools']:
        d=out/t['slug'];d.mkdir(parents=True,exist_ok=True);canonical=BASE+'daily-tools/'+t['slug']+'/'
        steps=''.join(f'<li>{e(x)}</li>' for x in t['steps'])
        schema={'@context':'https://schema.org','@graph':[{'@type':'WebApplication','name':t['title'],'description':t['intent'],'applicationCategory':'HealthApplication','operatingSystem':'Any','inLanguage':'ar','url':canonical},{'@type':'HowTo','name':t['title'],'step':[{'@type':'HowToStep','position':i+1,'text':x} for i,x in enumerate(t['steps'])]}]}
        body=f'<main>{nav()}<header><p>أداة تنظيمية غير تشخيصية</p><h1>{e(t["title"])}</h1><p>{e(t["intent"])}</p><p><strong>المدة:</strong> {e(t["duration"])}</p></header><section><h2>الخطوات</h2><ol>{steps}</ol></section>{save_form(t)}<section class="note"><h2>السلامة</h2><p>{e(t["safety"])}</p><p>{e(data["disclaimer"])}</p></section><section><h2>مصادر المنهج</h2>{source_list(data)}</section></main>'
        (d/'index.html').write_text(shell(t['title'],t['intent'],canonical,schema,body),encoding='utf-8')
    paths=SITE/'learning-paths';paths.mkdir(parents=True,exist_ok=True)
    cards=''.join(f'<article><h2>{e(p["title"])}</h2><p>{e(p["goal"])}</p><a class="button" href="{PATH}learning-paths/{e(p["slug"])}/">بدء المسار</a></article>' for p in data['paths'])
    (paths/'index.html').write_text(shell('مسارات تعلم الصحة النفسية','مسارات عربية قصيرة مترابطة للتعلم والتطبيق دون تشخيص ذاتي.',BASE+'learning-paths/',{'@context':'https://schema.org','@type':'CollectionPage','name':'مسارات تعلم الصحة النفسية','inLanguage':'ar'},f'<main>{nav()}<header><h1>مسارات تعلم قصيرة</h1><p>{e(data["disclaimer"])}</p></header><div class="grid">{cards}</div></main>'),encoding='utf-8')
    for p in data['paths']:
        d=paths/p['slug'];d.mkdir(parents=True,exist_ok=True);days=''.join(f'<li><strong>اليوم {i+1}:</strong> {e(x)}</li>' for i,x in enumerate(p['days']));links=''.join(f'<li><a href="{PATH}daily-tools/{e(s)}/">{e(next(t["title"] for t in data["tools"] if t["slug"]==s))}</a></li>' for s in p['related_tools'])
        schema={'@context':'https://schema.org','@type':'Course','name':p['title'],'description':p['goal'],'inLanguage':'ar','provider':{'@type':'Organization','name':'مصطلحات علم النفس'}}
        (d/'index.html').write_text(shell(p['title'],p['goal'],BASE+'learning-paths/'+p['slug']+'/',schema,f'<main>{nav()}<header><p>مسار تثقيفي غير علاجي</p><h1>{e(p["title"])}</h1><p>{e(p["goal"])}</p></header><section><h2>خطة الأيام</h2><ol>{days}</ol></section><section><h2>أدوات مرتبطة</h2><ul>{links}</ul></section><section class="note"><p>{e(data["disclaimer"])}</p></section></main>'),encoding='utf-8')
    urls=[BASE+'daily-tools/']+[BASE+'daily-tools/'+t['slug']+'/' for t in data['tools']]+[BASE+'learning-paths/']+[BASE+'learning-paths/'+p['slug']+'/' for p in data['paths']]
    ns='http://www.sitemaps.org/schemas/sitemap/0.9';root=ET.Element('urlset',xmlns=ns)
    for u in urls:
        n=ET.SubElement(root,'url');ET.SubElement(n,'loc').text=u;ET.SubElement(n,'lastmod').text=TODAY;ET.SubElement(n,'changefreq').text='monthly'
    ET.ElementTree(root).write(SITE/'sitemap-tools-paths.xml',encoding='utf-8',xml_declaration=True)
    idx=ET.parse(SITE/'sitemap.xml');r=idx.getroot();target=BASE+'sitemap-tools-paths.xml'
    if target not in {x.text for x in r.findall('{*}sitemap/{*}loc') if x.text}:
        s=ET.SubElement(r,'sitemap');ET.SubElement(s,'loc').text=target
    idx.write(SITE/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    api=SITE/'api';api.mkdir(exist_ok=True);(api/'daily-tools-v24.json').write_text(json.dumps({'version':24,'tools':len(data['tools']),'paths':len(data['paths']),'pages':len(urls),'local_only':True},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':
    if not SITE.exists(): raise SystemExit('Missing site output')
    publish(json.loads(DATA.read_text(encoding='utf-8')))
