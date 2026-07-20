from __future__ import annotations
import json,re,sys
from pathlib import Path
SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
TOOLS=[
('letter-span','مدى الحروف المتسلسل','الذاكرة العاملة','letter_span','احفظ سلسلة الحروف ثم اخترها بالترتيب نفسه.'),
('spatial-span','المدى المكاني المتسلسل','الذاكرة العاملة','spatial_span','احفظ تسلسل المواقع ثم اختر المسار الصحيح.'),
('one-back','مهمة المطابقة 1-Back','الذاكرة العاملة','one_back','حدد هل الرمز الحالي يطابق الرمز السابق مباشرة.'),
('two-back','مهمة المطابقة 2-Back','الذاكرة العاملة','two_back','حدد هل الرمز الحالي يطابق الرمز قبل خطوتين.'),
('three-back','مهمة المطابقة 3-Back','الذاكرة العاملة','three_back','حدد هل الرمز الحالي يطابق الرمز قبل ثلاث خطوات.'),
('memory-update','تحديث محتوى الذاكرة','الذاكرة العاملة','memory_update','تابع القيمة الابتدائية وطبّق التغييرات بالتتابع ثم اختر الناتج.'),
('visual-grid','ذاكرة مواقع الشبكة','الذاكرة البصرية','visual_grid','شاهد الخلايا المضيئة ثم اختر النمط المطابق بعد اختفائه.'),
('sequence-memory','ذاكرة ترتيب الرموز','الذاكرة','sequence_memory','احفظ ترتيب الرموز ثم اختر التسلسل الكامل الصحيح.'),
('paired-associates','ذاكرة الأزواج المترابطة','الذاكرة','paired_associates','احفظ أزواج الكلمات ثم اختر الشريك الصحيح بعد اختفاء قائمة الدراسة.'),
('symbol-memory','ذاكرة الرموز المستهدفة','الذاكرة البصرية','symbol_memory','شاهد مجموعة رموز ثم حدد الرمز الذي كان موجودًا بينها.'),
]
SUM={
'letter-span':'مهمة من خمس مراحل لقياس الاحتفاظ المتسلسل بالحروف، مع زيادة طول السلسلة تدريجيًا وإخفائها قبل الإجابة.',
'spatial-span':'مهمة مكانية من خمس مراحل تعرض مسارًا بين مواقع شبكة ثم تخفيه قبل اختيار المسار الصحيح.',
'one-back':'مهمة مطابقة مستمرة تقارن كل رمز بالرمز السابق مباشرة، مع توازن بين حالات التطابق وعدم التطابق.',
'two-back':'مهمة مطابقة مستمرة تقارن الرمز الحالي بما ظهر قبل خطوتين، مع تاريخ واضح محفوظ داخل كل محاولة.',
'three-back':'مهمة مطابقة مستمرة أصعب تقارن الرمز الحالي بما ظهر قبل ثلاث خطوات دون تحويلها إلى سؤال ذاكرة بسيط.',
'memory-update':'مهمة تحديث ذهني تعرض قيمة أولية وسلسلة عمليات قصيرة ثم تطلب الناتج النهائي بعد إخفاء خطوات المعالجة.',
'visual-grid':'مهمة ذاكرة بصرية تعرض خلايا مضيئة في شبكة ثم تخفيها قبل عرض أنماط بديلة متقاربة.',
'sequence-memory':'مهمة تذكّر ترتيب كامل لرموز متعددة، مع بدائل تختلف في مواضع محددة لا في رمز واحد فقط.',
'paired-associates':'مهمة تعلم أزواج تربط كلمات ببعضها، ثم تختبر استدعاء الشريك الصحيح بعد فترة دراسة قصيرة.',
'symbol-memory':'مهمة تعرف بصري تعرض مجموعة رموز ثم تختبر وجود رمز مستهدف بين بدائل مألوفة وجديدة.'}
BRANCH=r'''
 else if(mode==='letter_span'){const letters=['ب','د','ر','س','م','ن','ك','ل'],len=3+stage,seq=Array.from({length:len},()=>letters[Math.floor(rnd()*letters.length)]),correct=seq.join(' ');prompt='اختر تسلسل الحروف نفسه';answer=correct;options=shuffle(unique([correct,[...seq].reverse().join(' '),[...seq.slice(1),seq[0]].join(' '),[seq[0],...seq.slice(2),seq[1]].join(' ')]),rnd);study=`${seq.join(' – ')}`;studyMs=900+len*180;explanation=`التسلسل الصحيح هو ${correct}.`;}
 else if(mode==='spatial_span'){const cells=['1','2','3','4','5','6','7','8','9'],len=3+stage,seq=Array.from({length:len},()=>cells[Math.floor(rnd()*cells.length)]),correct=seq.join('→');prompt='اختر مسار المواقع الصحيح';answer=correct;options=shuffle(unique([correct,[...seq].reverse().join('→'),[...seq.slice(1),seq[0]].join('→'),[seq[0],...seq.slice(2),seq[1]].join('→')]),rnd);study=`المسار: ${seq.join(' → ')}`;studyMs=1000+len*180;explanation=`المسار الصحيح هو ${correct}.`;}
 else if(/^(one_back|two_back|three_back)$/.test(mode)){const n=mode==='one_back'?1:mode==='two_back'?2:3,pool=['●','▲','■','◆','★'],history=Array.from({length:n},()=>pool[Math.floor(rnd()*pool.length)]),match=(index+stage)%2===0,current=match?history[0]:pool.find(x=>x!==history[0]);prompt=`هل الرمز الحالي ${current} يطابق الرمز قبل ${n}؟`;answer=match?'نعم':'لا';options=['نعم','لا'];study=`السجل السابق: ${history.join(' ، ')}`;studyMs=900+stage*100;explanation=match?'يوجد تطابق وفق المسافة المطلوبة.':'لا يوجد تطابق وفق المسافة المطلوبة.';}
 else if(mode==='memory_update'){let value=2+Math.floor(rnd()*7),shown=value,ops=[];for(let i=0;i<2+stage;i++){const delta=(Math.floor(rnd()*5)-2)||1;value+=delta;ops.push(delta>0?`+${delta}`:`${delta}`)}prompt='ما القيمة النهائية بعد تطبيق التغييرات؟';answer=String(value);options=shuffle(unique([answer,String(value+1),String(value-1),String(value+2)]),rnd);study=`ابدأ من ${shown} ثم طبّق: ${ops.join(' ، ')}`;studyMs=1200+stage*250;explanation=`الناتج النهائي هو ${value}.`;}
 else if(mode==='visual_grid'){const count=2+stage,cells=shuffle(['1','2','3','4','5','6','7','8','9'],rnd).slice(0,count).sort(),correct=cells.join('-');prompt='اختر نمط الخلايا الذي ظهر';answer=correct;options=shuffle(unique([correct,[...cells].reverse().join('-'),[...cells.slice(1),String((Number(cells[0])%9)+1)].sort().join('-'),[...cells.slice(0,-1),String((Number(cells.at(-1))%9)+1)].sort().join('-')]),rnd);study=`الخلايا المضيئة: ${cells.join(' ، ')}`;studyMs=1000+count*150;explanation=`النمط الصحيح هو ${correct}.`;}
 else if(mode==='sequence_memory'){const pool=['●','▲','■','◆','★','☀'],len=4+stage,seq=shuffle(pool,rnd).slice(0,Math.min(len,pool.length)),correct=seq.join(' ');prompt='اختر ترتيب الرموز الصحيح';answer=correct;options=shuffle(unique([correct,[...seq].reverse().join(' '),[...seq.slice(1),seq[0]].join(' '),[seq[1],seq[0],...seq.slice(2)].join(' ')]),rnd);study=seq.join('  ');studyMs=1000+seq.length*180;explanation=`الترتيب الصحيح هو ${correct}.`;}
 else if(mode==='paired_associates'){const pairs=[['قمر','ليل'],['شمس','نهار'],['مفتاح','باب'],['كتاب','قراءة'],['مطر','مظلة'],['بحر','موج']],pick=shuffle(pairs,rnd).slice(0,3+Math.min(stage,2)),target=pick[Math.floor(rnd()*pick.length)];prompt=`ما الكلمة المرتبطة بـ «${target[0]}»؟`;answer=target[1];options=shuffle(unique([answer,...shuffle(pairs.map(x=>x[1]).filter(x=>x!==answer),rnd).slice(0,3)]),rnd);study=pick.map(x=>`${x[0]} — ${x[1]}`).join(' | ');studyMs=1400+pick.length*250;explanation=`الشريك الصحيح هو ${answer}.`;}
 else if(mode==='symbol_memory'){const pool=['●','▲','■','◆','★','☀','✚','⬟'],seen=shuffle(pool,rnd).slice(0,3+stage),target=(index+stage)%2?seen[Math.floor(rnd()*seen.length)]:pool.find(x=>!seen.includes(x));prompt=`هل كان الرمز ${target} ضمن المجموعة؟`;answer=seen.includes(target)?'نعم':'لا';options=['نعم','لا'];study=seen.join('  ');studyMs=1000+seen.length*160;explanation=seen.includes(target)?'الرمز كان ضمن مجموعة الدراسة.':'الرمز لم يكن ضمن مجموعة الدراسة.';}
'''

def patch_page(slug,title,cat,mode,instruction):
 p=SITE/'cognitive-lab'/slug/'index.html';t=p.read_text(encoding='utf-8');m=re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>',t,re.S)
 if not m: raise SystemExit(f'missing definition: {slug}')
 d=json.loads(m.group(1));new={**d,'title':title,'category':cat,'summary':SUM[slug],'mode':mode,'stages':5,'trials_per_stage':7,'instructions':instruction,'version':22};payload=json.dumps(new,ensure_ascii=False,separators=(',',':')).replace('</','<\\/');t=t[:m.start(1)]+payload+t[m.end(1):];t=t.replace(d.get('title',''),title).replace(d.get('summary',''),SUM[slug]);marker='<div class="question"><strong>مهم:</strong>'
 if instruction not in t:t=t.replace(marker,f'<div class="question"><strong>طريقة الاستخدام:</strong> {instruction}</div>{marker}',1)
 p.write_text(t,encoding='utf-8')

def main():
 for row in TOOLS:patch_page(*row)
 idx=SITE/'cognitive-lab/index.html';t=idx.read_text(encoding='utf-8')
 for slug,title,cat,mode,ins in TOOLS:
  pat=rf'(<a class="lab-v12__card" href="[^"]*{slug}[^"]*">.*?<h2>)(.*?)(</h2><p>)(.*?)(</p>)';t,n=re.subn(pat,lambda m:m.group(1)+title+m.group(3)+SUM[slug]+m.group(5),t,count=1,flags=re.S)
  if n!=1:raise SystemExit(f'card patch failed {slug}')
 idx.write_text(t,encoding='utf-8')
 js=SITE/'assets/js/lab-v12.js';s=js.read_text(encoding='utf-8')
 decl="audioCount=0,delay=0;"
 if decl not in s: raise SystemExit('trial state declaration not found')
 s=s.replace(decl,"audioCount=0,delay=0,study='',studyMs=0;",1)
 marker=" else if(/السرعة/.test(mode)||/reaction|auditory-symbol/.test(slug))"
 if marker not in s: raise SystemExit('fallback insertion marker not found')
 s=s.replace(marker,BRANCH+marker,1)
 pattern=r"started=now\(\);stim\.innerHTML=`<div class=\"trial-card\"><p>\$\{current\.prompt\}</p>"
 replacement="if(current.study){stim.innerHTML=`<div class=\"trial-card\"><p>${current.study}</p></div>`;await new Promise(r=>setTimeout(r,current.studyMs||1200));}started=now();stim.innerHTML=`<div class=\"trial-card\"><p>${current.prompt}</p>"
 s,n=re.subn(pattern,replacement,s,count=1)
 if n!=1:raise SystemExit('study phase patch failed')
 js.write_text(s,encoding='utf-8')
 report={'version':22,'batch':2,'count':10,'distinct_modes':10,'stages':50,'trials':350,'slugs':[x[0] for x in TOOLS]};api=SITE/'api';api.mkdir(exist_ok=True);(api/'cognitive-batch2-v22.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
