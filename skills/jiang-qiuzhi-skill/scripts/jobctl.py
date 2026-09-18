#!/usr/bin/env python3
"""Local job-search workspace: explicit data dir, atomic SQLite writes, no network."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
import sys
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from table_io import norm, read_table, write_csv

STAGES = ['selected', 'draft_filled', 'ready_for_review', 'submitted', 'assessment', 'interview', 'offer', 'rejected', 'withdrawn']
ACTUAL = set(STAGES[3:])
ROUTES = {'校招': 'campus', '校园招聘': 'campus', '秋招': 'campus', '应届': 'campus', 'campus': 'campus', '实习': 'internship', '实习生': 'internship', 'internship': 'internship', '社招': 'social', '社会招聘': 'social', 'social': 'social'}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8-sig'))


def dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(path)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def clean_url(url: str) -> str:
    p = urlsplit(url.strip())
    if p.scheme not in ('http', 'https') or not p.netloc:
        return url.strip()
    # Retain functional fragments used by SPA recruitment sites; only drop tracking params.
    q = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
               if not k.lower().startswith('utm_') and k.lower() not in ('gclid', 'fbclid'))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', urlencode(q), p.fragment))


def job_key(row: dict) -> str:
    values = [norm(row.get(k)) for k in ('company', 'title', 'city', 'route', 'graduation_year')]
    values.append(clean_url(str(row.get('url', ''))))
    return 'job-' + hashlib.sha256('\x1f'.join(values).encode()).hexdigest()[:20]


def parse_years(value: Any) -> set[int] | None:
    text = str(value or '').strip()
    if not text:
        return None
    # Only explicit year / simple year range; ambiguous date-window language requires review.
    m = re.fullmatch(r'(20\d{2})(?:届|年)?', text)
    if m:
        return {int(m[1])}
    m = re.fullmatch(r'(20\d{2})\s*[-~至—]\s*(20\d{2})(?:届|年)?', text)
    if m and 0 <= int(m[2])-int(m[1]) <= 4:
        return set(range(int(m[1]), int(m[2])+1))
    parts = re.split(r'[,，、/]', text)
    if len(parts) > 1 and all(re.fullmatch(r'20\d{2}(?:届|年)?', p.strip()) for p in parts):
        return {int(p.strip()[:4]) for p in parts}
    return None


def parse_deadline(value: Any) -> date | None:
    text = str(value or '').strip()
    if re.fullmatch(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', text):
        try:
            y, m, d = map(int, re.split('[-/]', text))
            return date(y, m, d)
        except ValueError:
            return None
    # Timestamp cannot be reduced to a local date without a known timezone policy.
    return None


def screen_one(job: dict, profile: dict, as_of: date, already_applied: bool = False) -> dict:
    failure, unknown, hits = [], [], []
    jr = ROUTES.get(norm(job.get('route')), '')
    pr = profile.get('route')
    if not jr:
        unknown.append('招聘类型未知或未标准化')
    elif pr and jr != pr:
        failure.append('招聘类型不符')
    years = parse_years(job.get('graduation_year'))
    if pr in ('campus', 'internship'):
        py = profile.get('graduation_year')
        if py is None or years is None:
            unknown.append('毕业资格待核实')
        elif int(py) not in years:
            failure.append('届别不符')
    cities = profile.get('cities', [])
    city = str(job.get('city', ''))
    if profile.get('city_strict') and cities:
        if not city:
            unknown.append('城市未知')
        elif not any(norm(c) in norm(city) for c in cities):
            # Nationwide / remote can be compatible but must be confirmed.
            if any(t in city for t in ('全国', '远程', '不限', '多个')):
                unknown.append('城市范围需确认')
            else:
                failure.append('不符合明确城市限制')
    deadline = parse_deadline(job.get('deadline'))
    if deadline and deadline < as_of:
        failure.append('已过所列截止日期')
    elif not deadline:
        unknown.append('截止时间未披露或格式待核实')
    kws = profile.get('job_keywords', [])
    haystack = norm(job.get('title', '') + ' ' + job.get('jd', ''))
    hits = [w for w in kws if norm(w) in haystack]
    if kws and not hits:
        unknown.append('方向关键词未命中，需人工复核')
    if not kws:
        unknown.append('目标方向尚未确认')
    if not str(job.get('url', '')).startswith(('https://', 'http://')):
        unknown.append('投递链接缺失或无效')
    if not job.get('jd'):
        unknown.append('完整JD待获取')
    bucket = '已投递' if already_applied else '不匹配或过期' if failure else '待补信息' if unknown else '优先核实'
    return {**job, 'bucket': bucket, 'eligibility': 'fail' if failure else 'unknown',
            'keyword_hits': '|'.join(hits), 'keyword_hit_count': len(hits),
            'reasons': '；'.join(failure+unknown) or '字段初筛无明显冲突；仍须官网核实与完整JD资格检查',
            'as_of': as_of.isoformat(), 'is_full_jd_assessment': False}


class Store:
    def __init__(self, directory: Path):
        self.directory = directory.expanduser().resolve()
        skill = Path(__file__).resolve().parents[1]
        if self.directory == skill or skill in self.directory.parents:
            raise ValueError('Runtime data must be outside the distributed Skill directory.')
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            self.directory.chmod(0o700)
        except OSError:
            pass
        self.path = self.directory/'state.sqlite3'
        existed = self.path.exists()
        self.db = sqlite3.connect(self.path, timeout=20)
        self.db.execute('PRAGMA busy_timeout=20000')
        if not existed:
            self.db.executescript('CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL); INSERT INTO meta VALUES ("schema_version", "1"); CREATE TABLE records (kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id)); CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, kind TEXT NOT NULL, record_id TEXT NOT NULL, action TEXT NOT NULL);')
            self.db.commit()
        try:
            v = self.db.execute('SELECT value FROM meta WHERE key=?', ('schema_version',)).fetchone()
        except sqlite3.Error as e:
            self.db.close()
            raise ValueError('Unrecognized database. Do not reuse the old Skill data directory.') from e
        if not v or v[0] != '1':
            self.db.close()
            raise ValueError('Unsupported schema version; keep original database unchanged.')
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    def close(self) -> None:
        self.db.close()

    def all(self, kind: str) -> list[dict]:
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM records WHERE kind=? ORDER BY id', (kind,))]

    def get(self, kind: str, id_: str) -> dict | None:
        r = self.db.execute('SELECT payload FROM records WHERE kind=? AND id=?', (kind, id_)).fetchone()
        return json.loads(r[0]) if r else None

    @contextmanager
    def write(self):
        # A separate backup connection before mutation, then one atomic write transaction.
        backup_dir = self.directory/'backups'
        backup_dir.mkdir(exist_ok=True, mode=0o700)
        backup_path = backup_dir/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'.sqlite3')
        b = sqlite3.connect(backup_path)
        try:
            self.db.backup(b)
        finally:
            b.close()
        try:
            backup_path.chmod(0o600)
        except OSError:
            pass
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def put(self, kind: str, id_: str, value: dict, action='update') -> None:
        payload = {**value, 'id': id_, 'updated_at': now()}
        self.db.execute('INSERT INTO records(kind,id,payload) VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload', (kind, id_, json.dumps(payload, ensure_ascii=False)))
        self.db.execute('INSERT INTO events(at,kind,record_id,action) VALUES(?,?,?,?)', (now(), kind, id_, action))


def validate_profile(p: dict) -> None:
    if not isinstance(p, dict) or p.get('route') not in ('campus', 'social', 'internship'):
        raise ValueError('profile.route must be campus, social, or internship.')
    if p.get('graduation_year') is not None and (type(p['graduation_year']) is not int or not 1900 <= p['graduation_year'] <= 2200):
        raise ValueError('graduation_year must be a year integer or null.')
    for k in ('cities', 'job_keywords', 'facts'):
        if not isinstance(p.get(k, []), list):
            raise ValueError(f'{k} must be an array.')
    if any(not isinstance(v, str) for k in ('cities', 'job_keywords') for v in p.get(k, [])):
        raise ValueError('cities/job_keywords must contain strings.')
    if not isinstance(p.get('city_strict', False), bool):
        raise ValueError('city_strict must be boolean.')
    ids = set()
    for f in p.get('facts', []):
        if not isinstance(f, dict) or not all(f.get(k) for k in ('id', 'experience_id', 'text', 'source')):
            raise ValueError('Each fact needs id, experience_id, text and source.')
        if f['id'] in ids:
            raise ValueError('Duplicate fact ID.')
        ids.add(f['id'])


def import_jobs(store: Store, path: Path, mapping: dict | None = None, selected_sheets: list[str] | None = None) -> dict:
    rows, report = read_table(path, mapping, selected_sheets)
    merged = {}
    duplicate_rows = []
    for row in rows:
        row['route'] = ROUTES.get(norm(row.get('route')), row.get('route', ''))
        row['url'] = clean_url(row.get('url', ''))
        key = job_key(row)
        row['id'] = key
        if key in merged:
            duplicate_rows.append({'id': key, 'source': row['_source']})
            merged[key]['provenance'].append({'source': row['_source'], 'raw': row['_raw']})
            # Keep first non-empty standardized value, preserve conflicting raw evidence.
            for k, v in row.items():
                if k not in ('id', '_source', '_raw') and v and not merged[key].get(k):
                    merged[key][k] = v
        else:
            merged[key] = {**row, 'provenance': [{'source': row['_source'], 'raw': row['_raw']}], 'imported_at': now()}
    added = updated = 0
    with store.write():
        for key, row in merged.items():
            existing = store.get('job', key)
            if existing:
                updated += 1
                old_prov = existing.get('provenance', [])
                serialized = {json.dumps(p, sort_keys=True, ensure_ascii=False) for p in old_prov}
                row['provenance'] = old_prov + [p for p in row['provenance'] if json.dumps(p, sort_keys=True, ensure_ascii=False) not in serialized]
                # Latest imported values replace previous values, with full original provenance retained.
            else:
                added += 1
            store.put('job', key, row, 'import')
    report.update(unique_jobs_in_input=len(merged), duplicate_rows=len(rows)-len(merged), duplicates=duplicate_rows, added=added, updated=updated)
    report_path = store.directory/'reports'/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')+'-import-report.json')
    dump(report_path, report)
    dump(store.directory/'import-report.json', report)
    return {'accepted_rows': len(rows), 'unique_jobs_in_input': len(merged), 'duplicate_rows': len(rows)-len(merged), 'skipped_rows': report['skipped_rows'], 'added': added, 'updated': updated, 'warnings': len(report['warnings']), 'report': str(report_path)}


def set_application(store: Store, jobid: str, stage: str, kind: str, evidence: str, resume_id: str | None = None, correct: bool = False) -> dict:
    if not store.get('job', jobid):
        raise ValueError('Unknown job ID. Import the job first.')
    if stage not in STAGES:
        raise ValueError('Unknown application stage.')
    if not evidence.strip():
        raise ValueError('An explicit evidence summary is required.')
    if stage in ACTUAL and kind not in ('user_report', 'receipt'):
        raise ValueError('Real recruitment progress requires user_report or receipt evidence; draft is not submission.')
    if resume_id and not store.get('resume', resume_id):
        raise ValueError('Unknown registered resume version.')
    old = store.get('application', jobid)
    if old and old['stage'] in ('rejected', 'withdrawn') and stage != old['stage'] and not correct:
        raise ValueError('Terminal state change needs --correct and an explicit reason.')
    if old and STAGES.index(stage) < STAGES.index(old['stage']) and not correct:
        raise ValueError('Backward stage change needs --correct and an explicit reason.')
    history = list((old or {}).get('history', [])) + [{'at': now(), 'stage': stage, 'evidence_kind': kind, 'evidence_summary': evidence[:500], 'correction': correct}]
    result = {**(old or {}), 'history': history, 'job_id': jobid, 'stage': stage, 'evidence_kind': kind, 'evidence_summary': evidence[:500], 'resume_id': resume_id or (old or {}).get('resume_id'), 'ever_submitted': bool((old or {}).get('ever_submitted')) or stage in ('submitted', 'assessment', 'interview', 'offer')}
    with store.write():
        store.put('application', jobid, result, 'correction' if correct else 'stage:'+stage)
    return result


def validate_due(text: str) -> None:
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text):
        date.fromisoformat(text)
    else:
        d = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if d.tzinfo is None:
            raise ValueError('Timed tasks require timezone offset; a date-only task is also supported.')


def validate_training(data: dict) -> None:
    allowed = {'question_type', 'score', 'issue_tags', 'improvement_summary', 'next_actions', 'job_id', 'dimensions'}
    if not isinstance(data, dict) or set(data)-allowed:
        raise ValueError('Only structured training summary fields are allowed; no answers/transcripts.')
    if not isinstance(data.get('question_type'), str) or not data['question_type'].strip():
        raise ValueError('question_type required.')
    if data.get('score') is not None and (type(data['score']) not in (int, float) or not 0 <= data['score'] <= 100):
        raise ValueError('score must be null or 0–100.')
    if not isinstance(data.get('improvement_summary', ''), str) or len(data.get('improvement_summary', '')) > 500:
        raise ValueError('Only a short improvement summary (<=500 chars) is permitted.')
    for field in ('issue_tags', 'next_actions'):
        if not isinstance(data.get(field, []), list) or any(not isinstance(x, str) or len(x) > 200 for x in data.get(field, [])):
            raise ValueError(f'{field} must contain short text strings.')
    dims = data.get('dimensions', {})
    limits = {'relevance':25,'evidence':25,'structure':20,'role_fit':20,'clarity':10}
    if not isinstance(dims, dict) or set(dims)-set(limits) or any(type(v) not in (int,float) or not 0 <= v <= limits[k] for k,v in dims.items()):
        raise ValueError('Invalid training dimensions.')


def register_resume(store: Store, path: Path) -> dict:
    manifest = load_json(path)
    if manifest.get('demo') or not manifest.get('approved_for_use') or not manifest.get('visual_checked'):
        raise ValueError('Demo/unapproved/unreviewed resumes cannot be registered for real use.')
    files = manifest.get('files', {})
    if 'resume.pdf' not in files:
        raise ValueError('A validated PDF must be present before registering.')
    for filename, digest in files.items():
        f = (path.parent/filename).resolve()
        if path.parent.resolve() not in f.parents or not f.is_file() or sha(f) != digest:
            raise ValueError(f'File missing, unsafe path, or hash mismatch: {filename}')
    qa = load_json(path.parent/'qa.json')
    if not qa.get('pdf_checks', {}).get('passed'):
        raise ValueError('PDF structural checks did not pass.')
    rid = 'resume-' + files['resume.pdf'][:20]
    record = {**manifest, 'manifest_path': str(path.resolve()), 'pdf_path': str((path.parent/'resume.pdf').resolve())}
    with store.write():
        store.put('resume', rid, record, 'register')
    return {'id': rid, 'pdf_path': record['pdf_path']}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir', required=True, type=Path)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    pr = sub.add_parser('profile').add_subparsers(dest='action', required=True)
    pr.add_parser('set').add_argument('--file', type=Path, required=True)
    pr.add_parser('show')
    jobs = sub.add_parser('jobs').add_subparsers(dest='action', required=True)
    ji = jobs.add_parser('import'); ji.add_argument('--file', type=Path, required=True); ji.add_argument('--mapping', type=Path); ji.add_argument('--sheets', nargs='+', help='Exact worksheet names; default all recognizable sheets')
    jobs.add_parser('list')
    js = jobs.add_parser('screen'); js.add_argument('--as-of', required=True); js.add_argument('--out', type=Path, required=True)
    rr = sub.add_parser('resume').add_subparsers(dest='action', required=True)
    rr.add_parser('register').add_argument('--manifest', type=Path, required=True); rr.add_parser('list')
    apps = sub.add_parser('applications').add_subparsers(dest='action', required=True)
    ap = apps.add_parser('set'); ap.add_argument('--job-id', required=True); ap.add_argument('--stage', required=True, choices=STAGES); ap.add_argument('--evidence-kind', required=True, choices=['draft', 'user_report', 'receipt']); ap.add_argument('--evidence', required=True); ap.add_argument('--resume-id'); ap.add_argument('--correct', action='store_true')
    apps.add_parser('list')
    ts = sub.add_parser('tasks').add_subparsers(dest='action', required=True)
    ta = ts.add_parser('add'); ta.add_argument('--title', required=True); ta.add_argument('--due', required=True); ta.add_argument('--job-id')
    ts.add_parser('done').add_argument('--id', required=True); ts.add_parser('list')
    d = sub.add_parser('daily'); d.add_argument('--date', required=True); d.add_argument('--timezone')
    tr = sub.add_parser('training').add_subparsers(dest='action', required=True)
    tr.add_parser('save').add_argument('--file', required=True, type=Path); tr.add_parser('list')
    return p


def run(a, s: Store) -> Any:
    cmd, act = a.command, getattr(a, 'action', '')
    if cmd == 'init':
        return {'schema_version': 1, 'database': str(s.path), 'notifications_enabled': False}
    if cmd == 'profile':
        if act == 'show': return s.get('profile', 'candidate')
        obj = load_json(a.file); validate_profile(obj)
        with s.write(): s.put('profile', 'candidate', obj, 'profile-confirmed')
        return {'saved': True}
    if cmd == 'jobs':
        if act == 'list': return s.all('job')
        if act == 'import': return import_jobs(s, a.file, load_json(a.mapping) if a.mapping else None, a.sheets)
        profile = s.get('profile', 'candidate')
        if not profile: raise ValueError('Set the confirmed profile first.')
        today = date.fromisoformat(a.as_of)
        apps = {x['job_id'] for x in s.all('application') if x.get('ever_submitted')}
        rows = [screen_one(j, profile, today, j['id'] in apps) for j in s.all('job')]
        rows.sort(key=lambda r: (-r['keyword_hit_count'], str(r.get('deadline') or '9999'), r['id']))
        a.out.mkdir(parents=True, exist_ok=True)
        cols = ['id', 'company', 'title', 'city', 'route', 'graduation_year', 'deadline', 'url', 'jd', 'source_type', 'verification', 'verified_at', 'bucket', 'keyword_hits', 'reasons', 'as_of']
        write_csv(a.out/'all-screened.csv', rows, cols); dump(a.out/'all-screened.json', rows)
        counts = {}
        for bucket in ['优先核实', '待补信息', '不匹配或过期', '已投递']:
            items = [r for r in rows if r['bucket'] == bucket]; counts[bucket] = len(items)
            write_csv(a.out/(bucket+'.csv'), items, cols)
        result = {'total_unique_jobs': len(rows), 'buckets': counts, 'official_pages_checked_by_this_command': 0, 'full_jd_assessments_by_this_command': 0, 'as_of': a.as_of, 'output': str(a.out.resolve())}
        dump(a.out/'screen-report.json', result); return result
    if cmd == 'resume':
        return s.all('resume') if act == 'list' else register_resume(s, a.manifest.resolve())
    if cmd == 'applications':
        return s.all('application') if act == 'list' else set_application(s, a.job_id, a.stage, a.evidence_kind, a.evidence, a.resume_id, a.correct)
    if cmd == 'tasks':
        if act == 'list': return s.all('task')
        if act == 'done':
            obj = s.get('task', a.id)
            if not obj: raise ValueError('Unknown task ID.')
            obj['done'] = True
            with s.write(): s.put('task', a.id, obj, 'complete')
            return {'done': True, 'id': a.id}
        validate_due(a.due)
        if a.job_id and not s.get('job', a.job_id): raise ValueError('Unknown job ID.')
        tid = 'task-' + uuid.uuid4().hex[:20]
        obj = {'title': a.title, 'due': a.due, 'job_id': a.job_id, 'done': False, 'notifications_enabled': False}
        with s.write(): s.put('task', tid, obj, 'create')
        return {'id': tid, **obj}
    if cmd == 'daily':
        today = date.fromisoformat(a.date)
        zone_name = a.timezone or (s.get('profile', 'candidate') or {}).get('timezone')
        items = []
        for task in s.all('task'):
            if task.get('done'): continue
            due = task['due']
            if len(due) == 10:
                day = date.fromisoformat(due); local_due = due
            else:
                if not zone_name: raise ValueError('Timed daily planning requires profile.timezone or --timezone.')
                try: zone = ZoneInfo(zone_name)
                except ZoneInfoNotFoundError as e: raise ValueError('Timezone database unavailable; ask host to resolve timezone, do not guess.') from e
                local = datetime.fromisoformat(due.replace('Z', '+00:00')).astimezone(zone)
                day = local.date(); local_due = local.isoformat()
            if day <= today: items.append({**task, 'local_due': local_due})
        items.sort(key=lambda t:t['local_due'])
        return {'date': a.date, 'timezone': zone_name, 'tasks': items, 'notifications_enabled': False}
    if cmd == 'training':
        if act == 'list': return s.all('training')
        obj = load_json(a.file); validate_training(obj)
        if obj.get('job_id') and not s.get('job', obj['job_id']): raise ValueError('Unknown job ID.')
        tid = 'training-' + uuid.uuid4().hex[:20]
        with s.write(): s.put('training', tid, obj, 'summary')
        return {'id': tid, 'saved': True}
    raise ValueError('Unknown command.')


def main() -> int:
    a = parser().parse_args()
    s = None
    try:
        s = Store(a.data_dir)
        print(json.dumps(run(a, s), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, json.JSONDecodeError) as e:
        print(json.dumps({'error': str(e), 'completed': False}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        if s: s.close()


if __name__ == '__main__':
    raise SystemExit(main())
