from __future__ import annotations
import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
JS = SITE / 'assets/js/lab-v12.js'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f'missing patch target: {label}')
    return text.replace(old, new, 1)


def main() -> None:
    text = JS.read_text(encoding='utf-8')

    full_decl = "let prompt='',options=[],answer='',kind='text',explanation='',audioCount=0,delay=0,study='',studyMs=0,stimulusWord='',stimulusInk='',stimulusRule='';"
    declaration_candidates = [
        "let prompt='',options=[],answer='',kind='text',explanation='',audioCount=0,delay=0;",
        "let prompt='',options=[],answer='',kind='text',explanation='',audioCount=0,delay=0,study='',studyMs=0;",
    ]
    if full_decl not in text:
        for candidate in declaration_candidates:
            if candidate in text:
                text = text.replace(candidate, full_decl, 1)
                break
        else:
            raise SystemExit('missing patch target: trial metadata declaration')

    old_basic = r'''else if(mode==='stroop_basic'){const word=COLORS[Math.floor(rnd()*COLORS.length)],ink=COLORS[(Math.floor(rnd()*COLORS.length)+(index%2?1:0))%COLORS.length];prompt=`اختر لون الحبر لا معنى الكلمة: ${word.label}`;answer=ink.value;options=shuffle(COLORS,rnd);kind='stroop';explanation=`لون الحبر المستهدف هو ${ink.label}.`;}'''
    new_basic = r'''else if(mode==='stroop_basic'){const wi=(stage+index)%COLORS.length,ii=(stage*2+index+1)%COLORS.length,word=COLORS[wi],ink=COLORS[ii===wi?(ii+1)%COLORS.length:ii];prompt=`اختر لون الحبر لا معنى الكلمة: <span class="stroop-word" data-word="${word.value}" data-ink="${ink.value}" style="color:${ink.hex};font-weight:900;font-size:1.35em">${word.label}</span>`;answer=ink.value;options=shuffle(COLORS,rnd);kind='stroop';stimulusWord=word.value;stimulusInk=ink.value;explanation=`اسم الكلمة ${word.label}، لكن لون الحبر المستهدف هو ${ink.label}.`;}'''
    text = replace_once(text, old_basic, new_basic, 'stroop basic')

    old_adv = r'''else if(mode==='stroop_advanced'){const word=COLORS[Math.floor(rnd()*COLORS.length)],ink=COLORS[Math.floor(rnd()*COLORS.length)],useInk=(stage+index)%2===0;prompt=`القاعدة: اختر ${useInk?'لون الحبر':'معنى الكلمة'}. الكلمة: ${word.label}`;answer=useInk?ink.value:word.value;options=shuffle(COLORS,rnd);kind='stroop';explanation=`طُبقت قاعدة ${useInk?'لون الحبر':'معنى الكلمة'}، والإجابة ${answer}.`;}'''
    new_adv = r'''else if(mode==='stroop_advanced'){const wi=(stage+index)%COLORS.length,ii=(stage*2+index+2)%COLORS.length,word=COLORS[wi],ink=COLORS[ii===wi?(ii+1)%COLORS.length:ii],useInk=(stage+index)%2===0;prompt=`القاعدة: اختر ${useInk?'لون الحبر':'معنى الكلمة'}: <span class="stroop-word" data-word="${word.value}" data-ink="${ink.value}" style="color:${ink.hex};font-weight:900;font-size:1.35em">${word.label}</span>`;answer=useInk?ink.value:word.value;options=shuffle(COLORS,rnd);kind='stroop';stimulusWord=word.value;stimulusInk=ink.value;stimulusRule=useInk?'ink':'word';explanation=`اسم الكلمة ${word.label} ولون الحبر ${ink.label}. طُبقت قاعدة ${useInk?'لون الحبر':'معنى الكلمة'}، والإجابة ${answer}.`;}'''
    text = replace_once(text, old_adv, new_adv, 'stroop advanced')

    old_generic = r'''else if(/الكبح/.test(mode)||/go-no-go|stroop|inhibition/.test(slug)){const word=COLORS[Math.floor(rnd()*COLORS.length)],ink=COLORS[Math.floor(rnd()*COLORS.length)];prompt=`اختر لون الحبر لا معنى الكلمة: ${word.label}`;answer=ink.value;options=shuffle(COLORS,rnd);kind='stroop';explanation=`لون الحبر المستهدف هو ${ink.label}.`;}'''
    new_generic = r'''else if(/الكبح/.test(mode)||/go-no-go|stroop|inhibition/.test(slug)){const wi=(stage+index)%COLORS.length,ii=(stage+index+1)%COLORS.length,word=COLORS[wi],ink=COLORS[ii];prompt=`اختر لون الحبر لا معنى الكلمة: <span class="stroop-word" data-word="${word.value}" data-ink="${ink.value}" style="color:${ink.hex};font-weight:900">${word.label}</span>`;answer=ink.value;options=shuffle(COLORS,rnd);kind='stroop';stimulusWord=word.value;stimulusInk=ink.value;explanation=`اسم الكلمة ${word.label} ولون الحبر ${ink.label}.`;}'''
    text = replace_once(text, old_generic, new_generic, 'generic inhibition')

    old_return = 'return{prompt,options,answer,kind,explanation,audioCount,delay};'
    new_return = 'return{prompt,options,answer,kind,explanation,audioCount,delay,study,studyMs,stimulusWord,stimulusInk,stimulusRule};'
    text = replace_once(text, old_return, new_return, 'trial metadata return')

    JS.write_text(text, encoding='utf-8')
    report = {
        'version': 23,
        'stroop_basic_varies': True,
        'stroop_advanced_varies': True,
        'advanced_word_colors': 4,
        'advanced_ink_colors': 4,
        'ink_rendered_inline': True,
        'metadata_declared': True,
        'study_metadata_preserved': True,
        'idempotent_patch': True,
    }
    api = SITE / 'api'
    api.mkdir(exist_ok=True)
    (api / 'stroop-variation-v23.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
