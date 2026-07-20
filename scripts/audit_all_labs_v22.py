from __future__ import annotations
import hashlib, json, re, sys
from collections import defaultdict
from pathlib import Path

SITE=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
OUT=SITE/'api'/'all-labs-v22.json'
AR_DIAC=re.compile(r'[\u064b-\u065f\u0670]')

def norm(v:object)->str:
    s=AR_DIAC.sub('',str(v or '').lower())
    s=s.replace('أ','ا').replace('إ','ا').replace('آ','ا').replace('ى','ي').replace('ة','ه')
    return re.sub(r'[^\w\u0600-\u06ff]+',' ',s).strip()

def definition(path:Path)->dict:
    text=path.read_text(encoding='utf-8')
    m=re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>',text,re.S)
    if not m: raise ValueError('missing lab-definition')
    return json.loads(m.group(1))

def main()->None:
    errors=[]; warnings=[]; rows=[]
    groups={'assessment':sorted((SITE/'assessment-lab').glob('*/index.html')),'cognitive':sorted((SITE/'cognitive-lab').glob('*/index.html'))}
    if len(groups['assessment'])!=40: errors.append(f"assessment count {len(groups['assessment'])} != 40")
    if len(groups['cognitive'])!=48: errors.append(f"cognitive count {len(groups['cognitive'])} != 48")
    seen_slug={}; seen_title={}; signatures=defaultdict(list); question_signatures=defaultdict(list)
    for kind,pages in groups.items():
        for page in pages:
            rel=page.relative_to(SITE).as_posix()
            try: d=definition(page)
            except Exception as exc: errors.append(f'{rel}: {exc}'); continue
            slug=str(d.get('slug','')).strip(); title=str(d.get('title','')).strip(); category=str(d.get('category','')).strip(); mode=str(d.get('mode','')).strip()
            if not slug or not title: errors.append(f'{rel}: missing slug/title')
            if slug in seen_slug: errors.append(f'duplicate slug {slug}: {seen_slug[slug]} / {rel}')
            seen_slug[slug]=rel
            nt=norm(title)
            if nt in seen_title: errors.append(f'duplicate normalized title {title}: {seen_title[nt]} / {rel}')
            seen_title[nt]=rel
            payload={k:v for k,v in d.items() if k not in {'slug','title','description'}}
            sig=hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
            signatures[(kind,sig)].append(rel)
            row={'kind':kind,'slug':slug,'title':title,'category':category,'mode':mode,'path':rel}
            if kind=='assessment':
                qs=d.get('questions'); opts=d.get('options')
                if not isinstance(qs,list) or len(qs)<3: errors.append(f'{rel}: fewer than 3 questions')
                if not isinstance(opts,list) and not all(isinstance(q,dict) and isinstance(q.get('options'),list) for q in (qs or [])): errors.append(f'{rel}: options missing')
                normalized_questions=[]
                for i,q in enumerate(qs or []):
                    text=q if isinstance(q,str) else q.get('text','') if isinstance(q,dict) else ''
                    nq=norm(text)
                    if len(nq)<8: errors.append(f'{rel}: question {i+1} too short')
                    normalized_questions.append(nq)
                    question_signatures[nq].append(f'{rel}#{i+1}')
                if len(normalized_questions)!=len(set(normalized_questions)): errors.append(f'{rel}: repeated questions inside assessment')
                if not d.get('score_type'): warnings.append(f'{rel}: no explicit score_type; generic interpretation only')
                row.update(questions=len(qs or []),score_type=d.get('score_type','generic'))
            else:
                stages=int(d.get('stages',5) or 0); trials=int(d.get('trials_per_stage',6) or 0)
                if stages<3: errors.append(f'{rel}: stages {stages} < 3')
                if trials<4: errors.append(f'{rel}: trials_per_stage {trials} < 4')
                if not (mode or category): errors.append(f'{rel}: no mode/category')
                row.update(stages=stages,trials_per_stage=trials,total_trials=stages*trials)
            rows.append(row)
    for (kind,sig),paths in signatures.items():
        if len(paths)>1: errors.append(f'probable duplicate {kind} definitions: {paths}')
    repeated_cross={q:locs for q,locs in question_signatures.items() if q and len(locs)>=3}
    for q,locs in list(repeated_cross.items())[:100]: warnings.append(f'repeated question text across assessments ({len(locs)}): {q[:90]} -> {locs[:6]}')
    report={'version':22,'assessment_count':len(groups['assessment']),'cognitive_count':len(groups['cognitive']),'tools':rows,'error_count':len(errors),'errors':errors,'warning_count':len(warnings),'warnings':warnings}
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if errors: raise SystemExit('\n'.join(errors[:100]))
if __name__=='__main__': main()
