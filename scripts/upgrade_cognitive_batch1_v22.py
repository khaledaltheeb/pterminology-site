from __future__ import annotations
import json,re,sys
from pathlib import Path

SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
TOOLS=[
 {'slug':'simple-reaction','title':'سرعة الاستجابة البسيطة','category':'سرعة الاستجابة','summary':'مهمة زمنية من خمس مراحل تقيس سرعة الضغط عند ظهور إشارة بصرية واحدة بعد انتظار متغير. تعرض الدقة والزمن الوسيط وتحفظ التقدم تلقائيًا.','mode':'simple_reaction','stages':5,'trials_per_stage':8,'instructions':'انتظر حتى تظهر إشارة «اضغط الآن»، ثم اضغط بأسرع ما تستطيع دون ضغط مبكر.'},
 {'slug':'choice-reaction','title':'سرعة الاستجابة الاختيارية','category':'سرعة الاستجابة','summary':'مهمة من خمس مراحل تربط اتجاه سهم بأحد أربعة اختيارات، وتزيد التشابه البصري تدريجيًا لقياس سرعة القرار مع الحفاظ على الدقة.','mode':'choice_reaction','stages':5,'trials_per_stage':8,'instructions':'اختر الاتجاه المطابق للسهم المركزي. ركّز على الدقة أولًا ثم السرعة.'},
 {'slug':'visual-reaction','title':'سرعة الاكتشاف البصري','category':'سرعة الاستجابة','summary':'مهمة بحث بصري من خمس مراحل تتطلب اكتشاف رمز هدف بين مشتتات متشابهة، مع زيادة عدد العناصر والتشابه عبر المراحل.','mode':'visual_reaction','stages':5,'trials_per_stage':8,'instructions':'اعثر على الرمز المختلف أو الهدف المحدد بين المشتتات، ثم اختره.'},
 {'slug':'auditory-symbol','title':'ربط النغمة بالرمز','category':'التمييز السمعي','summary':'مهمة سمعية متعددة المراحل تشغّل عددًا قصيرًا من النغمات، ثم تطلب اختيار الرمز المقابل للعدد وفق قاعدة ظاهرة وثابتة داخل المحاولة.','mode':'auditory_symbol','stages':5,'trials_per_stage':7,'instructions':'استمع للنغمات ثم اختر الرمز الذي يطابق عددها. يمكن إعادة تشغيل النغمة قبل الإجابة.'},
 {'slug':'go-no-go','title':'اذهب أو توقف','category':'كبح الاستجابة','summary':'مهمة قرار متدرّجة بين الاستجابة والامتناع وفق قاعدة هدف واضحة تتبدل صعوبتها عبر خمس مراحل، مع تسجيل الدقة والزمن.','mode':'go_no_go','stages':5,'trials_per_stage':10,'instructions':'اختر «استجب» للهدف و«امتنع» للمثير غير الهدف حسب القاعدة المعروضة.'},
 {'slug':'stroop-basic','title':'مهمة ستروب الأساسية','category':'كبح الاستجابة','summary':'مهمة من خمس مراحل تطلب اختيار لون الحبر مع تجاهل معنى كلمة اللون، وتوازن بين المحاولات المتوافقة والمتعارضة.','mode':'stroop_basic','stages':5,'trials_per_stage':8,'instructions':'اختر لون الحبر الذي كُتبت به الكلمة، ولا تختَر معنى الكلمة.'},
 {'slug':'stroop-advanced','title':'مهمة ستروب المتقدمة','category':'كبح الاستجابة والمرونة','summary':'مهمة ستروب متقدمة تتناوب فيها القاعدة بين لون الحبر ومعنى الكلمة وفق إشارة ظاهرة، فتقيس الالتزام بالقاعدة وتبديلها دون خلط.','mode':'stroop_advanced','stages':5,'trials_per_stage':10,'instructions':'اقرأ قاعدة كل محاولة: أحيانًا اختر لون الحبر وأحيانًا اختر معنى الكلمة.'},
 {'slug':'response-inhibition','title':'كبح الاستجابة للمشتتات','category':'كبح الاستجابة','summary':'مهمة أسهم مركزية من خمس مراحل تتطلب الاستجابة لاتجاه السهم الأوسط وتجاهل الأسهم المحيطة المتوافقة أو المتعارضة.','mode':'response_inhibition','stages':5,'trials_per_stage':10,'instructions':'استجب لاتجاه السهم الأوسط فقط، وتجاهل اتجاه الأسهم المحيطة.'},
 {'slug':'digit-span-forward','title':'مدى الأرقام الأمامي','category':'الذاكرة العاملة','summary':'مهمة تذكّر تسلسل رقمي بالترتيب نفسه عبر خمس مراحل، يبدأ الطول قصيرًا ويزداد تدريجيًا مع بدائل كاملة غير مكررة.','mode':'digit_span_forward','stages':5,'trials_per_stage':6,'instructions':'احفظ تسلسل الأرقام ثم اختر التسلسل نفسه بالترتيب الأصلي.'},
 {'slug':'digit-span-backward','title':'مدى الأرقام العكسي','category':'الذاكرة العاملة','summary':'مهمة تذكّر ومعالجة تتطلب اختيار التسلسل الرقمي معكوسًا، ويزداد طول السلسلة تدريجيًا عبر خمس مراحل.','mode':'digit_span_backward','stages':5,'trials_per_stage':6,'instructions':'احفظ الأرقام ثم اخترها بالترتيب العكسي الكامل، لا الرقم الأخير فقط.'},
]

def patch_page(tool:dict)->None:
 p=SITE/'cognitive-lab'/tool['slug']/'index.html'
 text=p.read_text(encoding='utf-8')
 m=re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>',text,re.S)
 if not m: raise SystemExit(f'missing definition {p}')
 old=json.loads(m.group(1)); new={**old,**tool,'instrument_type':'مهمة تدريبية أصلية غير تشخيصية','version':22}
 payload=json.dumps(new,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
 text=text[:m.start(1)]+payload+text[m.end(1):]
 old_title=old.get('title','');old_summary=old.get('summary','')
 text=text.replace(old_title,tool['title']).replace(old_summary,tool['summary'])
 marker='<div class="question"><strong>مهم:</strong>'
 if tool['instructions'] not in text:
  text=text.replace(marker,f'<div class="question"><strong>طريقة الاستخدام:</strong> {tool["instructions"]}</div>{marker}',1)
 p.write_text(text,encoding='utf-8')

def main()->None:
 for tool in TOOLS: patch_page(tool)
 index=SITE/'cognitive-lab'/'index.html'; text=index.read_text(encoding='utf-8')
 for tool in TOOLS:
  pattern=rf'(<a class="lab-v12__card" href="[^"]*{re.escape(tool["slug"])}[^"]*">.*?<h2>)(.*?)(</h2><p>)(.*?)(</p>)'
  text,n=re.subn(pattern,lambda m:m.group(1)+tool['title']+m.group(3)+tool['summary']+m.group(5),text,count=1,flags=re.S)
  if n!=1: raise SystemExit(f'index card not patched: {tool["slug"]}')
 index.write_text(text,encoding='utf-8')
 report={'version':22,'batch':1,'count':len(TOOLS),'slugs':[x['slug'] for x in TOOLS],'distinct_modes':len({x['mode'] for x in TOOLS}),'stages':sum(x['stages'] for x in TOOLS),'trials':sum(x['stages']*x['trials_per_stage'] for x in TOOLS)}
 api=SITE/'api';api.mkdir(exist_ok=True);(api/'cognitive-batch1-v22.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
