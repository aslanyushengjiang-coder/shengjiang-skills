#!/usr/bin/env python3
"""Fill bundled SVG templates or perform an allowlisted festival revision.

Local files only. No image generation, browser, network, raster export or publish.
All source images are embedded byte-for-byte so an output SVG is portable.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'assets/templates'
STYLE_ONLY_HASH = '7cd7449e0980dfdfd1bc237c97857286c08fdc57f694a7150709f9060e8c45d9'
PLACEHOLDER = re.compile(r'\{\{([a-z0-9_]+)\}\}')
HEX_COLOR = re.compile(r'#[0-9a-fA-F]{6}\Z')
TRUTH_STATUSES = {'fictional_demo', 'real_store_unverified', 'real_store_confirmed'}
DISH_SOURCE_ROLES = {'authoritative-dish', 'demo-fixture'}
LIMITS = {
    'store_name': 20, 'item_id': 24, 'headline_1': 14, 'headline_2': 14,
    'headline': 11, 'offer_line': 21, 'rule_1': 34, 'rule_2': 34, 'rule_3': 34,
    'rule_4': 34, 'dish_name': 16, 'spec_line': 28, 'price_line': 18,
    'date': 22, 'truth_disclosure': 43, 'accessibility_label': 100,
}
COLOR_KEYS = {'brand_ink', 'paper_color', 'photo_well_color', 'background_color', 'decoration_color', 'footer_color'}
CONFIG = {
    'top-space-poster': {'required': {'store_name', 'headline_1', 'brand_ink'},
        'text': {'store_name', 'headline_1', 'headline_2', 'offer_line', 'rule_1', 'rule_2', 'rule_3', 'rule_4'},
        'images': {'dish_image': 'dish_data_uri', 'background_image': 'background_data_uri'}},
    'dish-photo-card': {'required': {'store_name', 'item_id', 'dish_name', 'brand_ink', 'paper_color', 'photo_well_color'},
        'text': {'store_name', 'item_id', 'dish_name', 'spec_line', 'price_line'},
        'images': {'dish_image': 'dish_data_uri'}},
    'festival-locked': {'required': {'store_name', 'headline', 'date', 'brand_ink', 'background_color', 'decoration_color', 'footer_color'},
        'text': {'store_name', 'headline', 'date', 'price_line'},
        'images': {'dish_image': 'dish_data_uri'}},
}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict): fail('Input must be a JSON object.')
    return value


def exact_text(key: str, value: object, required: bool = False) -> str:
    if not isinstance(value, str): fail(f'{key} must be a string; preserve exact supplied copy.')
    if required and not value.strip(): fail(f'blocked-missing-fact: {key}')
    if value.strip().lower() in {'unknown', '待确认', '待补充', '待定'}:
        fail(f'blocked-missing-fact: {key}; omit an optional line instead of fabricating it.')
    if '\n' in value or '\r' in value or any(ord(c) < 32 for c in value):
        fail(f'{key} must be one line; use the separate line fields.')
    if len(value) > LIMITS.get(key, 100): fail(f'{key} exceeds its template length budget; shorten copy or choose another template, never silently truncate.')
    return value


def embed_image(value: object, base_dir: Path, role: str) -> tuple[str, dict]:
    if not isinstance(value, str) or not value: fail(f'blocked-missing-input: {role}')
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', value) and not re.match(r'^[a-zA-Z]:[\\/]', value):
        fail(f'{role} must be a local file, not a URL or data URI.')
    path = (base_dir / value).resolve()
    if not path.is_file(): fail(f'blocked-missing-input: {role}: {path.name}')
    raw = path.read_bytes()
    if len(raw) > 32 * 1024 * 1024: fail(f'{role} exceeds 32 MiB.')
    sha = hashlib.sha256(raw).hexdigest()
    if role in {'dish_image', 'background_image'} and sha == STYLE_ONLY_HASH:
        fail('style-reference-only: the bundled tomato-beef composition is not a SKU photo or an empty background.')
    if raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw) >= 33 and raw[12:16] == b'IHDR':
        mime = 'image/png'
        width, height = struct.unpack('>II', raw[16:24])
        if not width or not height: fail(f'Invalid PNG dimensions: {role}')
    elif raw.startswith(b'\xff\xd8\xff') and raw.endswith(b'\xff\xd9'):
        mime = 'image/jpeg'
        width = height = None
    else:
        fail(f'{role} must be a PNG or JPEG file; SVG/HTML/remote references are not accepted as image input.')
    return 'data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii'), {
        'role': role, 'source_name': path.name, 'sha256': sha, 'bytes': len(raw),
        'mime': mime, 'width': width, 'height': height, 'embedded_without_reencoding': True,
    }


def xml_escape(value: str) -> str:
    return html.escape(value, quote=True)


def write_output(output: Path, svg: str, manifest: dict) -> dict:
    root = ET.fromstring(svg)
    if PLACEHOLDER.search(svg): fail('Unresolved placeholder in output.')
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] in {'script', 'foreignObject'}: fail('Active SVG content is forbidden.')
        for key, value in node.attrib.items():
            if key.lower().startswith('on'): fail('SVG event handlers are forbidden.')
            if key.rsplit('}', 1)[-1] == 'href' and not value.startswith(('data:image/png;base64,', 'data:image/jpeg;base64,')):
                fail('All image references must be embedded; output contains an external reference.')
    manifest_path = output.with_suffix('.manifest.json')
    if output.exists() or manifest_path.exists(): fail('Output already exists; choose a new name to preserve the original.')
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest.update({'output_file': output.name, 'output_sha256': hashlib.sha256(svg.encode()).hexdigest(),
        'source_ready': True, 'raster_exported': False, 'visual_checked': False,
        'user_approved': False, 'published': False, 'status': 'source-ready-pending-visual',
        'image_generation_calls': 0, 'image_bytes_preserved': True})
    output.write_text(svg, encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def render(template: str, data_path: Path, output: Path) -> dict:
    cfg = CONFIG[template]
    data = load_json(data_path)
    allowed = cfg['text'] | cfg['required'] | set(cfg['images']) | {'facts_source', 'source_role', 'truth_status', 'truth_disclosure', 'accessibility_label'}
    if template == 'festival-locked': allowed |= {'logo_image', 'qr_image'}
    extra = set(data) - allowed
    if extra: fail('Unknown fields: ' + ', '.join(sorted(extra)))
    if not isinstance(data.get('facts_source'), str) or not data['facts_source'].strip(): fail('blocked-missing-fact: facts_source')
    if data.get('source_role') not in DISH_SOURCE_ROLES:
        fail('source_role for dish_image must be authoritative-dish or demo-fixture; style-only is not a SKU source.')
    if data.get('truth_status') not in TRUTH_STATUSES: fail('truth_status must explicitly distinguish fictional demo from a real store.')
    if data['source_role'] == 'demo-fixture' and data['truth_status'] != 'fictional_demo':
        fail('demo-fixture cannot be upgraded to a real-store fact.')
    disclosure = exact_text('truth_disclosure', data.get('truth_disclosure', ''), True)
    if data['truth_status'] == 'fictional_demo' and not ('虚构' in disclosure and '演示' in disclosure):
        fail('Fictional examples must visibly disclose 虚构演示.')
    values = {}
    for key in cfg['text']:
        values[key] = xml_escape(exact_text(key, data.get(key, ''), key in cfg['required']))
    for key in cfg['required'] & COLOR_KEYS:
        value = data.get(key, '')
        if not isinstance(value, str) or not HEX_COLOR.fullmatch(value): fail(f'{key} must be a supplied #RRGGBB color.')
        values[key] = value
    values['truth_disclosure'] = xml_escape(disclosure)
    values['accessibility_label'] = xml_escape(exact_text('accessibility_label', data.get('accessibility_label', disclosure), True))
    images = []
    for source_key, token in cfg['images'].items():
        values[token], info = embed_image(data.get(source_key), data_path.parent, source_key)
        info['source_role'] = data['source_role'] if source_key == 'dish_image' else 'style-only'
        images.append(info)
    if template == 'festival-locked':
        if data.get('logo_image'):
            uri, info = embed_image(data['logo_image'], data_path.parent, 'logo_image'); images.append(info)
            values['logo_layer'] = '<image href="' + uri + '" x="90" y="80" width="360" height="110" preserveAspectRatio="xMidYMid meet"/>'
        else:
            values['logo_layer'] = '<text x="90" y="151" font-family="PingFang SC, Microsoft YaHei, sans-serif" font-size="42" fill="' + values['brand_ink'] + '">' + values['store_name'] + '</text>'
        if data.get('qr_image'):
            uri, info = embed_image(data['qr_image'], data_path.parent, 'qr_image'); images.append(info)
            values['qr_layer'] = '<image href="' + uri + '" width="170" height="170" preserveAspectRatio="xMidYMid meet"/>'
        else: values['qr_layer'] = ''
    raw = (TEMPLATES / (template + '.svg')).read_text(encoding='utf-8')
    missing = set(PLACEHOLDER.findall(raw)) - set(values)
    if missing: fail('Template fields not filled: ' + ', '.join(sorted(missing)))
    svg = PLACEHOLDER.sub(lambda match: values[match.group(1)], raw)
    return write_output(output, svg, {'template': template, 'source_role': data['source_role'], 'truth_status': data['truth_status'],
        'facts_source': data['facts_source'], 'exact_copy': {k: data.get(k, '') for k in sorted(cfg['text'])},
        'images': images, 'all_images_embedded': True,
        'logo_status': 'provided-not-visually-checked' if data.get('logo_image') else 'not-provided; store-name text is not a logo',
        'qr_status': 'provided-not-scan-verified' if data.get('qr_image') else 'not-provided; no fake QR created'})


def revise_festival(source: Path, changes_path: Path, output: Path) -> dict:
    changes = load_json(changes_path)
    color_targets = {'background_color':'change-background-base', 'decoration_color':'change-background-decoration-1', 'footer_color':'change-background-decoration-2'}
    allowed = set(color_targets) | {'date'}
    if not changes or set(changes) - allowed: fail('Change Set allows only date and the three background colors; protected content cannot change.')
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    original = source.read_text(encoding='utf-8')
    before = ET.fromstring(original)
    after = ET.fromstring(original)
    required = {'protected-dish','protected-logo','protected-title','protected-price','protected-qr','change-date',*color_targets.values()}
    found = {n.get('id') for n in after.iter()}
    if not required.issubset(found): fail('Input is not a filled T03 festival-locked template.')
    for key, value in changes.items():
        if key == 'date':
            node = after.find(".//*[@id='change-date']")
            node.text = exact_text('date', value, True)
        else:
            if not isinstance(value, str) or not HEX_COLOR.fullmatch(value): fail(f'{key} must be #RRGGBB.')
            after.find(".//*[@id='" + color_targets[key] + "']").set('fill', value)
    changed=[]; protected=[]
    for left,right in zip(list(before),list(after)):
        ident=left.get('id','anonymous')
        same=ET.tostring(left)==ET.tostring(right)
        if not same:
            changed.append(ident)
            if ident not in {'change-date',*color_targets.values()}: fail('Protected layer changed: '+ident)
        if ident.startswith('protected-'):
            protected.append({'id':ident,'identical':same,'sha256':hashlib.sha256(ET.tostring(left)).hexdigest()})
    if before.attrib != after.attrib or len(before)!=len(after): fail('Canvas or layer count changed.')
    svg=ET.tostring(after,encoding='unicode')
    return write_output(output, svg, {'template':'festival-locked','source_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'change_set':changes,'changed_layers':changed,'protected_layers':protected,
        'truth_status':'inherited-from-source','facts_source':source.name,'all_images_embedded':True})


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('render');p.add_argument('--template',choices=CONFIG,required=True)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('revise-festival');p.add_argument('--source',type=Path,required=True)
    p.add_argument('--changes',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        result=render(args.template,args.data,args.output) if args.command=='render' else revise_festival(args.source,args.changes,args.output)
    except (ValueError,OSError,ET.ParseError) as error:
        print(json.dumps({'status':'blocked','reason':str(error)},ensure_ascii=False),file=sys.stderr)
        return 2
    print(json.dumps({'status':result['status'],'output':str(args.output),'raster_exported':False,'visual_checked':False},ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
