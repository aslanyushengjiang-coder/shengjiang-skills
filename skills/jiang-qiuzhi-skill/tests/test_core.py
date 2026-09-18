from __future__ import annotations
import argparse
import copy
import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from jobctl import Store, clean_url, import_jobs, job_key, parse_deadline, parse_years, register_resume, run, screen_one, set_application, validate_due, validate_profile, validate_training
from table_io import read_table, safe_cell, write_csv
from resume_export import validate_resume, render_html


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
        self.s=Store(self.base/'state')
        self.profile=json.loads((ROOT/'demo/profile.json').read_text())
        self.resume=json.loads((ROOT/'demo/resume-after.json').read_text())
        self.job={'id':'job-demo','company':'虚构公司','title':'数据分析','city':'杭州','route':'campus','graduation_year':'2027届','deadline':'2026-10-15','url':'https://example.invalid/j1','jd':'虚构数据分析JD'}
        with self.s.write():self.s.put('job',self.job['id'],self.job)
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def write_csv(self, rows):
        p=self.base/'input.csv'
        with p.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        return p
    def test_schema_initialized(self):self.assertEqual(self.s.db.execute('SELECT value FROM meta').fetchone()[0],'1')
    def test_workspace_isolation(self):
        other=Store(self.base/'other')
        try:self.assertEqual(other.all('job'),[])
        finally:other.close()
    def test_skill_data_refused(self):
        with self.assertRaises(ValueError):Store(ROOT/'data')
    def test_backup_created(self):self.assertTrue(list((self.s.directory/'backups').glob('*.sqlite3')))
    def test_transaction_rollback(self):
        try:
            with self.s.write():self.s.put('job','bad',{});raise ValueError('stop')
        except ValueError:pass
        self.assertIsNone(self.s.get('job','bad'))
    def test_profile_valid(self):validate_profile(self.profile)
    def test_profile_year_type(self):
        p=copy.deepcopy(self.profile);p['graduation_year']='2027'
        with self.assertRaises(ValueError):validate_profile(p)
    def test_profile_duplicate_fact(self):
        p=copy.deepcopy(self.profile);p['facts'].append(p['facts'][0])
        with self.assertRaises(ValueError):validate_profile(p)
    def test_url_tracking_removed(self):self.assertEqual(clean_url('https://X.test/job?id=3&utm_source=a'),'https://x.test/job?id=3')
    def test_url_job_id_preserved(self):self.assertNotEqual(clean_url('https://x.test/job?id=3'),clean_url('https://x.test/job?id=4'))
    def test_spa_fragment_preserved(self):self.assertNotEqual(clean_url('https://x.test/#/job/3'),clean_url('https://x.test/#/job/4'))
    def test_different_cities_not_merged(self):self.assertNotEqual(job_key(self.job),job_key({**self.job,'city':'上海'}))
    def test_simple_year_range(self):self.assertEqual(parse_years('2026-2027届'),{2026,2027})
    def test_complex_year_window_unknown(self):self.assertIsNone(parse_years('2026年9月到2027年8月'))
    def test_invalid_date_unknown(self):self.assertIsNone(parse_deadline('2026-02-30'))
    def test_unknown_deadline_not_expired(self):
        r=screen_one({**self.job,'deadline':''},self.profile,date(2026,9,17));self.assertEqual(r['bucket'],'待补信息')
    def test_expired_excluded(self):
        r=screen_one({**self.job,'deadline':'2026-09-01'},self.profile,date(2026,9,17));self.assertEqual(r['bucket'],'不匹配或过期')
    def test_city_mismatch(self):
        r=screen_one({**self.job,'city':'上海'},self.profile,date(2026,9,17));self.assertEqual(r['bucket'],'不匹配或过期')
    def test_remote_city_uncertain(self):
        r=screen_one({**self.job,'city':'全国远程'},self.profile,date(2026,9,17));self.assertEqual(r['bucket'],'待补信息')
    def test_year_mismatch(self):
        r=screen_one({**self.job,'graduation_year':'2026届'},self.profile,date(2026,9,17));self.assertEqual(r['eligibility'],'fail')
    def test_screen_not_full_jd_review(self):
        r=screen_one(self.job,self.profile,date(2026,9,17));self.assertEqual(r['bucket'],'优先核实');self.assertFalse(r['is_full_jd_assessment']);self.assertEqual(r['eligibility'],'unknown')
    def test_import_13_rows(self):
        r=import_jobs(self.s,ROOT/'demo/jobs-fictional.csv');self.assertEqual((r['accepted_rows'],r['unique_jobs_in_input'],r['duplicate_rows']),(13,12,1))
    def test_reimport_idempotent(self):
        import_jobs(self.s,ROOT/'demo/jobs-fictional.csv');n=len(self.s.all('job'));r=import_jobs(self.s,ROOT/'demo/jobs-fictional.csv');self.assertEqual(len(self.s.all('job')),n);self.assertEqual(r['added'],0)
    def test_import_no_application(self):import_jobs(self.s,ROOT/'demo/jobs-fictional.csv');self.assertEqual(self.s.all('application'),[])
    def test_full_5000_rows(self):
        rows=[{'公司':'虚构公司'+str(i),'岗位':'数据分析','城市':'杭州','招聘类型':'校招','毕业届别':'2027','截止日期':'2026-10-15','投递链接':'https://example.invalid/'+str(i),'岗位JD':'虚构JD'} for i in range(5000)]
        r=import_jobs(self.s,self.write_csv(rows));self.assertEqual(r['accepted_rows'],5000);self.assertEqual(r['unique_jobs_in_input'],5000)
    def test_skipped_missing_fields(self):
        rows=[{'公司':'A','岗位':'数据分析'},{'公司':'','岗位':'销售'}];r=import_jobs(self.s,self.write_csv(rows));self.assertEqual(r['skipped_rows'],1)
    def test_xlsx_demo(self):
        path=ROOT/'demo/jobs-fictional.xlsx'
        if not path.exists():self.skipTest('XLSX fixture not yet built')
        rows,report=read_table(path);self.assertEqual(len(rows),13);self.assertGreaterEqual(len(report['sheets']),2)
    def test_formula_csv_escape(self):
        for v in ['=1+1','+X','-4','@SUM(A1)','\t=1+1','  =1+1']:self.assertTrue(safe_cell(v).startswith("'"))
    def test_csv_roundtrip_no_formula(self):
        p=self.base/'safe.csv';write_csv(p,[{'x':'=1+1'}],['x']);self.assertIn("'=1+1",p.read_text(encoding='utf-8-sig'))
    def test_draft_not_submitted(self):
        r=set_application(self.s,'job-demo','draft_filled','draft','已填写未提交');self.assertFalse(r['ever_submitted'])
    def test_submitted_rejects_draft_evidence(self):
        with self.assertRaises(ValueError):set_application(self.s,'job-demo','submitted','draft','已填')
    def test_submitted_user_report(self):
        r=set_application(self.s,'job-demo','submitted','user_report','用户明确已提交');self.assertTrue(r['ever_submitted'])
    def test_stage_backwards_blocked(self):
        set_application(self.s,'job-demo','submitted','user_report','用户明确已提交')
        with self.assertRaises(ValueError):set_application(self.s,'job-demo','draft_filled','draft','回退')
    def test_stage_history_kept(self):
        set_application(self.s,'job-demo','submitted','user_report','已提交');r=set_application(self.s,'job-demo','interview','user_report','收到面试');self.assertEqual(len(r['history']),2)
    def test_unregistered_resume_refused(self):
        with self.assertRaises(ValueError):set_application(self.s,'job-demo','draft_filled','draft','草稿','unknown')
    def test_timezone_required(self):
        with self.assertRaises(ValueError):validate_due('2026-09-20T10:00:00')
    def test_timezone_accepted(self):validate_due('2026-09-20T10:00:00+08:00')
    def test_date_only_accepted(self):validate_due('2026-09-20')
    def test_daily_converts_timezone(self):
        with self.s.write():
            self.s.put('profile','candidate',{**self.profile,'timezone':'America/Los_Angeles'})
            self.s.put('task','task-a',{'title':'面试','due':'2026-09-18T08:00:00+08:00','done':False})
        r=run(argparse.Namespace(command='daily',date='2026-09-17',timezone=None),self.s)
        self.assertEqual(len(r['tasks']),1);self.assertFalse(r['notifications_enabled'])
    def test_training_no_transcript(self):
        with self.assertRaises(ValueError):validate_training({'question_type':'intro','transcript':'secret'})
    def test_training_no_nested_answers(self):
        with self.assertRaises(ValueError):validate_training({'question_type':'intro','dimensions':{'answer':'secret'}})
    def test_training_score_limit(self):
        with self.assertRaises(ValueError):validate_training({'question_type':'intro','score':101})
    def test_training_summary_valid(self):validate_training({'question_type':'intro','score':70,'improvement_summary':'先说结论','issue_tags':['结构'],'next_actions':['重答']})
    def test_resume_valid(self):self.assertTrue(validate_resume(self.resume,self.profile)['fact_reference_checks_passed'])
    def test_resume_new_metric(self):
        r=copy.deepcopy(self.resume);r['sections'][1]['entries'][0]['bullets'][0]['text']+='效率提升80%'
        with self.assertRaises(ValueError):validate_resume(r,self.profile)
    def test_resume_cross_experience(self):
        r=copy.deepcopy(self.resume);r['sections'][1]['entries'][0]['bullets'][0]['fact_ids']=['f-a1']
        with self.assertRaises(ValueError):validate_resume(r,self.profile)
    def test_resume_unsupported_stronger_claim(self):
        r=copy.deepcopy(self.resume);r['sections'][1]['entries'][0]['bullets'][0]['text']='主导全部数据分析工作'
        with self.assertRaises(ValueError):validate_resume(r,self.profile)
    def test_resume_placeholder(self):
        r=copy.deepcopy(self.resume);r['name']='【待补姓名】'
        with self.assertRaises(ValueError):validate_resume(r,self.profile)
    def test_resume_html_escaping(self):
        r=copy.deepcopy(self.resume);r['name']='<script>alert(1)</script>'
        h,_=render_html(r,'',True,False);self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h)
    def test_demo_banner_always_present(self):
        h,t=render_html(self.resume,'',True,True);self.assertIn('不可投递',h);self.assertIn('不可投递',t)
    def test_demo_registration_blocked(self):
        f=self.base/'manifest.json';f.write_text(json.dumps({'demo':True,'approved_for_use':True,'visual_checked':True}))
        with self.assertRaises(ValueError):register_resume(self.s,f)

    def test_selected_xlsx_sheet(self):
        rows, report=read_table(ROOT/'demo/jobs-fictional.xlsx',selected_sheets=['岗位A'])
        self.assertEqual(len(rows),8)
    def test_selected_missing_sheet_rejected(self):
        with self.assertRaises(ValueError):read_table(ROOT/'demo/jobs-fictional.xlsx',selected_sheets=['不存在'])

if __name__=='__main__':unittest.main()
