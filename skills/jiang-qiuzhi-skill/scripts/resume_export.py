#!/usr/bin/env python3
"""Evidence-aware resume HTML/TXT export and optional browser-based A4 PDF."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

FORBIDDEN = ['【待补', '{{', '}}', 'TODO', 'TBD', '<待填写>']
STRONG_WORDS = ['主导', '独立完成', '精通', '熟练掌握', '带领团队', '显著提升']


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict): raise ValueError('Input JSON must be an object.')
    return value


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def numeric_tokens(text: str) -> set[str]:
    # Detect most newly introduced metrics; not a semantic truth proof.
    # Normalize zero-padding in dates and equivalent 2023.09 / 2023年9月 formats.
    return {str(int(x)) if re.fullmatch(r'\d+', x) else x for x in re.findall(r'\d+(?:\.\d+)?(?:%|万|亿|倍)?', re.sub(r'(20\d{2})[./-](0?[1-9]|1[0-2])', r'\1年\2月', text))}


def validate_resume(resume: dict, profile: dict) -> dict:
    for required in ('name', 'target', 'version'):
        if not isinstance(resume.get(required), str) or not resume[required].strip():
            raise ValueError(f'Missing resume field: {required}')
    if not isinstance(resume.get('contact', []), list) or any(not isinstance(x,str) for x in resume.get('contact', [])):
        raise ValueError('contact must be an array of strings.')
    sections = resume.get('sections')
    if not isinstance(sections, list) or not sections:
        raise ValueError('At least one resume section is required.')
    facts = profile.get('facts', [])
    by_id = {f['id']: f for f in facts if isinstance(f,dict) and f.get('id')}
    if len(by_id) != len(facts): raise ValueError('Duplicate or invalid fact IDs.')
    errors, lines = [], 0
    # Cover visible contact/header text, not private metadata such as source paths.
    visible = [resume['name'], resume['target'], *resume.get('contact', [])]
    for section in sections:
        if not isinstance(section,dict) or not section.get('heading') or not isinstance(section.get('entries'),list):
            raise ValueError('Each section needs heading and entries.')
        visible.append(str(section['heading']))
        for entry in section['entries']:
            exp = entry.get('experience_id')
            units = [{'text': str(entry.get('title',''))+' '+str(entry.get('period','')), 'fact_ids': entry.get('fact_ids', [])}]
            units += entry.get('bullets', [])
            for unit in units:
                text = unit.get('text','')
                if not isinstance(text, str): raise ValueError('Resume bullet text must be a string.')
                refs = unit.get('fact_ids', [])
                visible.append(text); lines += 1
                if not refs:
                    errors.append('Every entry title/bullet requires fact_ids.'); continue
                evidence = []
                for fid in refs:
                    f = by_id.get(fid)
                    if not f or f.get('confirmed') is not True:
                        errors.append(f'Missing or unconfirmed fact: {fid}'); continue
                    if not exp or f.get('experience_id') != exp:
                        errors.append(f'Cross-experience fact reference: {fid}'); continue
                    evidence.append(f.get('text',''))
                source = '\n'.join(evidence)
                for token in numeric_tokens(text)-numeric_tokens(source):
                    errors.append(f'New numeric token without cited evidence: {token}')
                for word in STRONG_WORDS:
                    if word in text and word not in source:
                        errors.append(f'Unsupported stronger claim: {word}')
    for marker in FORBIDDEN:
        if marker in '\n'.join(visible): errors.append(f'Unresolved placeholder: {marker}')
    if errors: raise ValueError('; '.join(dict.fromkeys(errors)))
    return {'fact_reference_checks_passed': True, 'units_checked': lines, 'semantic_truth_guaranteed': False, 'human_fact_review_required': True}


def render_html(resume: dict, css: str, demo: bool, approved: bool) -> tuple[str,str]:
    esc = html.escape
    banner = '虚构演示材料 · 不可投递' if demo else '' if approved else '待用户确认的简历草稿 · 不可直接投递'
    plain = [banner] if banner else []
    plain += [resume['name'], resume['target'], ' | '.join(resume.get('contact', []))]
    chunks = [f'<aside class="notice">{esc(banner)}</aside>' if banner else '', '<header>', f'<h1>{esc(resume["name"])}</h1>', f'<p class="target">{esc(resume["target"])}</p>', f'<p class="contact">{esc(" | ".join(resume.get("contact", [])))}</p>', '</header>']
    for section in resume['sections']:
        chunks.append(f'<section><h2>{esc(section["heading"])}</h2>')
        plain += ['', section['heading']]
        for entry in section['entries']:
            chunks.append('<article><div class="entry-head"><h3>'+esc(entry['title'])+'</h3><span>'+esc(entry.get('period',''))+'</span></div>')
            plain.append(entry['title']+' '+entry.get('period',''))
            if entry.get('bullets'):
                chunks.append('<ul>')
                for bullet in entry['bullets']:
                    chunks.append('<li>'+esc(bullet['text'])+'</li>'); plain.append('- '+bullet['text'])
                chunks.append('</ul>')
            chunks.append('</article>')
        chunks.append('</section>')
    doc = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; font-src \'none\'"><title>'+esc(resume['name'])+' · 简历</title><style>'+css+'</style></head><body>'+''.join(chunks)+'</body></html>'
    return doc, '\n'.join(plain).strip()+'\n'


def export_pdf(html_path: Path, pdf_path: Path, browser_path: str, sandbox: bool = True) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise ValueError('Optional PDF dependency playwright is missing. HTML/TXT are available; obtain permission before installing.') from e
    if not browser_path or not Path(browser_path).is_file():
        raise ValueError('An existing Chromium browser --browser path is required. No browser will be downloaded automatically.')
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=browser_path, headless=True, chromium_sandbox=sandbox)
        try:
            page = browser.new_page()
            # Block network regardless of document content. Only local static HTML is used.
            page.route(re.compile(r'^https?://'), lambda route: route.abort())
            page.set_content(html_path.read_text(encoding='utf-8'), wait_until='load')
            page.evaluate('document.fonts.ready')
            page.pdf(path=str(pdf_path), format='A4', prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()


def check_pdf(path: Path, expected_name: str, max_pages: int) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise ValueError('Optional PDF check dependency pypdf is missing. PDF cannot be marked verified.') from e
    pdf = PdfReader(path)
    errors = []
    if not 1 <= len(pdf.pages) <= max_pages: errors.append(f'Unexpected page count: {len(pdf.pages)}')
    text = '\n'.join(p.extract_text() or '' for p in pdf.pages)
    sizes = []
    for i, page in enumerate(pdf.pages,1):
        width,height = float(page.mediabox.width),float(page.mediabox.height)
        sizes.append([round(width,2), round(height,2)])
        if abs(width-595.28)>1 or abs(height-841.89)>1: errors.append(f'Page {i} is not A4 portrait.')
    if not text.strip(): errors.append('No extractable text.')
    if re.sub(r'\s','',unicodedata.normalize('NFKC',expected_name)) not in re.sub(r'\s','',unicodedata.normalize('NFKC',text)): errors.append('Expected name is not extractable.')
    if any(x in text for x in FORBIDDEN): errors.append('Unresolved visible placeholders.')
    return {'passed':not errors,'page_count':len(pdf.pages),'page_sizes_pt':sizes,'text_characters':len(text),'errors':errors,'visual_check':'not_performed_by_this_script'}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True); p.add_argument('--facts',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--approved',action='store_true'); p.add_argument('--demo',action='store_true'); p.add_argument('--pdf',action='store_true'); p.add_argument('--browser'); p.add_argument('--max-pages',type=int,default=1,choices=[1,2])
    a=p.parse_args()
    try:
        if a.out.exists() and any(a.out.iterdir()): raise ValueError('Output directory must be new or empty; existing resume versions are never overwritten.')
        resume,profile=load(a.input),load(a.facts)
        qa=validate_resume(resume,profile)
        a.out.mkdir(parents=True,exist_ok=True)
        css=(Path(__file__).resolve().parents[1]/'assets/resume.css').read_text(encoding='utf-8')
        h,t=render_html(resume,css,a.demo,a.approved)
        (a.out/'resume.html').write_text(h,encoding='utf-8'); (a.out/'resume.txt').write_text(t,encoding='utf-8')
        qa['pdf_checks']={'passed':False,'status':'not_requested'}
        error=None
        if a.pdf:
            try:
                export_pdf(a.out/'resume.html',a.out/'resume.pdf',a.browser or '')
                qa['pdf_checks']=check_pdf(a.out/'resume.pdf',resume['name'],a.max_pages)
                if not qa['pdf_checks']['passed']: error='PDF validation failed.'
            except Exception as e:
                error=str(e); qa['pdf_checks']={'passed':False,'status':'failed','error':error}
        save(a.out/'qa.json',qa)
        files={f.name:fingerprint(f) for f in a.out.iterdir() if f.is_file()}
        manifest={'version':resume['version'],'job_id':resume.get('job_id'),'jd_reference':resume.get('jd_reference'),'demo':a.demo,'approved_for_use':bool(a.approved and not a.demo),'visual_checked':False,'files':files}
        save(a.out/'manifest.json',manifest)
        print(json.dumps({'output':str(a.out.resolve()),'html_txt_created':True,'pdf_verified':qa['pdf_checks'].get('passed',False),'visual_check_required':True,'error':error},ensure_ascii=False,indent=2))
        return 2 if error else 0
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as e:
        print(json.dumps({'error':str(e),'completed':False},ensure_ascii=False),file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
