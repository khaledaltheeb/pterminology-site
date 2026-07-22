from __future__ import annotations
import sys
from pathlib import Path
SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site').resolve(); HOME=SITE/'index.html'
def main()->None:
    if not HOME.exists(): raise SystemExit('Missing generated homepage')
    text=HOME.read_text(encoding='utf-8')
    nav='<a href="blog/">المدونة</a>'
    if nav not in text:
        anchor='<a href="hubs/">المراكز</a>'
        if anchor not in text: raise SystemExit('Homepage navigation anchor changed')
        text=text.replace(anchor,nav+anchor,1)
    card='<article class="card" data-blog-v160><h3>المدونة التحليلية</h3><p>مقالات ركيزية عربية تربط الأسئلة اليومية بالموسوعة والأدوات والمصادر الرسمية دون تشخيص ذاتي.</p><a href="blog/">قراءة المدونة</a></article>'
    if 'data-blog-v160' not in text:
        anchor='<article class="card"><h3>المراكز الموضوعية</h3>'
        if anchor not in text: raise SystemExit('Homepage cards anchor changed')
        text=text.replace(anchor,card+anchor,1)
    HOME.write_text(text,encoding='utf-8')
if __name__=='__main__': main()
