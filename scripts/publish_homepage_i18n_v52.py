#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/i18n/v52/homepage.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site"

CSS = """body{margin:0;font-family:Arial,Tahoma,sans-serif;line-height:1.7;color:#173f45;background:#f7fffd}.wrap{width:min(1100px,92%);margin:auto}header{display:flex;justify-content:space-between;gap:1rem;padding:1rem 0;border-bottom:1px solid #c9e9e5}.nav{display:flex;gap:.8rem;flex-wrap:wrap}.hero,.section{padding:2.5rem 0}.cards,.quality,.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}.card,.stat,.quality div,.notice{background:#fff;border:1px solid #c9e9e5;border-radius:1rem;padding:1rem}.notice{border-inline-start:5px solid #b9537d}.skip{position:absolute;inset-inline-start:-9999px}.skip:focus{inset-inline-start:1rem;top:1rem}.lang{font-weight:700}.lang a{margin-inline:.35rem}@media(max-width:800px){.cards,.quality,.stats{grid-template-columns:1fr}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render(locale: str, page: dict) -> str:
    cards = "".join(
        f'<article class="card"><h3>{esc(title)}</h3><p>{esc(text)}</p><a href="{esc(href)}">{esc(label)}</a></article>'
        for title, text, label, href in page["sections"]["cards"]
    )
    stats = "".join(f'<div class="stat"><strong>{esc(n)}</strong><br>{esc(t)}</div>' for n, t in page["stats"])
    quality = "".join(f'<div><strong>{esc(t)}</strong><br>{esc(d)}</div>' for t, d in page["sections"]["quality"])
    canonical = f"{BASE}/{locale}/"
    other = "es" if locale == "en" else "en"
    return f'''<!doctype html>
<html lang="{locale}" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(page['title'])}</title><meta name="description" content="{esc(page['description'])}"><meta name="robots" content="index,follow">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ar" href="{BASE}/"><link rel="alternate" hreflang="en" href="{BASE}/en/"><link rel="alternate" hreflang="es" href="{BASE}/es/"><link rel="alternate" hreflang="x-default" href="{BASE}/">
<meta property="og:type" content="website"><meta property="og:locale" content="{locale}_{'US' if locale == 'en' else 'ES'}"><meta property="og:url" content="{canonical}"><meta property="og:title" content="{esc(page['title'])}"><meta property="og:description" content="{esc(page['description'])}">
<style>{CSS}</style></head><body><a class="skip" href="#main">Skip to main content</a><div class="wrap"><header><a href="../">Psychology Terminology</a><nav class="nav" aria-label="Primary"><a href="../encyclopedia/">Encyclopedia</a><a href="../tips/">Guides</a><a href="../assessment-lab/">Assessments</a><a href="../cognitive-lab/">Cognitive lab</a></nav><div class="lang" aria-label="Language"><a lang="ar" dir="rtl" href="../">العربية</a><a lang="{other}" href="../{other}/">{other.upper()}</a></div></header>
<main id="main"><section class="hero"><p>{esc(page['eyebrow'])}</p><h1>{esc(page['heading'])}</h1><p>{esc(page['lead'])}</p><div class="notice" role="note">{esc(page['notice'])}</div></section><section class="stats" aria-label="Platform size">{stats}</section><section class="section"><h2>{esc(page['sections']['discover_title'])}</h2><p>{esc(page['sections']['discover_intro'])}</p><div class="cards">{cards}</div></section><section class="section"><h2>{esc(page['sections']['quality_title'])}</h2><div class="quality">{quality}</div></section><section class="section"><h2>{esc(page['sections']['media_title'])}</h2><p>{esc(page['sections']['media_intro'])}</p></section></main><footer><p>{esc(page['footer'])}</p></footer></div></body></html>'''


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    required = data["required_fields"]
    for locale in ("en", "es"):
        page = data["locales"][locale]
        missing = [field for field in required if not page.get(field)]
        if page.get("status") != "translated" or missing:
            raise SystemExit(f"Refusing incomplete locale {locale}: {missing}")
        target = ROOT / locale / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(locale, page), encoding="utf-8")


if __name__ == "__main__":
    main()
