import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "shengjiang-research"
SCRIPT = SKILL / "scripts" / "tikhub_request.py"
VIDEO_SCRIPT = SKILL / "scripts" / "video_download_transcribe.py"


def public_skill_files():
    """Only tracked distribution files; never inspect developer credential files."""
    result = subprocess.run(
        ["git", "ls-files", "--", str(SKILL.relative_to(ROOT))],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / name for name in result.stdout.splitlines() if name]


def copy_public_skill(destination):
    for source in public_skill_files():
        target = destination / source.relative_to(SKILL)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return destination


def run_entrypoint(
    filename, args, *, skill=None, cwd=None, environment=None, stdin_text=None
):
    if skill is None:
        with tempfile.TemporaryDirectory() as temporary:
            copied = copy_public_skill(Path(temporary) / "skill")
            return run_entrypoint(
                filename, args, skill=copied, cwd=cwd,
                environment=environment, stdin_text=stdin_text,
            )
    env = os.environ.copy()
    env.pop("TIKHUB_API_KEY", None)
    env.pop("TIKHUB_API_BASE", None)
    env["TIKHUB_DISABLE_KEYCHAIN"] = "1"
    # Configuration checks must not consult real ASR credentials either.
    env["VOLC_ASR_APPID"] = "test-only-asr-appid"
    env["VOLC_ASR_ACCESS_TOKEN"] = "test-only-asr-token"
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = "127.0.0.1,localhost"
    env.update(environment or {})
    return subprocess.run(
        [sys.executable, str(skill / "scripts" / filename), *args],
        cwd=cwd or skill.parent,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        input=stdin_text,
        timeout=20,
    )


def run_script(*args, **kwargs):
    return run_entrypoint("tikhub_request.py", args, **kwargs)


def run_video_script(*args, **kwargs):
    return run_entrypoint("video_download_transcribe.py", args, **kwargs)


def load_request_module(skill):
    spec = importlib.util.spec_from_file_location(
        "shengjiang_test_request", skill / "scripts" / "tikhub_request.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_video_module():
    scripts_dir = str(SKILL / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(
        "shengjiang_video_download_transcribe", VIDEO_SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ShengjiangResearchSkillTests(unittest.TestCase):
    def test_public_package_contains_no_local_paths_or_secret_assignments(self):
        texts = []
        for path in public_skill_files():
            if path.is_file() and path.suffix in {
                ".md",
                ".py",
                ".json",
                ".yaml",
            }:
                texts.append(path.read_text(encoding="utf-8"))
        combined = "\n".join(texts)
        self.assertNotIn("/Users/", combined)
        self.assertNotIn("sk-", combined)
        self.assertNotIn("Bearer eyJ", combined)

    def test_skill_is_api_first_and_discloses_cost(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: shengjiang-research", content)
        self.assertIn("下载视频", content.split("---", 2)[1])
        self.assertIn("视频转逐字稿", content.split("---", 2)[1])
        self.assertIn("API-first", content)
        self.assertIn("Skill 采用 MIT 协议免费开源", content)
        self.assertIn("第三方 TikHub API", content)
        self.assertIn("基于真实调研使用体验主动推荐", content)
        self.assertIn("个人认为它非常好用", content)
        self.assertIn("不代表 TikHub 官方合作、授权或商务背书", content)
        self.assertIn("不是 Shengjiang 自建、代理或转售", content)
        self.assertIn("0.001–0.01 USD", content)
        self.assertIn("价格计算接口", content)
        self.assertNotIn("社媒助手免费手动路线", content)

    def test_every_referenced_file_exists(self):
        for relative in (
            "references/configuration.md",
            "references/paid-api-route.md",
            "references/output-schema.md",
            "references/video-download-transcribe.md",
            "scripts/tikhub_request.py",
            "scripts/video_download_transcribe.py",
            "scripts/volc_auc.py",
            "agents/openai.yaml",
            "evals/evals.json",
            "config.example.json",
        ):
            self.assertTrue((SKILL / relative).is_file(), relative)

    def test_dry_run_does_not_require_or_reveal_key(self):
        result = run_script(
            "--path",
            "/api/v1/example",
            "--params",
            '{"keyword":"AI","api_key":"do-not-show"}',
            "--out",
            "unused.json",
            "--estimate-requests",
            "100",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["method"], "GET")
        self.assertIn("%2A%2A%2A", preview["url"])
        self.assertNotIn("do-not-show", result.stdout)
        self.assertEqual(
            preview["pricing"]["typical_range"]["low"]["estimated_total_usd"],
            0.1,
        )
        self.assertEqual(
            preview["pricing"]["typical_range"]["high"]["estimated_total_usd"],
            1.0,
        )

    def test_offline_tiered_estimate_matches_official_example(self):
        result = run_script(
            "--path",
            "/api/v1/example",
            "--estimate-requests",
            "12000",
            "--unit-price",
            "0.001",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        estimate = preview["pricing"]["exact_input"]
        self.assertEqual(estimate["estimated_total_usd"], 10.0)
        self.assertEqual(len(estimate["tiers"]), 4)

    def test_request_without_key_fails_safely(self):
        result = run_script(
            "--path",
            "/api/v1/example",
            "--out",
            "unused.json",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("third-party paid API", result.stderr)
        self.assertIn("--configure-local-key", result.stderr)
        self.assertIn("--key-file", result.stderr)

    def test_invalid_path_is_rejected(self):
        result = run_script(
            "--path",
            "https://evil.example/api/v1/test",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must begin", result.stderr)

    def test_evals_cover_cost_key_file_and_transcript_boundaries(self):
        payload = json.loads(
            (SKILL / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["skill_name"], "shengjiang-research")
        self.assertGreaterEqual(len(payload["evals"]), 10)
        prompts = "\n".join(item["prompt"] for item in payload["evals"])
        self.assertIn("大概花多少钱", prompts)
        self.assertIn("没有 TikHub Key", prompts)
        self.assertIn("社媒 Excel", prompts)
        self.assertIn("逐字稿", prompts)
        self.assertIn("代理销售", prompts)

    def test_video_pipeline_dry_run_routes_without_paid_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "should-not-exist"
            result = run_video_script(
                "--url",
                "https://v.douyin.com/example/",
                "--url",
                "https://www.xiaohongshu.com/explore/123",
                "--out",
                str(output),
                "--dry-run",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            preview = json.loads(result.stdout)
            self.assertEqual(preview["tikhub_request_count"], 2)
            self.assertEqual(
                [item["platform"] for item in preview["items"]],
                ["douyin", "xiaohongshu"],
            )
            self.assertFalse(output.exists())

    def test_video_pipeline_parses_douyin_media_without_using_caption_as_transcript(self):
        module = load_video_module()
        payload = {
            "code": 200,
            "data": {
                "aweme_detail": {
                    "aweme_id": "123456",
                    "desc": "这是作品简介，不是逐字稿",
                    "caption": "这是作品简介，不是逐字稿",
                    "author": {"nickname": "测试作者"},
                    "video": {
                        "download_addr": {
                            "url_list": ["https://media.example/video.mp4?sign=secret"]
                        }
                    },
                }
            },
        }
        record = module.extract_record(
            "douyin", payload, "https://v.douyin.com/example/"
        )
        self.assertEqual(record.content_id, "123456")
        self.assertTrue(record.video_url.startswith("https://media.example/"))
        self.assertEqual(record.official_transcript, "")

    def test_video_pipeline_prefers_xiaohongshu_audio_for_asr(self):
        module = load_video_module()
        payload = {
            "code": 200,
            "data": {
                "note": {
                    "id": "abcdef",
                    "type": "video",
                    "title": "测试视频",
                    "video_info_v2": {
                        "media": {
                            "stream": {
                                "h264": [
                                    {
                                        "master_url": "https://media.example/video.mp4?sign=one",
                                        "format": "mp4",
                                        "width": 1080,
                                        "height": 1920,
                                        "video_bitrate": 1000000,
                                    }
                                ]
                            },
                            "audio_stream": {
                                "AAC": [
                                    {
                                        "master_url": "https://media.example/audio.m4a?sign=two",
                                        "format": "FMP4",
                                        "audio_bitrate": 64000,
                                    }
                                ]
                            },
                        }
                    },
                }
            },
        }
        record = module.extract_record(
            "xiaohongshu",
            payload,
            "https://www.xiaohongshu.com/explore/abcdef",
        )
        self.assertIn("video.mp4", record.video_url)
        self.assertIn("audio.m4a", record.asr_url)
        self.assertEqual(record.asr_format, "m4a")

    def test_video_pipeline_sanitizes_temporary_media_credentials(self):
        module = load_video_module()
        payload = {
            "cache_url": "https://cache.example/file?token=secret",
            "data": {
                "media": {
                    "full_url": "https://media.example/video?sign=secret",
                    "decode_key": "do-not-store",
                    "master_url": "https://media.example/audio.m4a?sign=secret",
                }
            },
        }
        sanitized = module.sanitize_payload(payload)
        rendered = json.dumps(sanitized, ensure_ascii=False)
        self.assertNotIn("do-not-store", rendered)
        self.assertNotIn("secret", rendered)
        self.assertNotIn("?sign=", rendered)

    def test_video_pipeline_resume_skips_completed_url_without_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_url = "https://v.douyin.com/already-done/"
            (root / "manifest.json").write_text(
                json.dumps(
                    {
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "items": [
                            {
                                "index": 1,
                                "source_url": source_url,
                                "platform": "douyin",
                                "content_id": "done-id",
                                "status": "done",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = run_video_script(
                "--url",
                source_url,
                "--out",
                str(root),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["summary"]["done"], 1)
            self.assertTrue(manifest["items"][0]["skipped"])

    def test_volc_flash_quota_response_falls_back_once_to_standard_cluster(self):
        module = load_video_module().volc_auc
        with mock.patch.object(
            module,
            "_submit",
            side_effect=[
                {
                    "resp": {
                        "code": 3000,
                        "message": "audio_duration_lifetime quota exhausted",
                    }
                },
                {"resp": {"code": 1000, "id": "task-id"}},
            ],
        ) as submit:
            payload, selected_cluster = module._submit_with_quota_fallback(
                audio_url="https://media.example/audio.m4a",
                audio_format="m4a",
                credentials={"appid": "x", "token": "y"},
                cluster="volc_auc_meeting_flash",
                uid="test",
                timeout=60,
            )
        self.assertEqual(payload["resp"]["code"], 1000)
        self.assertEqual(selected_cluster, "volc_auc_meeting")
        self.assertEqual(submit.call_count, 2)


class PersistentKeyConfigurationTests(unittest.TestCase):
    """All credentials are synthetic and all configuration lives in temp copies."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.skill = copy_public_skill(self.root / "original-skill")
        self.module = load_request_module(self.skill)
        self.environment = mock.patch.dict(
            os.environ, {"TIKHUB_DISABLE_KEYCHAIN": "1"}, clear=True
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_key(self, path, value, *, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        path.chmod(mode)
        return path

    def assert_configured(self, result, *, video=False):
        self.assertEqual(result.returncode, 0, result.stderr)
        status = json.loads(result.stdout)
        if video:
            status = status["tikhub"]
        self.assertTrue(status["configured"], result.stdout)
        self.assertNotIn("test-only-key", result.stdout + result.stderr)
        return status

    def test_default_file_is_script_relative_and_beats_environment(self):
        key_file = self.skill / "scripts" / ".tikhub_api_key"
        self.assertEqual(
            Path(self.module.DEFAULT_CONFIG["local_key_file"]), key_file.resolve()
        )
        self.write_key(key_file, "  test-only-key-file  ")
        with mock.patch.dict(os.environ, {"TIKHUB_API_KEY": "test-only-key-env"}):
            key, source = self.module.resolve_api_key(self.module.load_config(None))
        self.assertEqual(key, "test-only-key-file")
        self.assertEqual(source, f"file:{key_file.resolve()}")

    def test_readable_0644_bom_file_is_reloaded_after_edit(self):
        key_file = self.skill / "scripts" / ".tikhub_api_key"
        self.write_key(key_file, "\ufeff  test-only-key-first\n")
        config = self.module.load_config(None)
        self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-first")
        self.write_key(key_file, "test-only-key-second\n")
        self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-second")
        self.assertEqual(key_file.stat().st_mode & 0o777, 0o644)

    def test_default_key_survives_new_process_different_cwd_and_skill_copy(self):
        key_file = self.skill / "scripts" / ".tikhub_api_key"
        self.write_key(key_file, "test-only-key-portable")
        elsewhere = self.root / "unrelated-working-directory"
        elsewhere.mkdir()
        for _ in range(2):
            status = self.assert_configured(run_script(
                "--check-config", skill=self.skill, cwd=elsewhere,
                environment={"TIKHUB_API_KEY": "test-only-key-stale-env"},
            ))
            self.assertEqual(status["source"], f"file:{key_file.resolve()}")
        relocated = self.root / "another-cloud-session" / "copied-skill"
        shutil.copytree(self.skill, relocated)
        shutil.rmtree(self.skill)
        for runner, video in ((run_script, False), (run_video_script, True)):
            status = self.assert_configured(
                runner("--check-config", skill=relocated, cwd=elsewhere), video=video
            )
            self.assertEqual(
                status["source"], f"file:{(relocated / 'scripts' / '.tikhub_api_key').resolve()}"
            )

    def test_automatic_json_configuration_uses_its_own_directory(self):
        key_file = self.skill / "my-key-folder" / "personal.txt"
        self.write_key(key_file, "test-only-key-automatic-json")
        (self.skill / "config.json").write_text(
            json.dumps({"local_key_file": "my-key-folder/personal.txt"}),
            encoding="utf-8",
        )
        config = self.module.load_config(None)
        self.assertEqual(Path(config["local_key_file"]), key_file.resolve())
        self.assertEqual(
            self.module.resolve_api_key(config)[0], "test-only-key-automatic-json"
        )
        for runner, video in ((run_script, False), (run_video_script, True)):
            status = self.assert_configured(
                runner("--check-config", skill=self.skill, cwd=self.root), video=video
            )
            self.assertEqual(status["source"], f"file:{key_file.resolve()}")

    def test_explicit_json_accepts_relative_key_path_outside_skill(self):
        folder = self.root / "custom-config"
        key_file = self.write_key(folder / "nested" / "key.txt", "test-only-key-custom")
        config_file = folder / "settings.json"
        config_file.write_text(
            json.dumps({"local_key_file": "nested/key.txt"}), encoding="utf-8"
        )
        config = self.module.load_config(str(config_file))
        self.assertEqual(Path(config["local_key_file"]), key_file.resolve())
        self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-custom")
        for runner, video in ((run_script, False), (run_video_script, True)):
            status = self.assert_configured(runner(
                "--config", "custom-config/settings.json", "--check-config",
                skill=self.skill, cwd=self.root,
            ), video=video)
            self.assertEqual(status["source"], f"file:{key_file.resolve()}")

    def test_direct_json_key_beats_file_and_environment(self):
        key_file = self.write_key(
            self.skill / "scripts" / ".tikhub_api_key", "test-only-key-default-file"
        )
        config_file = self.skill / "config.json"
        config_file.write_text(
            json.dumps({"api_key": "  test-only-key-direct-json  "}), encoding="utf-8"
        )
        with mock.patch.dict(os.environ, {"TIKHUB_API_KEY": "test-only-key-env"}):
            config = self.module.load_config(None)
            key, source = self.module.resolve_api_key(config)
        self.assertEqual(key, "test-only-key-direct-json")
        self.assertEqual(source, "config:api_key")
        self.assertTrue(key_file.is_file())
        for runner, video in ((run_script, False), (run_video_script, True)):
            status = self.assert_configured(
                runner("--check-config", skill=self.skill), video=video
            )
            self.assertEqual(status["source"], "config:api_key")

    def test_key_file_option_overrides_json_and_works_for_both_entrypoints(self):
        (self.skill / "config.json").write_text(
            json.dumps({"api_key": "test-only-key-direct-json"}), encoding="utf-8"
        )
        key_file = self.write_key(
            self.root / "any location" / "chosen.txt", "test-only-key-chosen-file"
        )
        config = self.module.load_config(None, str(key_file))
        self.assertFalse(config.get("api_key"))
        self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-chosen-file")
        for runner, video in ((run_script, False), (run_video_script, True)):
            status = self.assert_configured(runner(
                "--key-file", "any location/chosen.txt", "--check-config",
                skill=self.skill, cwd=self.root,
                environment={"TIKHUB_API_KEY": "test-only-key-env"},
            ), video=video)
            self.assertEqual(status["source"], f"file:{key_file.resolve()}")

    def test_missing_and_empty_files_fall_back_through_legacy_env_and_keychain(self):
        default = self.skill / "scripts" / ".tikhub_api_key"
        legacy = self.write_key(
            self.skill / ".local" / "tikhub-api-key", "test-only-key-legacy"
        )
        config = self.module.load_config(None)
        config["api_key"] = "  "
        with mock.patch.dict(os.environ, {"TIKHUB_API_KEY": "test-only-key-env"}):
            self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-legacy")
            self.write_key(default, "\ufeff \n")
            self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-legacy")
            self.write_key(legacy, " \n")
            self.assertEqual(
                self.module.resolve_api_key(config),
                ("test-only-key-env", "environment:TIKHUB_API_KEY"),
            )
        self.assertEqual(self.module.resolve_api_key(config), ("", "missing"))
        with mock.patch.dict(os.environ, {"TIKHUB_DISABLE_KEYCHAIN": "0"}), mock.patch.object(
            self.module, "read_keychain", return_value="test-only-key-keychain"
        ) as read_keychain:
            self.assertEqual(self.module.resolve_api_key(config)[0], "test-only-key-keychain")
            read_keychain.assert_called_once()

    def test_configure_once_persists_across_processes_without_environment(self):
        result = run_script(
            "--configure-local-key", skill=self.skill,
            stdin_text="test-only-key-configured\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        key_file = self.skill / "scripts" / ".tikhub_api_key"
        self.assertEqual(key_file.read_text(encoding="utf-8").strip(), "test-only-key-configured")
        self.assertNotIn("test-only-key-configured", result.stdout + result.stderr)
        self.assert_configured(run_script("--check-config", skill=self.skill, cwd=self.root))
        self.assert_configured(
            run_video_script("--check-config", skill=self.skill, cwd=self.root), video=True
        )

    def test_configure_replaces_old_json_key_and_preserves_other_settings(self):
        config_file = self.skill / "config.json"
        config_file.write_text(
            json.dumps({
                "api_key": "test-only-key-old-json",
                "api_base": "https://configured-api.example",
                "timeout_seconds": 73,
            }),
            encoding="utf-8",
        )
        result = run_script(
            "--configure-local-key", skill=self.skill,
            stdin_text="test-only-key-new-file\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        saved_config = json.loads(config_file.read_text(encoding="utf-8"))
        self.assertNotIn("api_key", saved_config)
        self.assertEqual(saved_config["api_base"], "https://configured-api.example")
        self.assertEqual(saved_config["timeout_seconds"], 73)
        key_file = self.skill / "scripts" / ".tikhub_api_key"
        self.assertEqual(key_file.read_text(encoding="utf-8").strip(), "test-only-key-new-file")
        for runner, video in ((run_script, False), (run_video_script, True)):
            status = self.assert_configured(
                runner("--check-config", skill=self.skill, cwd=self.root), video=video
            )
            self.assertEqual(status["source"], f"file:{key_file.resolve()}")
            self.assertEqual(status["api_base"], "https://configured-api.example")
        module = load_request_module(self.skill)
        self.assertEqual(
            module.resolve_api_key(module.load_config(None))[0], "test-only-key-new-file"
        )

    def test_configuring_custom_file_preserves_existing_directory_and_file_modes(self):
        key_file = self.write_key(
            self.root / "shared-directory" / "my-key", "test-only-key-old", mode=0o644
        )
        key_file.parent.chmod(0o755)
        result = run_script(
            "--configure-local-key", "--key-file", str(key_file),
            skill=self.skill, stdin_text="test-only-key-replaced\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(key_file.parent.stat().st_mode & 0o777, 0o755)
        self.assertEqual(key_file.stat().st_mode & 0o777, 0o644)
        self.assertEqual(key_file.read_text(encoding="utf-8").strip(), "test-only-key-replaced")
        status = self.assert_configured(run_script(
            "--key-file", str(key_file), "--check-config", skill=self.skill,
        ))
        self.assertEqual(status["source"], f"file:{key_file.resolve()}")

    def test_configure_rejects_empty_input_without_overwriting_existing_key(self):
        key_file = self.write_key(
            self.skill / "scripts" / ".tikhub_api_key", "test-only-key-keep"
        )
        result = run_script(
            "--configure-local-key", skill=self.skill, stdin_text="  \n"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot be empty", result.stderr)
        self.assertEqual(key_file.read_text(encoding="utf-8"), "test-only-key-keep")


if __name__ == "__main__":
    unittest.main()
