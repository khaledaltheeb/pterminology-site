from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
JS = SITE / 'assets/js/lab-v12.js'

PATCHES = [
    (
        "else if(mode==='choice_reaction'){const target=arrows[Math.floor(rnd()*4)];",
        "else if(mode==='choice_reaction'){const target=arrows[(stage+index)%arrows.length];",
        'choice reaction directions',
    ),
    (
        "else if(mode==='auditory_symbol'){audioCount=1+Math.floor(rnd()*4);",
        "else if(mode==='auditory_symbol'){audioCount=1+((stage+index)%4);",
        'auditory symbol tone counts',
    ),
    (
        "const shown=symbols[Math.floor(rnd()*symbols.length)];const go=targets.includes(shown);prompt=`القاعدة: استجب للرموز ${targets.join('، ')}. المثير الحالي: ${shown}`;",
        "const shown=symbols[(stage+index)%symbols.length];const go=targets.includes(shown);prompt=`القاعدة: استجب للرموز ${targets.join('، ')}. المثير الحالي: ${shown}`;",
        'go no-go stimuli',
    ),
]


def main() -> None:
    if not JS.exists():
        raise SystemExit(f'Missing cognitive runtime: {JS}')
    text = JS.read_text(encoding='utf-8')
    changed = []
    for old, new, label in PATCHES:
        if new in text:
            changed.append(label + ':already')
            continue
        if old not in text:
            raise SystemExit(f'Missing cognitive variation target: {label}')
        text = text.replace(old, new, 1)
        changed.append(label + ':patched')
    JS.write_text(text, encoding='utf-8')
    report = {
        'version': 25,
        'patched_tools': ['choice-reaction', 'auditory-symbol', 'go-no-go'],
        'first_five_variation_required': True,
        'changes': changed,
    }
    api = SITE / 'api'
    api.mkdir(parents=True, exist_ok=True)
    (api / 'initial-cognitive-variation-v25.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
