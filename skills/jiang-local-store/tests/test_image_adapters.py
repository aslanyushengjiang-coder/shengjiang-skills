#!/usr/bin/env python3
"""Offline protocol regression tests for the Image 2 adapters.

Every HTTP connection is to a temporary loopback TLS server. The only key is
FAKE_KEY. Noise PNGs are protocol fixtures, never generated restaurant visuals.
No production config, account, or model API is read or called.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import shutil
import ssl
import socketserver
import struct
import subprocess
import sys
import threading
import tempfile
import time
import unittest
from unittest import mock
import zlib
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.dont_write_bytecode = True
ROOT = None
DEFAULT_SOURCE = Path(__file__).resolve().parents[1] / 'scripts'
FAKE_KEY = 'fake-selftest-never-bill-0123456789'
STATE = {}
COMMANDS = []
RESULTS = []


def chunk(tag, data):
    return struct.pack('!I', len(data)) + tag + data + struct.pack('!I', zlib.crc32(tag + data) & 0xffffffff)


def noise_fixture():
    rng = random.Random(20260828)
    pixels = b''.join(b'\0' + bytes(rng.randrange(256) for _ in range(128 * 3)) for _ in range(128))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 128, 128, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_bytes(self, status, body, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, body, status=200):
        self.send_bytes(status, json.dumps(body).encode())

    def maybe_redirect_api(self, method):
        prefix = 'api-' + method.lower() + '-redirect-'
        if not STATE['scenario'].startswith(prefix):
            return False
        origin, code = STATE['scenario'][len(prefix):].rsplit('-', 1)
        base = STATE['base'] if origin == 'same' else STATE['redirect_base']
        self.send_response(int(code))
        self.send_header('Location', base + '/api-redirect-destination?mock-secret=' + FAKE_KEY)
        self.send_header('Content-Length', '0')
        self.end_headers()
        return True

    def record(self, body=None):
        req = {'method': self.command, 'path': self.path, 'server_port': self.server.server_port, 'authorization': self.headers.get('Authorization'), 'content_type': self.headers.get('Content-Type')}
        if body is not None:
            ctype = self.headers.get('Content-Type', '')
            if ctype.startswith('multipart/'):
                message = BytesParser(policy=default).parsebytes(('Content-Type: ' + ctype + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + body)
                req['parts'] = [{'name': p.get_param('name', header='Content-Disposition'), 'filename': p.get_filename(), 'type': p.get_content_type(), 'bytes': len(p.get_payload(decode=True) or b''), 'sha256': hashlib.sha256(p.get_payload(decode=True) or b'').hexdigest(), 'text': None if p.get_filename() else (p.get_payload(decode=True) or b'').decode('utf-8')} for p in message.iter_parts()]
            else:
                try:
                    data = json.loads(body)
                    if 'image_urls' in data:
                        req['reference_urls'] = data['image_urls']
                        data = dict(data, image_urls=[{'prefix': u[:30], 'length': len(u)} for u in data['image_urls']])
                    req['json'] = data
                except (ValueError, TypeError):
                    req['body_size'] = len(body)
        STATE['requests'].append(req)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        self.record(body)
        if self.path.startswith('/api-redirect-destination'):
            return self.send_json({'data': []})
        scenario = STATE['scenario']
        if self.headers.get('Authorization') != 'Bearer ' + FAKE_KEY:
            self.send_json({'error': 'MOCK bad Authorization prefix'}, 401)
        elif scenario == 'http-error-echo-key':
            self.send_json({'error': 'MOCK key=' + FAKE_KEY}, 401)
        elif scenario == 'rate-limit':
            self.send_json({'error': 'MOCK rate limited'}, 429)
        elif scenario == 'malformed-json':
            self.send_bytes(200, b'{not-json')
        elif scenario == 'scalar-json':
            self.send_json(['MOCK wrong shape'])
        elif self.maybe_redirect_api('POST'):
            return
        elif STATE['kind'] == 'async':
            self.send_json({'data': [{}]} if scenario == 'missing-task' else {'data': [{'task_id': 'MOCK-TASK-001'}]})
        elif scenario == 'missing-data':
            self.send_json({'data': []})
        elif scenario == 'bad-item':
            self.send_json({'data': [None]})
        elif scenario == 'html-result':
            self.send_json({'data': [{'url': STATE['base'] + '/assets/html.png'}]})
        elif scenario == 'file-result':
            self.send_json({'data': [{'url': STATE['fixture'].as_uri()}]})
        elif scenario in {'redirect-file', 'redirect-https', 'redirect-http'}:
            self.send_json({'data': [{'url': STATE['base'] + '/assets/' + scenario}]})
        elif scenario == 'bad-base64':
            self.send_json({'data': [{'b64_json': '!not-base64!'}]})
        elif scenario == 'url-result':
            self.send_json({'data': [{'url': STATE['base'] + '/assets/fixture.png'}]})
        elif scenario == 'small-result':
            self.send_json({'data': [{'b64_json': base64.b64encode(b'not-image').decode()}]})
        else:
            self.send_json({'data': [{'b64_json': base64.b64encode(STATE['png']).decode()}]})

    def do_GET(self):
        self.record()
        if self.path.startswith('/api-redirect-destination'):
            return self.send_json({'data': []})
        if self.path.startswith('/v1/') and self.maybe_redirect_api('GET'):
            return
        if self.path in {'/assets/redirect-file', '/assets/redirect-https', '/assets/redirect-http'}:
            location = STATE['fixture'].as_uri() if self.path.endswith('file') else STATE['base'] + '/assets/fixture.png'
            if self.path.endswith('-http'):
                location = location.replace('https://', 'http://', 1)
            self.send_response(302)
            self.send_header('Location', location)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if self.path == '/assets/fixture.png':
            return self.send_bytes(200, STATE['png'], 'image/png')
        if self.path == '/assets/html.png':
            return self.send_bytes(200, b'<html>MOCK error page</html>' * 600, 'text/html')
        if self.path == '/v1/models':
            return self.send_json({'data': [{'id': 'gpt-image-2'}]})
        if self.path.startswith('/v1/tasks/'):
            if STATE['scenario'] == 'failed-task':
                return self.send_json({'data': {'status': 'failed', 'error': {'message': 'MOCK failure'}}})
            if STATE['scenario'] == 'failed-task-echo-key':
                return self.send_json({'data': {'status': 'failed', 'error': {'message': 'MOCK key=' + FAKE_KEY}}})
            if STATE['scenario'] in {'processing-forever', 'pending-forever'}:
                return self.send_json({'data': {'status': STATE['scenario'].split('-')[0]}})
            if STATE['scenario'] == 'unknown-status':
                return self.send_json({'data': {'status': 'MOCK-new-state'}})
            statuses = STATE['statuses']
            status = statuses.pop(0) if len(statuses) > 1 else statuses[0]
            data = {'status': status}
            if status == 'completed':
                scenario = STATE['scenario']
                url = STATE['base'] + ('/assets/html.png' if scenario == 'html-result' else '/assets/fixture.png')
                if scenario == 'file-result':
                    url = STATE['fixture'].as_uri()
                images = [] if scenario == 'missing-url' else [{'url': [url]}]
                data.update(result={'images': images}, cost=0)
            return self.send_json({'data': data})
        self.send_json({'error': 'MOCK unknown route'}, 404)


def isolated_env(kind, **overrides):
    env = {'PATH': os.defpath, 'PYTHONDONTWRITEBYTECODE': '1', 'SSL_CERT_FILE': str(ROOT / 'tls-cert.pem'), 'PYTHONPATH': str(ROOT/'mock-runtime'),
           'IMAGE2_CONFIG_FILE': str(ROOT / 'missing-image2.env'), 'APIMART_CONFIG_FILE': str(ROOT / 'missing-apimart.env'),
           'IMAGE2_API_KEY': FAKE_KEY, 'APIMART_API_KEY': FAKE_KEY,
           'IMAGE2_BASE_URL': STATE['base'] + '/v1', 'APIMART_BASE_URL': STATE['base']}
    for key, val in overrides.items():
        if val is None:
            env.pop(key, None)
        else:
            env[key] = val
    return env


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global ROOT
        cls.owned_server = None
        if 'base' not in STATE:
            ROOT = Path(tempfile.mkdtemp(prefix='image2-adapter-selftest-'))
            cls.owned_server = setup(DEFAULT_SOURCE, False)
        cls.redirect_server = start_mock_server()
        STATE['redirect_base'] = 'https://127.0.0.1:' + str(cls.redirect_server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.redirect_server.shutdown()
        cls.redirect_server.server_close()
        if cls.owned_server:
            cls.owned_server.shutdown()
            cls.owned_server.server_close()

    def setUp(self):
        self.out = ROOT / 'outputs' / (self._testMethodName + '-' + str(time.time_ns()))
        self.out.mkdir(parents=True, exist_ok=True)

    def cli(self, kind, args, scenario='success', **env_overrides):
        STATE.update(kind=kind, scenario=scenario, requests=[], statuses=['submitted', 'pending', 'processing', 'completed'])
        path = STATE['sources']['image2_api.py' if kind == 'sync' else 'apimart_image.py']
        argv = [sys.executable, str(path)] + list(args)
        started = time.monotonic()
        cp = subprocess.run(argv, env=isolated_env(kind, **env_overrides), capture_output=True, text=True, timeout=8)
        requests = []
        for r in STATE['requests']:
            requests.append({k: v for k, v in r.items() if k != 'reference_urls'})
        COMMANDS.append({'test': self._testMethodName, 'argv': argv, 'scenario': scenario, 'exit': cp.returncode,
                         'elapsed_seconds': round(time.monotonic()-started, 4), 'stdout': cp.stdout, 'stderr': cp.stderr,
                         'request_count': len(requests), 'requests': requests,
                         'environment_policy': 'Fresh allowlist; fake keys; both config paths override; loopback TLS only'})
        return cp

    def generate(self, kind, scenario='success', extra=(), **env):
        if kind == 'sync':
            args = ['generate', '--prompt', 'MOCK 协议测试，不是门店成图', '--size', '1024x1536', '--output', str(self.out / 'result.png')]
        else:
            args = ['generate', '--prompt', 'MOCK 协议测试，不是门店成图', '--size', '4:5', '--output-dir', str(self.out), '--name', 'protocol-fixture', '--timeout', '5', '--interval', '1']
        return self.cli(kind, args + list(extra), scenario, **env)

    def assert_clean_failure(self, cp, text=None, no_request=False):
        self.assertNotEqual(cp.returncode, 0, cp.stdout)
        self.assertNotIn('Traceback', cp.stderr)
        if text:
            self.assertIn(text, cp.stderr)
        if no_request:
            self.assertEqual([], STATE['requests'])

    def test_01_doctor_missing_key(self):
        for kind, key in [('sync', 'IMAGE2_API_KEY'), ('async', 'APIMART_API_KEY')]:
            cp = self.cli(kind, ['doctor'], **{key: None})
            self.assertEqual(cp.returncode, 2)
            self.assertFalse(json.loads(cp.stdout)['ready'])
            self.assertEqual(STATE['requests'], [])

    def test_02_doctor_fake_key_is_only_config_ready(self):
        for kind in ['sync', 'async']:
            cp = self.cli(kind, ['doctor'])
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertTrue(json.loads(cp.stdout)['ready'])
            self.assertNotIn(FAKE_KEY, cp.stdout + cp.stderr)
            self.assertEqual(STATE['requests'], [])

    def test_03_sync_probe_models_local_mock(self):
        cp = self.cli('sync', ['doctor', '--probe-models'])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertTrue(json.loads(cp.stdout)['models_probe']['target_model_visible'])
        self.assertEqual([r['path'] for r in STATE['requests']], ['/v1/models'])

    def test_04_config_permission_guard(self):
        path = ROOT / 'world-readable-fake.env'
        path.write_text('IMAGE2_API_KEY=' + FAKE_KEY + '\n')
        path.chmod(0o644)
        for kind, key in [('sync', 'IMAGE2_CONFIG_FILE'), ('async', 'APIMART_CONFIG_FILE')]:
            cp = self.cli(kind, ['doctor'], **{key: str(path)})
            self.assert_clean_failure(cp, 'permissions are too open', no_request=True)

    def test_05_dry_run_without_key_or_output(self):
        for kind in ['sync', 'async']:
            key = 'IMAGE2_API_KEY' if kind == 'sync' else 'APIMART_API_KEY'
            cp = self.cli(kind, ['generate', '--prompt', 'MOCK payload preview', '--dry-run'], **{key: None})
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertTrue(json.loads(cp.stdout)['dry_run'])
            self.assertEqual(STATE['requests'], [])
            self.assertEqual(list(self.out.iterdir()), [])

    def test_06_sync_generate_json_and_base64(self):
        cp = self.generate('sync')
        self.assertEqual(cp.returncode, 0, cp.stderr)
        payload = STATE['requests'][0]['json']
        self.assertEqual(payload['model'], 'gpt-image-2')
        self.assertEqual(payload['n'], 1)
        self.assertEqual(payload['size'], '1024x1536')
        self.assertNotIn('input_fidelity', payload)
        self.assertNotIn('background', payload)
        self.assertEqual((self.out / 'result.png').read_bytes(), STATE['png'])

    def test_07_sync_edit_multipart_two_references_and_mask(self):
        cp = self.cli('sync', ['edit', '--prompt', 'MOCK 保留参考像素语义', '--image', str(STATE['fixture']), '--image', str(STATE['fixture']), '--mask', str(STATE['fixture']), '--size', '1024x1536', '--output', str(self.out / 'edit.png')])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(STATE['requests'][0]['path'], '/v1/images/edits')
        parts = STATE['requests'][0]['parts']
        images = [p for p in parts if p['filename']]
        self.assertEqual([p['name'] for p in images], ['image[]', 'image[]', 'mask'])
        self.assertTrue(all(p['sha256'] == hashlib.sha256(STATE['png']).hexdigest() for p in images))
        self.assertEqual((self.out / 'edit.png').read_bytes(), STATE['png'])

    def test_08_sync_url_result_download(self):
        cp = self.generate('sync', 'url-result')
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual((self.out / 'result.png').read_bytes(), STATE['png'])
        self.assertIsNone(STATE['requests'][-1]['authorization'])

    def test_09_async_submit_poll_download(self):
        cp = self.generate('async')
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(json.loads(cp.stdout)['reported_cost_usd'], 0)
        self.assertEqual(STATE['requests'][0]['json']['n'], 1)
        polls = [r for r in STATE['requests'] if r['path'].startswith('/v1/tasks/')]
        self.assertEqual(len(polls), 4)
        self.assertEqual(len({r['path'] for r in polls}), 1)
        self.assertEqual(len([r for r in STATE['requests'] if r['method'] == 'POST']), 1)
        self.assertEqual((self.out / 'protocol-fixture-01.png').read_bytes(), STATE['png'])
        self.assertIsNone(STATE['requests'][-1]['authorization'])

    def test_10_async_reference_edit_json_data_uri(self):
        cp = self.generate('async', extra=['--reference-image', str(STATE['fixture'])])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        refs = STATE['requests'][0]['reference_urls']
        self.assertEqual(len(refs), 1)
        self.assertTrue(refs[0].startswith('data:image/png;base64,'))
        self.assertEqual(base64.b64decode(refs[0].split(',', 1)[1]), STATE['png'])

    def test_11_async_submit_only_no_false_completed_files(self):
        cp = self.generate('async', extra=['--submit-only'])
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(json.loads(cp.stdout)['status'], 'submitted')
        self.assertNotIn('files', json.loads(cp.stdout))
        self.assertEqual(len(STATE['requests']), 1)

    def test_12_empty_prompt_rejected(self):
        for kind in ['sync', 'async']:
            cp = self.generate(kind, extra=['--prompt', '  '])
            self.assert_clean_failure(cp, 'Prompt cannot be empty', no_request=True)

    def test_13_reference_count_limit(self):
        args = sum((['--reference-image', str(STATE['fixture'])] for _ in range(17)), [])
        cp = self.generate('async', extra=args)
        self.assert_clean_failure(cp, 'at most 16', no_request=True)
        cp = self.cli('sync', ['edit', '--prompt', 'MOCK', '--output', str(self.out/'edit.png')] + sum((['--image', str(STATE['fixture'])] for _ in range(17)), []))
        self.assert_clean_failure(cp, 'at most 16', no_request=True)

    def test_14_missing_reference_rejected(self):
        cp = self.generate('async', extra=['--reference-image', str(ROOT/'missing.png')])
        self.assert_clean_failure(cp, 'does not exist', no_request=True)
        cp = self.cli('sync', ['edit', '--prompt', 'MOCK', '--image', str(ROOT/'missing.png'), '--output', str(self.out/'edit.png')])
        self.assert_clean_failure(cp, 'does not exist', no_request=True)

    def test_15_transparent_background_rejected(self):
        cp = self.generate('sync', extra=['--background', 'transparent'])
        self.assert_clean_failure(cp, 'does not support', no_request=True)

    def test_16_path_traversal_name_rejected(self):
        cp = self.generate('async', extra=['--name', '../escaped'])
        self.assert_clean_failure(cp, 'single filename stem', no_request=True)

    def test_17_http_errors_and_missing_results(self):
        for kind in ['sync', 'async']:
            cp = self.generate(kind, 'rate-limit')
            self.assert_clean_failure(cp, 'HTTP 429')
        cp = self.generate('sync', 'missing-data')
        self.assert_clean_failure(cp, 'no data array')
        cp = self.generate('async', 'missing-task')
        self.assert_clean_failure(cp, 'no task_id')
        cp = self.generate('async', 'missing-url')
        self.assert_clean_failure(cp, 'no image URL')

    def test_18_async_failed_and_unknown_status(self):
        cp = self.generate('async', 'failed-task')
        self.assert_clean_failure(cp, 'task failed')
        cp = self.generate('async', 'unknown-status')
        self.assert_clean_failure(cp, 'Unexpected')

    def test_19_async_poll_deadline(self):
        for scenario in ['processing-forever', 'pending-forever']:
            with self.subTest(scenario=scenario):
                cp = self.generate('async', scenario, extra=['--timeout', '1', '--interval', '1'])
                self.assert_clean_failure(cp, 'Timed out waiting')
                self.assertFalse(list(self.out.glob('*.png')))

    def test_20_sync_env_auth_prefix_preserves_space(self):
        cp = self.generate('sync', IMAGE2_AUTH_PREFIX='Bearer ')
        self.assertEqual(cp.returncode, 0, 'Expected normal Bearer authentication: ' + cp.stderr)

    def test_21_sync_http_error_does_not_echo_key(self):
        cp = self.generate('sync', 'http-error-echo-key')
        self.assertNotIn(FAKE_KEY, cp.stdout + cp.stderr)

    def test_22_async_http_error_does_not_echo_non_sk_key(self):
        cp = self.generate('async', 'http-error-echo-key')
        self.assertNotIn(FAKE_KEY, cp.stdout + cp.stderr)

    def test_23_async_task_error_does_not_echo_non_sk_key(self):
        cp = self.generate('async', 'failed-task-echo-key')
        self.assertNotIn(FAKE_KEY, cp.stdout + cp.stderr)

    def test_24_sync_rejects_html_response(self):
        cp = self.generate('sync', 'html-result')
        self.assertNotEqual(cp.returncode, 0, 'HTML bytes were declared an image: ' + cp.stdout)

    def test_25_async_rejects_html_response(self):
        cp = self.generate('async', 'html-result')
        self.assertNotEqual(cp.returncode, 0, 'HTML bytes were declared an image: ' + cp.stdout)

    def test_26_sync_rejects_file_scheme_response(self):
        cp = self.generate('sync', 'file-result')
        self.assertNotEqual(cp.returncode, 0, 'Provider URL read a local fixture file: ' + cp.stdout)

    def test_27_async_rejects_file_scheme_response(self):
        cp = self.generate('async', 'file-result')
        self.assertNotEqual(cp.returncode, 0, 'Provider URL read a local fixture file: ' + cp.stdout)

    def test_28_sync_zero_size_cleanly_rejected(self):
        cp = self.generate('sync', extra=['--size', '0x0'])
        self.assert_clean_failure(cp, no_request=True)

    def test_29_async_zero_size_rejected_before_submission(self):
        cp = self.generate('async', extra=['--size', '0x0'])
        self.assert_clean_failure(cp, no_request=True)

    def test_30_async_zero_timeout_rejected_before_submission(self):
        cp = self.generate('async', extra=['--timeout', '0'])
        self.assert_clean_failure(cp, no_request=True)

    def test_31_async_negative_interval_rejected_before_submission(self):
        cp = self.generate('async', extra=['--interval', '-1'])
        self.assert_clean_failure(cp, no_request=True)

    def test_32_sync_malformed_json_has_clean_error(self):
        cp = self.generate('sync', 'malformed-json')
        self.assert_clean_failure(cp)

    def test_33_async_malformed_json_has_clean_error(self):
        cp = self.generate('async', 'malformed-json')
        self.assert_clean_failure(cp)

    def test_34_sync_network_timeout_has_clean_error(self):
        module = STATE['modules']['sync']
        with mock.patch.object(module, 'open_api_request', side_effect=TimeoutError('MOCK socket read timeout')):
            with self.assertRaises(SystemExit):
                module.perform_request(module.urllib.request.Request(STATE['base']))

    def test_35_async_network_timeout_has_clean_error(self):
        module = STATE['modules']['async']
        with mock.patch.object(module, 'open_api_request', side_effect=TimeoutError('MOCK socket read timeout')):
            with self.assertRaises(SystemExit):
                module.request_json('GET', STATE['base'], FAKE_KEY)

    def test_36_sync_rejected_small_output_is_not_left_as_image(self):
        cp = self.generate('sync', 'small-result')
        self.assert_clean_failure(cp)
        self.assertFalse((self.out/'result.png').exists(), 'Rejected bytes left at final output path')

    def test_37_sync_non_image_reference_rejected_before_submission(self):
        cp = self.cli('sync', ['edit', '--prompt', 'MOCK', '--image', str(STATE['text_fixture']), '--output', str(self.out/'result.png')])
        self.assert_clean_failure(cp, no_request=True)

    def test_38_async_non_image_reference_rejected_before_submission(self):
        cp = self.generate('async', extra=['--reference-image', str(STATE['text_fixture'])])
        self.assert_clean_failure(cp, no_request=True)

    def test_39_async_zero_interval_rejected_before_submission(self):
        cp = self.generate('async', extra=['--interval', '0'])
        self.assert_clean_failure(cp, no_request=True)

    def test_40_download_redirect_to_file_rejected(self):
        cp = self.generate('sync', 'redirect-file')
        self.assert_clean_failure(cp)
        self.assertFalse((self.out/'result.png').exists())
        self.assertTrue(any(r['path'] == '/assets/redirect-file' for r in STATE['requests']))

    def test_41_download_https_redirect_still_works(self):
        cp = self.generate('sync', 'redirect-https')
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual((self.out/'result.png').read_bytes(), STATE['png'])
        self.assertTrue(all(r['authorization'] is None for r in STATE['requests'] if r['path'].startswith('/assets/')))

    def test_42_download_https_downgrade_rejected(self):
        cp = self.generate('sync', 'redirect-http')
        self.assert_clean_failure(cp, 'downgrade')
        self.assertFalse((self.out/'result.png').exists())

    def test_43_invalid_base64_and_data_shape_rejected_cleanly(self):
        for scenario in ['bad-base64', 'bad-item', 'scalar-json']:
            cp = self.generate('sync', scenario)
            self.assert_clean_failure(cp)
            self.assertFalse((self.out/'result.png').exists())
        cp = self.generate('async', 'scalar-json')
        self.assert_clean_failure(cp)

    def test_44_png_crc_pixel_stream_and_bomb_rejected(self):
        validator = STATE['modules']['sync'].validate_image_bytes
        corrupted = bytearray(STATE['png'])
        corrupted[45] ^= 1
        bad_pixels = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0')) + chunk(b'IEND', b'')
        bomb = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 100000, 100000, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0')) + chunk(b'IEND', b'')
        for data in [bytes(corrupted), STATE['png'][:-12], bad_pixels, bomb, b'\x89PNG\r\n\x1a\n' + b'not-pixels'*2000]:
            with self.assertRaises(SystemExit):
                validator(data)

    def test_45_valid_small_png_is_not_rejected_by_file_size(self):
        data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 1, 1, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0\xff\0\0')) + chunk(b'IEND', b'')
        module = STATE['modules']['sync']
        self.assertEqual(module.validate_image_bytes(data), 'png')
        target = self.out/'valid-small-protocol-fixture.png'
        module.atomic_write_image(target, data)
        self.assertEqual(target.read_bytes(), data)

    def test_46_atomic_rejection_keeps_existing_output(self):
        target = self.out/'result.png'
        target.write_bytes(STATE['png'])
        cp = self.generate('sync', 'html-result')
        self.assert_clean_failure(cp)
        self.assertEqual(target.read_bytes(), STATE['png'])
        self.assertEqual(list(self.out.glob('*.tmp')), [])

    def test_47_atomic_rename_error_removes_temporary_file(self):
        module = STATE['modules']['sync']
        target = self.out/'result.png'
        with mock.patch.object(module.os, 'replace', side_effect=OSError('MOCK rename denied')):
            with self.assertRaises(SystemExit):
                module.atomic_write_image(target, STATE['png'])
        self.assertFalse(target.exists())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_48_reference_data_uri_type_and_bytes_checked(self):
        for data_uri in ['data:image/png;base64,!invalid!', 'data:image/png;base64,' + base64.b64encode(b'not-an-image').decode(), 'data:image/jpeg;base64,' + base64.b64encode(STATE['png']).decode()]:
            cp = self.generate('async', extra=['--reference-image', data_uri])
            self.assert_clean_failure(cp, no_request=True)

    def test_49_redaction_happens_before_truncation(self):
        module = STATE['modules']['sync']
        message = 'MOCK ' + 'x'*990 + FAKE_KEY
        self.assertNotIn(FAKE_KEY, module.redact_sensitive(message, FAKE_KEY))
        self.assertNotIn(FAKE_KEY[:12], module.redact_sensitive(message, FAKE_KEY)[:1000])

    def test_50_direct_download_url_protocol_guard(self):
        module = STATE['modules']['sync']
        for url in ['file:///tmp/mock.png', 'ftp://127.0.0.1/mock.png', 'data:image/png;base64,AAAA', '//127.0.0.1/mock.png', 'https://user:password@127.0.0.1/mock.png']:
            with self.assertRaises(SystemExit):
                module.validate_download_url(url)

    def test_51_png_output_format_mismatch_rejected(self):
        with self.assertRaises(SystemExit):
            STATE['modules']['sync'].atomic_write_image(self.out/'mismatch.jpg', STATE['png'], 'jpeg')
        self.assertFalse((self.out/'mismatch.jpg').exists())

    def test_52_sync_edit_dry_run_summarizes_local_reference(self):
        cp = self.cli('sync', ['edit', '--prompt', 'MOCK', '--image', str(STATE['fixture']), '--mask', str(STATE['fixture']), '--size', '1024x1536', '--dry-run'], IMAGE2_API_KEY=None)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        data = json.loads(cp.stdout)
        self.assertEqual(data['content_type'], 'multipart/form-data')
        self.assertTrue(data['url'].endswith('/images/edits'))
        self.assertEqual(data['references'][0]['sha256'], hashlib.sha256(STATE['png']).hexdigest())
        self.assertEqual((data['references'][0]['width'], data['references'][0]['height']), (128, 128))
        self.assertEqual(data['mask']['sha256'], data['references'][0]['sha256'])
        self.assertNotIn(str(STATE['fixture']), cp.stdout)
        self.assertEqual(STATE['requests'], [])

    def test_53_dry_run_does_not_print_key_prompt_or_base64(self):
        private_prompt = 'MOCK private prompt contains ' + FAKE_KEY
        for kind in ['sync', 'async']:
            extra = ['--reference-image', str(STATE['fixture'])] if kind == 'async' else []
            cp = self.cli(kind, ['generate', '--prompt', private_prompt, '--dry-run'] + extra)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertNotIn(FAKE_KEY, cp.stdout + cp.stderr)
            self.assertNotIn(private_prompt, cp.stdout)
            self.assertNotIn('data:image/', cp.stdout)
            self.assertEqual(json.loads(cp.stdout)['prompt']['sha256'], hashlib.sha256(private_prompt.encode()).hexdigest())
            self.assertEqual(STATE['requests'], [])

    def test_54_dry_run_invalid_inputs_still_fail_without_key(self):
        for kind, key in [('sync', 'IMAGE2_API_KEY'), ('async', 'APIMART_API_KEY')]:
            cp = self.cli(kind, ['generate', '--prompt', 'MOCK', '--size', '0x0', '--dry-run'], **{key: None})
            self.assert_clean_failure(cp, no_request=True)
            cp = self.cli(kind, ['generate', '--prompt-file', str(ROOT/'missing-prompt.txt'), '--dry-run'], **{key: None})
            self.assert_clean_failure(cp, no_request=True)
        cp = self.cli('sync', ['edit', '--prompt', 'MOCK', '--image', str(ROOT/'missing.png'), '--dry-run'], IMAGE2_API_KEY=None)
        self.assert_clean_failure(cp, no_request=True)
        cp = self.cli('async', ['generate', '--prompt', 'MOCK', '--reference-image', str(ROOT/'missing.png'), '--dry-run'], APIMART_API_KEY=None)
        self.assert_clean_failure(cp, no_request=True)

    def test_55_async_remote_reference_dry_run_does_not_fetch(self):
        cp = self.cli('async', ['generate', '--prompt', 'MOCK', '--reference-image', STATE['base'] + '/assets/fixture.png?signed-token=MOCK-PRIVATE-URL', '--dry-run'], APIMART_API_KEY=None)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        reference = json.loads(cp.stdout)['references'][0]
        self.assertIsNone(reference['sha256'])
        self.assertIsNone(reference['width'])
        self.assertNotIn('MOCK-PRIVATE-URL', cp.stdout)
        self.assertEqual(STATE['requests'], [])

    def test_56_dry_run_parameters_match_real_constructed_payload(self):
        for kind in ['sync', 'async']:
            cp = self.generate(kind, extra=['--dry-run'])
            self.assertEqual(cp.returncode, 0, cp.stderr)
            preview = json.loads(cp.stdout)
            self.assertEqual(STATE['requests'], [])
            cp = self.generate(kind)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            actual = STATE['requests'][0]['json']
            self.assertEqual(preview['parameters'], {k: v for k, v in actual.items() if k not in {'prompt', 'image_urls'}})
            self.assertEqual(preview['prompt']['sha256'], hashlib.sha256(actual['prompt'].encode()).hexdigest())

    def test_57_real_generate_still_requires_output_before_http(self):
        for kind in ['sync', 'async']:
            cp = self.cli(kind, ['generate', '--prompt', 'MOCK'])
            self.assert_clean_failure(cp, 'required', no_request=True)

    def test_58_cli_help_explains_no_http_dry_run(self):
        for kind, command in [('sync', 'generate'), ('sync', 'edit'), ('async', 'generate')]:
            cp = self.cli(kind, [command, '--help'])
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertIn('--dry-run', cp.stdout)
            self.assertIn('without HTTP', cp.stdout)
            self.assertEqual(STATE['requests'], [])

    def test_59_async_dry_run_checks_reference_data(self):
        cp = self.cli('async', ['generate', '--prompt', 'MOCK', '--reference-image', str(STATE['fixture']), '--dry-run'], APIMART_API_KEY=None)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        ref = json.loads(cp.stdout)['references'][0]
        self.assertEqual(ref['sha256'], hashlib.sha256(STATE['png']).hexdigest())
        self.assertEqual((ref['width'], ref['height']), (128, 128))
        cp = self.cli('async', ['generate', '--prompt', 'MOCK', '--reference-image', str(STATE['text_fixture']), '--dry-run'], APIMART_API_KEY=None)
        self.assert_clean_failure(cp, no_request=True)

    def assert_api_redirect_blocked(self, cp, kind, method):
        self.assert_clean_failure(cp, 'API redirect rejected')
        self.assertNotIn(FAKE_KEY, cp.stdout + cp.stderr)
        self.assertNotIn('/api-redirect-destination', cp.stdout + cp.stderr)
        expected_methods = ['POST', 'GET'] if kind == 'async' and method == 'GET' else [method]
        self.assertEqual([r['method'] for r in STATE['requests']], expected_methods)
        self.assertFalse(any(r['path'].startswith('/api-redirect-destination') for r in STATE['requests']))
        self.assertEqual(list(self.out.iterdir()), [], 'Redirect rejection must not create output files')

    def check_api_post_redirects(self, kind, origin):
        for code in [301, 302, 303, 307, 308]:
            with self.subTest(kind=kind, origin=origin, status=code):
                cp = self.generate(kind, 'api-post-redirect-' + origin + '-' + str(code))
                self.assert_api_redirect_blocked(cp, kind, 'POST')

    def test_60_sync_authenticated_post_same_origin_redirects_rejected(self):
        self.check_api_post_redirects('sync', 'same')

    def test_61_sync_authenticated_post_cross_origin_redirects_rejected(self):
        self.check_api_post_redirects('sync', 'cross')

    def test_62_async_authenticated_post_same_origin_redirects_rejected(self):
        self.check_api_post_redirects('async', 'same')

    def test_63_async_authenticated_post_cross_origin_redirects_rejected(self):
        self.check_api_post_redirects('async', 'cross')

    def test_64_sync_authenticated_models_get_redirects_rejected(self):
        for origin in ['same', 'cross']:
            for code in [301, 302, 303, 307, 308]:
                with self.subTest(origin=origin, status=code):
                    cp = self.cli('sync', ['doctor', '--probe-models'], 'api-get-redirect-' + origin + '-' + str(code))
                    self.assert_api_redirect_blocked(cp, 'sync', 'GET')

    def test_65_async_authenticated_poll_get_redirects_rejected(self):
        for origin in ['same', 'cross']:
            for code in [301, 302, 303, 307, 308]:
                with self.subTest(origin=origin, status=code):
                    cp = self.generate('async', 'api-get-redirect-' + origin + '-' + str(code))
                    self.assert_api_redirect_blocked(cp, 'async', 'GET')

    def test_66_sync_multipart_edit_redirects_rejected(self):
        for origin in ['same', 'cross']:
            for code in [302, 307, 308]:
                with self.subTest(origin=origin, status=code):
                    cp = self.cli('sync', ['edit', '--prompt', 'MOCK edit redirect', '--image', str(STATE['fixture']), '--output', str(self.out/'result.png')], 'api-post-redirect-' + origin + '-' + str(code))
                    self.assert_api_redirect_blocked(cp, 'sync', 'POST')


class RecordingResult(unittest.TextTestResult):
    def startTest(self, test):
        self.started = time.monotonic()
        super().startTest(test)

    def record(self, test, status, err=None):
        item = {'id': test._testMethodName, 'status': status, 'seconds': round(time.monotonic()-self.started, 4)}
        if err:
            item['evidence'] = self._exc_info_to_string(err, test)
        RESULTS.append(item)

    def addSuccess(self, test):
        self.record(test, 'pass')
        super().addSuccess(test)

    def addFailure(self, test, err):
        self.record(test, 'fail', err)
        super().addFailure(test, err)

    def addError(self, test, err):
        self.record(test, 'fail', err)
        super().addError(test, err)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            existing = next((item for item in RESULTS if item['id'] == test._testMethodName), None)
            if existing is None:
                self.record(test, 'fail', err)
            else:
                existing['evidence'] += '\n' + str(subtest) + '\n' + self._exc_info_to_string(err, test)
        super().addSubTest(test, subtest, err)


def start_mock_server():
    class LoopbackServer(ThreadingHTTPServer):
        def server_bind(self):
            socketserver.TCPServer.server_bind(self)
            self.server_name = 'localhost'
            self.server_port = self.server_address[1]
    server = LoopbackServer(('127.0.0.1', 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(ROOT/'tls-cert.pem'), str(ROOT/'tls-key.pem'))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def setup(source, snapshot):
    ROOT.mkdir(parents=True, exist_ok=True)
    dest = ROOT/'original-source'
    if snapshot:
        dest.mkdir(exist_ok=True)
        for filename in ['image2_api.py', 'apimart_image.py']:
            target = dest/filename
            if target.exists() and target.read_bytes() != (source/filename).read_bytes():
                raise SystemExit('Snapshot exists and differs; preserve it; select --source and --live-source for a separate regression run.')
            target.write_bytes((source/filename).read_bytes())
    else:
        dest = source
    STATE['sources'] = {n: dest/n for n in ['image2_api.py', 'apimart_image.py']}
    sys.path.insert(0, str(dest))
    STATE['modules'] = {}
    for kind, filename in [('sync', 'image2_api.py'), ('async', 'apimart_image.py')]:
        spec = importlib.util.spec_from_file_location('selftest_'+kind, dest/filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        STATE['modules'][kind] = module
    STATE['png'] = noise_fixture()
    STATE['fixture'] = ROOT/'protocol-noise-fixture.png'
    STATE['fixture'].write_bytes(STATE['png'])
    STATE['text_fixture'] = ROOT/'not-an-image.txt'
    STATE['text_fixture'].write_text('MOCK plain text; not an image.\n'*600)
    config = ROOT/'tls-openssl.cnf'
    config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\n')
    if not (ROOT/'tls-cert.pem').exists():
        cp = subprocess.run(['/usr/bin/openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(ROOT/'tls-key.pem'), '-out', str(ROOT/'tls-cert.pem'), '-days', '1', '-config', str(config)], capture_output=True, text=True, check=True)
        (ROOT/'tls-key.pem').chmod(0o600)
    runtime = ROOT/'mock-runtime'
    runtime.mkdir(exist_ok=True)
    (runtime/'sitecustomize.py').write_text('''# Test-process-only CA trust. No TLS verification is disabled.\nimport os\nimport ssl\ndef local_fixture_https_context(*args, **kwargs):\n    return ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])\nssl._create_default_https_context = local_fixture_https_context\n''')
    server = start_mock_server()
    STATE['base'] = 'https://127.0.0.1:' + str(server.server_port)
    return server


def main():
    global ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--live-source', action='store_true', help='Use explicit source for regression without replacing original snapshot')
    parser.add_argument('--output-root', type=Path, help='All evidence and TLS fixtures go outside the skill source')
    args = parser.parse_args()
    ROOT = args.output_root.resolve() if args.output_root else Path(tempfile.mkdtemp(prefix='image2-adapter-selftest-'))
    if ROOT == DEFAULT_SOURCE.parent or DEFAULT_SOURCE.parent in ROOT.parents:
        raise SystemExit('Test artifacts must be outside the Skill source.')
    server = setup(args.source, not args.live_source)
    capture = io.StringIO()
    try:
        result = unittest.TextTestRunner(stream=capture, verbosity=2, resultclass=RecordingResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests))
    finally:
        server.shutdown()
        server.server_close()
    (ROOT/'unittest-output.txt').write_text(capture.getvalue())
    report = {'checked_at': datetime.datetime.now().astimezone().isoformat(), 'execution_type': 'CLI against LOCAL MOCK TLS + injected unit edge cases',
              'real_api_used': False, 'real_key_read': False, 'paid_requests': 0, 'model_images_generated': 0,
              'sources': {n: {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for n, p in STATE['sources'].items()},
              'summary': {'tests': result.testsRun, 'pass': sum(r['status']=='pass' for r in RESULTS), 'fail': sum(r['status']=='fail' for r in RESULTS), 'cli_invocations': len(COMMANDS)},
              'tests': RESULTS, 'commands': COMMANDS,
              'not_tested': ['Real vendor API/model identity/balance/billing/privacy', 'Actual image quality, exact text, dish identity or mask fidelity', 'Production credentials or Flova workflow', 'Large-scale concurrency/rate-limit retries/resume', 'Public-network DNS rebinding or proxy interception']}
    (ROOT/'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report['summary'], ensure_ascii=False))
    print('Evidence: ' + str(ROOT))
    print('Failing cases: ' + ', '.join(r['id'] for r in RESULTS if r['status']=='fail'))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
