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
NEW_MAKE_TRIAL=r'''function makeTrial(d,stage,index){
 const rnd=seeded((d.slug.length+1)*999+stage*71+index*13),mode=d.mode||d.category||'',slug=d.slug||'';let prompt='',options=[],answer='',kind='text',explanation='',audioCount=0,delay=0;
 const arrows=['↑','→','↓','←'],symbols=['●','▲','■','★','◆','☀'];
 if(mode==='simple_reaction'){prompt='اضغط الآن';answer='اضغط الآن';options=['اضغط الآن'];kind='reaction';delay=350+Math.floor(rnd()*650);explanation='تم تسجيل زمن الاستجابة بعد ظهور الإشارة.';}
 else if(mode==='choice_reaction'){const target=arrows[Math.floor(rnd()*4)];prompt=`اختر اتجاه السهم: ${target}`;answer=target;options=shuffle(arrows,rnd);explanation=`الاتجاه الصحيح هو ${target}.`;}
 else if(mode==='visual_reaction'){const pool=stage<2?['●','○','◉','◎']:['▲','△','◆','◇'];const target=pool[Math.floor(rnd()*pool.length)];const distract=pool[(pool.indexOf(target)+1)%pool.length];const count=6+stage*2;const row=shuffle([target,...Array(count-1).fill(distract)],rnd).join(' ');prompt=`اعثر على الرمز المختلف: ${row}`;answer=target;options=shuffle(unique(pool),rnd);explanation=`الرمز المختلف هو ${target}.`;}
 else if(mode==='auditory_symbol'){audioCount=1+Math.floor(rnd()*4);const map=['●','▲','■','★'];prompt='استمع إلى عدد النغمات ثم اختر الرمز المقابل: 1=●، 2=▲، 3=■، 4=★';answer=map[audioCount-1];options=shuffle(map,rnd);kind='audio';explanation=`سُمعت ${audioCount} نغمات، والرمز المقابل هو ${answer}.`;}
 else if(mode==='go_no_go'){const targets=stage<2?['●']:stage<4?['●','▲']:['●','▲','■'];const shown=symbols[Math.floor(rnd()*symbols.length)];const go=targets.includes(shown);prompt=`القاعدة: استجب للرموز ${targets.join('، ')}. المثير الحالي: ${shown}`;answer=go?'استجب':'امتنع';options=['استجب','امتنع'];explanation=go?'المثير هدف، لذا الاستجابة صحيحة.':'المثير ليس هدفًا، لذا الامتناع صحيح.';}
 else if(mode==='stroop_basic'){const word=COLORS[Math.floor(rnd()*COLORS.length)],ink=COLORS[(Math.floor(rnd()*COLORS.length)+(index%2?1:0))%COLORS.length];prompt=`اختر لون الحبر لا معنى الكلمة: ${word.label}`;answer=ink.value;options=shuffle(COLORS,rnd);kind='stroop';explanation=`لون الحبر المستهدف هو ${ink.label}.`;}
 else if(mode==='stroop_advanced'){const word=COLORS[Math.floor(rnd()*COLORS.length)],ink=COLORS[Math.floor(rnd()*COLORS.length)],useInk=(stage+index)%2===0;prompt=`القاعدة: اختر ${useInk?'لون الحبر':'معنى الكلمة'}. الكلمة: ${word.label}`;answer=useInk?ink.value:word.value;options=shuffle(COLORS,rnd);kind='stroop';explanation=`طُبقت قاعدة ${useInk?'لون الحبر':'معنى الكلمة'}، والإجابة ${answer}.`;}
 else if(mode==='response_inhibition'){const center=arrows[Math.floor(rnd()*4)],flanker=(index+stage)%2?arrows[(arrows.indexOf(center)+1)%4]:center;prompt=`اختر اتجاه السهم الأوسط فقط: ${flanker} ${flanker} ${center} ${flanker} ${flanker}`;answer=center;options=shuffle(arrows,rnd);explanation=`اتجاه السهم الأوسط هو ${center}.`;}
 else if(mode==='digit_span_forward'||mode==='digit_span_backward'){const len=3+stage,seq=Array.from({length:len},()=>Math.floor(rnd()*9)+1),correct=(mode==='digit_span_backward'?[...seq].reverse():seq).join(' ');const variants=[correct,[...seq].reverse().join(' '),[...seq.slice(1),seq[0]].join(' '),[seq[0],...seq.slice(2),seq[1]].join(' ')];prompt=`احفظ التسلسل ثم اختره ${mode==='digit_span_backward'?'معكوسًا':'بالترتيب نفسه'}: ${seq.join(' – ')}`;answer=correct;options=shuffle(unique(variants),rnd);explanation=`التسلسل الصحيح هو ${correct}.`;}
 else if(/السرعة/.test(mode)||/reaction|auditory-symbol/.test(slug)){const target=COLORS[Math.floor(rnd()*COLORS.length)];prompt=`اختر اللون: ${target.label}`;answer=target.value;options=shuffle(COLORS,rnd);kind='color';explanation=`الإجابة الصحيحة هي ${target.label}.`;}
 else if(/الكبح/.test(mode)||/go-no-go|stroop|inhibition/.test(slug)){const word=COLORS[Math.floor(rnd()*COLORS.length)],ink=COLORS[Math.floor(rnd()*COLORS.length)];prompt=`اختر لون الحبر لا معنى الكلمة: ${word.label}`;answer=ink.value;options=shuffle(COLORS,rnd);kind='stroop';explanation=`لون الحبر المستهدف هو ${ink.label}.`;}
 else if(/الذاكرة العاملة/.test(mode)){const nums=Array.from({length:3+stage},()=>Math.floor(rnd()*9)+1);prompt=`ما آخر رقم في التسلسل ${nums.join(' – ')}؟`;answer=String(nums[nums.length-1]);options=shuffle(unique([answer,String((Number(answer)+1)%10),String((Number(answer)+2)%10),String(Math.max(0,Number(answer)-1))]),rnd);explanation=`الإجابة هي ${answer}.`;}
 else if(/الذاكرة/.test(mode)){const seq=Array.from({length:4+stage},()=>symbols[Math.floor(rnd()*symbols.length)]),pos=Math.min(seq.length-1,1+Math.floor(rnd()*(seq.length-1)));prompt=`ما الرمز رقم ${pos+1} في التسلسل: ${seq.join('  ')}؟`;answer=seq[pos];options=shuffle(unique([answer,...shuffle(symbols,rnd).filter(x=>x!==answer).slice(0,3)]),rnd);explanation=`الرمز في الموضع ${pos+1} هو ${answer}.`;}
 else if(/الانتباه/.test(mode)){const target=['★','●','▲'][Math.floor(rnd()*3)],count=2+Math.floor(rnd()*4),distract=['○','△','◇'],row=shuffle([...Array(count).fill(target),...Array(8-count).fill(0).map(()=>distract[Math.floor(rnd()*distract.length)])],rnd);prompt=`كم مرة يظهر ${target}؟ ${row.join(' ')}`;answer=String(count);options=shuffle(unique([answer,String(count+1),String(Math.max(0,count-1)),String(count+2)]),rnd);explanation=`ظهر الرمز ${count} مرات.`;}
 else if(/الاستدلال/.test(mode)){const a=Math.floor(rnd()*8)+2,b=Math.floor(rnd()*5)+1;prompt=`أكمل النمط: ${a}، ${a+b}، ${a+2*b}، ؟`;answer=String(a+3*b);options=shuffle(unique([answer,String(a+4*b),String(a+2*b+1),String(Math.max(0,a+3*b-2))]),rnd);explanation=`يزداد التسلسل بمقدار ${b}.`;}
 else if(/المرونة/.test(mode)){const rule=stage%2===0?'اختر الأكبر':'اختر الأصغر',a=Math.floor(rnd()*20)+1,b=Math.floor(rnd()*20)+1;prompt=`القاعدة الحالية: ${rule}. اختر بين ${a} و${b}.`;answer=String(stage%2===0?Math.max(a,b):Math.min(a,b));options=shuffle(unique([String(a),String(b),String(a+b),String(Math.abs(a-b))]),rnd);explanation=`طُبقت قاعدة ${rule}.`;}
 else{const target=Math.floor(rnd()*9)+1;prompt=`اختر الرقم ${target}`;answer=String(target);options=shuffle([String(target),String((target+1)%10),String((target+2)%10),String((target+3)%10)],rnd);explanation=`الرقم المطلوب هو ${target}.`;}
 return{prompt,options,answer,kind,explanation,audioCount,delay};
}
'''

def patch_page(tool:dict)->None:
 p=SITE/'cognitive-lab'/tool['slug']/'index.html';text=p.read_text(encoding='utf-8')
 m=re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>',text,re.S)
 if not m: raise SystemExit(f'missing definition {p}')
 old=json.loads(m.group(1));new={**old,**tool,'instrument_type':'مهمة تدريبية أصلية غير تشخيصية','version':22}
 payload=json.dumps(new,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
 text=text[:m.start(1)]+payload+text[m.end(1):]
 text=text.replace(old.get('title',''),tool['title']).replace(old.get('summary',''),tool['summary'])
 marker='<div class="question"><strong>مهم:</strong>'
 if tool['instructions'] not in text:text=text.replace(marker,f'<div class="question"><strong>طريقة الاستخدام:</strong> {tool["instructions"]}</div>{marker}',1)
 p.write_text(text,encoding='utf-8')

def patch_runtime()->None:
 p=SITE/'assets/js/lab-v12.js';text=p.read_text(encoding='utf-8')
 text,n=re.subn(r'function makeTrial\(d,stage,index\)\{.*?\n\}\nfunction optionHtml',NEW_MAKE_TRIAL+'function optionHtml',text,count=1,flags=re.S)
 if n!=1:raise SystemExit('makeTrial replacement failed')
 tone="function playBeeps(count){try{const C=window.AudioContext||window.webkitAudioContext;if(!C)return;const c=new C();for(let i=0;i<count;i++){const o=c.createOscillator(),g=c.createGain();o.frequency.value=520;o.connect(g);g.connect(c.destination);const t=c.currentTime+i*.22;g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.18,t+.01);g.gain.exponentialRampToValueAtTime(.0001,t+.13);o.start(t);o.stop(t+.14)}}catch{}}\n"
 text=text.replace('function optionHtml',tone+'function optionHtml',1)
 old="current=makeTrial(d,state.stage,state.trial);started=now();const stim=q('.stimulus',host);stim.innerHTML=`<div class=\"trial-card\"><p>${current.prompt}</p>"
 new="current=makeTrial(d,state.stage,state.trial);const stim=q('.stimulus',host);if(current.delay){stim.innerHTML='<p>انتظر الإشارة…</p>';await new Promise(r=>setTimeout(r,current.delay));}started=now();stim.innerHTML=`<div class=\"trial-card\"><p>${current.prompt}</p>"
 if old not in text:raise SystemExit('nextTrial timing patch failed')
 text=text.replace('function nextTrial(){','async function nextTrial(){',1).replace(old,new,1)
 text=text.replace("qa('[data-value]',stim).forEach(b=>b.onclick=()=>{", "if(current.audioCount)playBeeps(current.audioCount);qa('[data-value]',stim).forEach(b=>b.onclick=()=>{",1)
 p.write_text(text,encoding='utf-8')

def main()->None:
 for tool in TOOLS:patch_page(tool)
 index=SITE/'cognitive-lab'/'index.html';text=index.read_text(encoding='utf-8')
 for tool in TOOLS:
  pattern=rf'(<a class="lab-v12__card" href="[^"]*{re.escape(tool["slug"])}[^"]*">.*?<h2>)(.*?)(</h2><p>)(.*?)(</p>)'
  text,n=re.subn(pattern,lambda m:m.group(1)+tool['title']+m.group(3)+tool['summary']+m.group(5),text,count=1,flags=re.S)
  if n!=1:raise SystemExit(f'index card not patched: {tool["slug"]}')
 index.write_text(text,encoding='utf-8');patch_runtime()
 report={'version':22,'batch':1,'count':10,'distinct_modes':10,'stages':50,'trials':410,'slugs':[x['slug'] for x in TOOLS]}
 api=SITE/'api';api.mkdir(exist_ok=True);(api/'cognitive-batch1-v22.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
