#!/usr/bin/env python3
"""Read-only CSV/TSV/XLSX import. No network, macros, or formula execution."""
from __future__ import annotations
import csv
import io
import json
import posixpath
import re
import unicodedata
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ALIASES = {
    'company': ['company', '公司', '公司名称', '企业', '企业名称', '单位名称'],
    'title': ['title', '岗位', '职位', '岗位名称', '职位名称', '招聘岗位'],
    'city': ['city', '城市', '工作城市', '工作地点', '地点'],
    'route': ['route', '招聘类型', '类型', '招聘类别'],
    'graduation_year': ['graduation_year', '毕业届别', '届别', '毕业年份', '毕业时间要求'],
    'deadline': ['deadline', '截止时间', '截止日期', '投递截止时间'],
    'url': ['url', '投递链接', '网申链接', '链接', '岗位链接', '招聘链接'],
    'jd': ['jd', '岗位jd', '岗位JD', 'JD', '职位描述', '岗位描述', '岗位要求'],
    'source_type': ['source_type', '来源类型'],
    'verification': ['verification', '核验状态'],
    'verified_at': ['verified_at', '核验时间'],
    'source_quote': ['source_quote', '来源原文', '证据摘录'],
}
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RELNS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'


def norm(value: Any) -> str:
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value or ''))).casefold()


def header_key(value: str, mapping: dict[str, str]) -> str | None:
    if value in mapping:
        result = mapping[value]
        if result not in ALIASES:
            raise ValueError(f'Unknown standard column in mapping: {result}')
        return result
    n = norm(value)
    for key, aliases in ALIASES.items():
        if n in {norm(x) for x in aliases}:
            return key
    return None


def safe_cell(value: Any) -> str:
    """Escape formula-like text in CSV exports. Original remains in JSON."""
    text = '' if value is None else str(value)
    if text and (text[0] in '\t\r\n' or text.lstrip().startswith(('=', '+', '-', '@'))):
        return "'" + text
    return text


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        w.writeheader()
        for row in rows:
            w.writerow({k: safe_cell(row.get(k, '')) for k in columns})


def _decode(data: bytes) -> str:
    for enc in ('utf-8-sig', 'gb18030', 'utf-16'):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError('Unsupported text encoding; provide UTF-8 CSV.')


def _col_index(ref: str) -> int:
    m = re.match(r'([A-Za-z]+)', ref)
    if not m:
        return 0
    n = 0
    for c in m[1].upper():
        n = n * 26 + ord(c) - 64
    return n - 1


def _rels(z: zipfile.ZipFile, member: str) -> dict[str, dict[str, str]]:
    if member not in z.namelist():
        return {}
    return {n.attrib['Id']: n.attrib for n in ET.fromstring(z.read(member))}


def _member(base: str, target: str) -> str:
    path = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(base, target))
    if path.startswith('../'):
        raise ValueError('Invalid XLSX relationship path.')
    return path


def _xlsx_sheets(path: Path, warnings: list[dict]) -> list[tuple[str, list[tuple[int, list[str]]]]]:
    with zipfile.ZipFile(path) as z:
        members = z.infolist()
        if sum(m.file_size for m in members) > 500_000_000 or any(m.file_size > 150_000_000 for m in members):
            raise ValueError('Workbook exceeds safe unpacked-size limit.')
        if any(m.filename.endswith('vbaProject.bin') for m in members):
            warnings.append({'reason': 'macro_content_ignored'})
        if 'xl/workbook.xml' not in z.namelist():
            raise ValueError('Not a supported XLSX workbook.')
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        date1904 = wb.find('m:workbookPr', NS)
        epoch = datetime(1904, 1, 1) if date1904 is not None and date1904.get('date1904') in ('1', 'true') else datetime(1899, 12, 30)
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        styles = []
        formats = {}
        if 'xl/styles.xml' in z.namelist():
            st = ET.fromstring(z.read('xl/styles.xml'))
            formats = {int(n.get('numFmtId', '0')): n.get('formatCode', '') for n in st.findall('m:numFmts/m:numFmt', NS)}
            styles = [int(n.get('numFmtId', '0')) for n in st.findall('m:cellXfs/m:xf', NS)]
        bookrels = _rels(z, 'xl/_rels/workbook.xml.rels')
        out = []
        for sh in wb.findall('m:sheets/m:sheet', NS):
            name = sh.get('name', '')
            rel = bookrels.get(sh.get('{'+RELNS+'}id', ''), {})
            if rel.get('TargetMode') == 'External':
                warnings.append({'sheet': name, 'reason': 'external_sheet_ignored'})
                continue
            member = _member('xl', rel.get('Target', ''))
            if member not in z.namelist():
                warnings.append({'sheet': name, 'reason': 'sheet_xml_missing'})
                continue
            root = ET.fromstring(z.read(member))
            srels = _rels(z, posixpath.join(posixpath.dirname(member), '_rels', posixpath.basename(member)+'.rels'))
            links = {}
            for h in root.findall('m:hyperlinks/m:hyperlink', NS):
                hr = srels.get(h.get('{'+RELNS+'}id', ''), {})
                target = hr.get('Target', '')
                if target.startswith(('http://', 'https://')):
                    links[h.get('ref', '')] = target
            if root.find('m:mergeCells', NS) is not None:
                warnings.append({'sheet': name, 'reason': 'merged_cells_present_check_headers'})
            data = []
            for row in root.findall('m:sheetData/m:row', NS):
                rn = int(row.get('r', len(data)+1))
                vals: dict[int, str] = {}
                for c in row.findall('m:c', NS):
                    ref = c.get('r', 'A1')
                    col = _col_index(ref)
                    v = c.find('m:v', NS)
                    value = v.text or '' if v is not None else ''
                    typ = c.get('t', '')
                    if typ == 's' and value:
                        value = shared[int(value)]
                    elif typ == 'inlineStr':
                        value = ''.join(c.find('m:is', NS).itertext()) if c.find('m:is', NS) is not None else ''
                    elif typ == 'b':
                        value = 'true' if value == '1' else 'false'
                    formula = c.find('m:f', NS)
                    if formula is not None:
                        warnings.append({'sheet': name, 'row': rn, 'cell': ref, 'reason': 'formula_cached_value_only' if value else 'formula_without_cached_value'})
                        # HYPERLINK string literals can be read without evaluating formulas.
                        hm = re.match(r'^HYPERLINK\(\s*"(https?://[^"\r\n]+)"\s*[,;]', formula.text or '', re.I)
                        if hm and ref not in links:
                            links[ref] = hm[1]
                    if ref in links:
                        # Preserve label and URL separately, with an explicit warning.
                        warnings.append({'sheet': name, 'row': rn, 'cell': ref, 'reason': 'hyperlink_target_used', 'display': value})
                        value = links[ref]
                    else:
                        si = int(c.get('s', '0'))
                        fmtid = styles[si] if si < len(styles) else 0
                        code = re.sub(r'"[^"]*"|\[[^\]]*\]', '', formats.get(fmtid, ''))
                        isdate = fmtid in set(range(14, 23)) | set(range(45, 48)) or bool(re.search(r'[dy]', code, re.I))
                        if value and isdate and typ not in ('s', 'inlineStr'):
                            try:
                                value = (epoch + timedelta(days=float(value))).date().isoformat()
                            except (ValueError, OverflowError):
                                warnings.append({'sheet': name, 'row': rn, 'cell': ref, 'reason': 'unparsed_excel_date'})
                    vals[col] = value
                if vals and any(str(v).strip() for v in vals.values()):
                    data.append((rn, [vals.get(i, '') for i in range(max(vals)+1)]))
            out.append((name, data))
        return out


def read_table(path: Path, mapping: dict[str, str] | None = None, selected_sheets: list[str] | None = None) -> tuple[list[dict], dict]:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f'Input not found: {path}')
    if path.stat().st_size > 100_000_000:
        raise ValueError('Input exceeds 100 MB; split explicitly before importing.')
    mapping = mapping or {}
    warnings: list[dict] = []
    suffix = path.suffix.casefold()
    if suffix == '.xlsx':
        sheets = _xlsx_sheets(path, warnings)
    elif suffix in ('.csv', '.tsv'):
        text = _decode(path.read_bytes())
        delimiter = '\t' if suffix == '.tsv' else ','
        sheets = [(path.stem, [(i, row) for i, row in enumerate(csv.reader(io.StringIO(text), delimiter=delimiter), 1) if any(v.strip() for v in row)])]
    else:
        raise ValueError('Supported formats: .csv .tsv .xlsx; no XLS, encrypted files, or screenshots.')
    if selected_sheets:
        available = {name for name, _ in sheets}
        missing = set(selected_sheets) - available
        if missing:
            raise ValueError('Selected sheets not found: ' + ', '.join(sorted(missing)))
        warnings.extend({'sheet': name, 'reason': 'not_selected_by_user'} for name, _ in sheets if name not in selected_sheets)
        sheets = [(name, data) for name, data in sheets if name in selected_sheets]
    results, skipped, sheet_stats = [], [], []
    scanned = 0
    for name, rows in sheets:
        found = None
        for idx, (rn, values) in enumerate(rows[:30]):
            keys = [header_key(v, mapping) for v in values]
            if 'company' in keys and 'title' in keys:
                found = (idx, values, keys)
                break
        if found is None:
            warnings.append({'sheet': name, 'reason': 'company_title_header_not_found', 'nonempty_rows': len(rows)})
            sheet_stats.append({'sheet': name, 'processed': False, 'nonempty_rows': len(rows)})
            continue
        idx, headers, keys = found
        mapped = [k for k in keys if k]
        if len(mapped) != len(set(mapped)):
            warnings.append({'sheet': name, 'reason': 'duplicate_mapped_headers_first_nonempty_used'})
        accepted = 0
        for rn, values in rows[idx+1:]:
            scanned += 1
            row: dict[str, Any] = {}
            raw = {f'{i+1}:{headers[i] if i<len(headers) else "extra"}': v for i, v in enumerate(values)}
            for i, key in enumerate(keys):
                if key and i < len(values) and not row.get(key):
                    row[key] = values[i].strip()
            if not row.get('company') or not row.get('title'):
                skipped.append({'sheet': name, 'row': rn, 'reason': 'missing_company_or_title', 'raw': raw})
                continue
            if header_key(str(row['company']), mapping) == 'company' and header_key(str(row['title']), mapping) == 'title':
                skipped.append({'sheet': name, 'row': rn, 'reason': 'repeated_header', 'raw': raw})
                continue
            row['_source'] = {'file': str(path), 'sheet': name, 'row': rn}
            row['_raw'] = raw
            results.append(row)
            accepted += 1
        sheet_stats.append({'sheet': name, 'processed': True, 'header_row': rows[idx][0], 'scanned_rows': len(rows)-idx-1, 'accepted_rows': accepted})
    report = {'input': str(path), 'scanned_data_rows': scanned, 'accepted_rows': len(results), 'skipped_rows': len(skipped), 'skipped': skipped, 'sheets': sheet_stats, 'warnings': warnings}
    if not any(s['processed'] for s in sheet_stats):
        raise ValueError('No usable company/title header found. Provide explicit column mapping or a standardized table.')
    return results, report
