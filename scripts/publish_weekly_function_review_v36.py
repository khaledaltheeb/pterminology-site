from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
PATH = "/pterminology-site/"
SLUG = "weekly-function-review"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def build_page() -> str:
    canonical = f"{BASE}daily-tools/{SLUG}/"
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebApplication",
                "name": "مراجعة الأداء الأسبوعية",
                "description": "أداة تنظيمية غير تشخيصية لمراجعة النوم والطاقة والتركيز والعلاقات والمهام مع تاريخ محلي اختياري.",
                "applicationCategory": "HealthApplication",
                "operatingSystem": "Any",
                "inLanguage": "ar",
                "url": canonical,
                "isAccessibleForFree": True,
            },
            {
                "@type": "HowTo",
                "name": "كيفية استخدام مراجعة الأداء الأسبوعية",
                "step": [
                    {"@type": "HowToStep", "position": 1, "text": "قيّم خمسة مجالات من صفر إلى عشرة."},
                    {"@type": "HowToStep", "position": 2, "text": "راجع القراءة التنظيمية غير التشخيصية."},
                    {"@type": "HowToStep", "position": 3, "text": "اختر حفظ السجل محليًا على جهازك أو استخدم الأداة دون حفظ."},
                    {"@type": "HowToStep", "position": 4, "text": "صدّر أو اطبع أو احذف جميع البيانات المحلية متى شئت."},
                ],
            },
        ],
    }
    questions = [
        ("sleep", "النوم", "إلى أي درجة كان نومك داعمًا لوظيفتك اليومية هذا الأسبوع؟"),
        ("energy", "الطاقة", "إلى أي درجة كانت طاقتك كافية للأنشطة الأساسية؟"),
        ("focus", "التركيز", "إلى أي درجة استطعت بدء المهام والاستمرار فيها؟"),
        ("relationships", "العلاقات", "إلى أي درجة حافظت على تواصل آمن ومقبول مع الآخرين؟"),
        ("tasks", "المهام", "إلى أي درجة أتممت الضروريات الواقعية دون استنزاف؟"),
    ]
    fields = "".join(
        f'''<fieldset><legend>{esc(title)}</legend><label for="{name}">{esc(prompt)}</label><div class="rating-row"><span aria-hidden="true">0</span><input id="{name}" name="{name}" type="range" min="0" max="10" step="1" value="5" aria-describedby="{name}-help"><output for="{name}">5</output><span aria-hidden="true">10</span></div><p id="{name}-help" class="help">0 يعني تعطلًا شديدًا في هذا المجال، و10 يعني دعمًا قويًا. هذه ليست درجة سريرية.</p></fieldset>'''
        for name, title, prompt in questions
    )
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>مراجعة الأداء الأسبوعية | مصطلحات علم النفس</title>
<meta name="description" content="أداة عربية غير تشخيصية لمراجعة النوم والطاقة والتركيز والعلاقات والمهام، مع سجل محلي اختياري وتصدير وطباعة وحذف شامل.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="مراجعة الأداء الأسبوعية"><meta property="og:description" content="مراجعة تنظيمية غير تشخيصية مع تاريخ محلي اختياري وخصوصية واضحة."><meta property="og:url" content="{canonical}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace('</', '<\/')}</script>
<style>
*{{box-sizing:border-box}}:root{{color-scheme:light}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.8;color:#173f45;background:linear-gradient(145deg,#fff8fb,#e9fbf8,#f0edff)}}main{{width:min(1080px,94%);margin:auto;padding:24px 0 70px}}header,section,aside{{background:#fff;border:1px solid #c5e2df;border-radius:22px;padding:clamp(18px,4vw,34px);margin:16px 0;box-shadow:0 12px 35px rgba(20,80,85,.08)}}header{{background:linear-gradient(135deg,#ffe8f1,#e2faf7,#eee9ff)}}h1{{font-size:clamp(2rem,6vw,3.6rem);line-height:1.25}}h2{{color:#743957}}a{{color:#075f61}}nav{{display:flex;flex-wrap:wrap;gap:10px}}nav a,.button,button{{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:10px 15px;border:1px solid #8ebfba;border-radius:12px;background:#fff;color:#173f45;font:inherit;font-weight:700;text-decoration:none;cursor:pointer}}button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible{{outline:3px solid #6c3d8d;outline-offset:3px}}form{{display:grid;gap:16px}}fieldset{{border:1px solid #b7d8d4;border-radius:16px;padding:16px}}legend,label{{font-weight:700}}.rating-row{{display:grid;grid-template-columns:auto 1fr auto auto;gap:12px;align-items:center;margin-top:12px}}input[type=range]{{width:100%;min-height:44px}}output{{min-width:2.5rem;text-align:center;font-weight:700;border:1px solid #aacfc9;border-radius:9px;padding:4px 8px}}textarea,input[type=date]{{width:100%;padding:11px;border:1px solid #91c3bd;border-radius:10px;font:inherit}}textarea{{min-height:110px}}.help,.muted{{color:#48686b;font-size:.95rem}}.privacy{{border-right:6px solid #146b6a;background:#eefaf8}}.safety{{border-right:6px solid #a43d58;background:#fff1f4}}.actions{{display:flex;flex-wrap:wrap;gap:10px}}.danger{{border-color:#9b3048;color:#7a1730}}[hidden]{{display:none!important}}table{{width:100%;border-collapse:collapse;min-width:720px}}th,td{{border:1px solid #bdd7d4;padding:9px;text-align:center}}.table-wrap{{overflow:auto}}canvas{{width:100%;height:260px;border:1px solid #bdd7d4;border-radius:12px;background:#fff}}.result{{background:#f3fbfa;border:2px solid #7fb8b2}}.status{{min-height:1.8em;font-weight:700}}@media(max-width:640px){{nav,.actions{{display:grid}}.rating-row{{grid-template-columns:auto 1fr auto}}.rating-row output{{grid-column:1/-1}}}}@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{scroll-behavior:auto!important;animation:none!important;transition:none!important}}}}@media print{{nav,.actions,.privacy input,.screen-only{{display:none!important}}body{{background:#fff}}main{{width:100%;padding:0}}header,section,aside{{box-shadow:none;break-inside:avoid}}}}
</style>
</head>
<body>
<main>
<nav aria-label="التنقل الرئيسي"><a href="{PATH}">الرئيسية</a><a href="{PATH}daily-tools/">الأدوات اليومية</a><a href="{PATH}learning-paths/">مسارات التعلم</a><a href="{PATH}care-guides/">أدلة التعامل</a></nav>
<header><p>أداة تنظيمية غير تشخيصية</p><h1>مراجعة الأداء الأسبوعية</h1><p>راجع خمسة مجالات وظيفية، ثم اختر خطوة صغيرة واقعية. لا تنتج الأداة تشخيصًا ولا درجة سريرية ولا توصية دوائية.</p></header>
<section class="privacy" aria-labelledby="privacy-title"><h2 id="privacy-title">الخصوصية قبل الاستخدام</h2><p>الحساب يتم داخل المتصفح. لا تُرسل البيانات إلى خادم. الحفظ اختياري ومحلي على هذا الجهاز فقط، ويمكن حذف جميع السجلات فورًا.</p><label><input id="weekly-review-storage-consent" type="checkbox"> أوافق على حفظ السجل محليًا على هذا الجهاز</label></section>
<section><h2>أدخل مراجعة هذا الأسبوع</h2><form data-weekly-review-v36 novalidate><label for="date">تاريخ نهاية الأسبوع</label><input id="date" name="date" type="date" required>{fields}<label for="note">ملاحظة اختيارية لا تتجاوز 500 حرفًا</label><textarea id="note" name="note" maxlength="500" placeholder="حدث مهم، ضغط محتمل، أو عامل ساعدك دون كتابة بيانات تعريفية حساسة."></textarea><div class="actions"><button type="submit">احسب القراءة</button><button id="weekly-review-print" type="button">طباعة</button><button id="weekly-review-export-json" type="button">تصدير JSON</button><button id="weekly-review-export-csv" type="button">تصدير CSV</button><button id="weekly-review-clear" class="danger" type="button">حذف جميع البيانات</button></div><p id="weekly-review-status" class="status" aria-live="polite"></p></form></section>
<section id="weekly-review-result" class="result" aria-live="polite" tabindex="-1" hidden></section>
<section><h2>التاريخ المحلي والاتجاه</h2><p id="weekly-review-empty">لا توجد سجلات محفوظة. يمكنك استخدام الأداة دون حفظ.</p><canvas id="weekly-review-chart" role="img" aria-describedby="weekly-review-chart-text"></canvas><p id="weekly-review-chart-text" class="muted"></p><div class="table-wrap"><table><caption>سجل المراجعات الأسبوعية المحفوظ محليًا</caption><thead><tr><th>التاريخ</th><th>النوم</th><th>الطاقة</th><th>التركيز</th><th>العلاقات</th><th>المهام</th><th>المتوسط التنظيمي</th></tr></thead><tbody id="weekly-review-history-body"></tbody></table></div></section>
<aside class="safety" aria-labelledby="safety-title"><h2 id="safety-title">متى تطلب المساعدة؟</h2><p>إذا استمر التعطل أو أثر في الدراسة أو العمل أو العلاقات أو العناية بالنفس، تواصل مع مختص مؤهل. عند وجود خطر مباشر، أفكار لإيذاء النفس أو الآخرين، فقدان السيطرة، أو عدم القدرة على البقاء آمنًا، استخدم خدمات الطوارئ المحلية فورًا ولا تعتمد على هذه الأداة.</p></aside>
<section><h2>حدود الأداة</h2><ul><li>لا تقارن نفسك بشخص آخر، بل راقب التغير داخل ظروفك.</li><li>المتوسط الحسابي وسيلة تنظيم فقط، وليس مقياسًا نفسيًا معتمدًا.</li><li>الانخفاض قد يرتبط بألم أو مرض أو دواء أو بيئة أو ضغط أو نقص نوم، ولا يثبت سببًا نفسيًا.</li><li>اختر خطوة واحدة قابلة للتنفيذ بدل محاولة إصلاح كل المجالات دفعة واحدة.</li></ul></section>
</main>
<script src="{PATH}assets/weekly-function-review-v36.js" defer></script>
<script>document.querySelectorAll('input[type=range]').forEach(function(input){{var out=input.parentElement.querySelector('output');function sync(){{out.value=input.value;out.textContent=input.value}}input.addEventListener('input',sync);sync()}});document.getElementById('date').value=new Date().toISOString().slice(0,10);</script>
</body></html>'''


def publish() -> None:
    if not SITE.exists():
        raise SystemExit("Missing site output")
    target = SITE / "daily-tools" / SLUG
    target.mkdir(parents=True, exist_ok=True)
    assets = SITE / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets" / "weekly-function-review-v36.js", assets / "weekly-function-review-v36.js")
    (target / "index.html").write_text(build_page(), encoding="utf-8")
    api = SITE / "api"
    api.mkdir(exist_ok=True)
    report = {
        "version": 36,
        "tool": SLUG,
        "questions": 5,
        "rating_min": 0,
        "rating_max": 10,
        "storage": "optional-local-only",
        "history_limit": 52,
        "exports": ["json", "csv", "print"],
        "delete_all": True,
        "non_diagnostic": True,
        "accessible_chart_fallback": True,
    }
    (api / "weekly-function-review-v36.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    publish()
