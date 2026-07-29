import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "shengjiang-research"
SCRIPT = SKILL / "scripts" / "tikhub_request.py"


def run_script(*args):
    env = os.environ.copy()
    env.pop("TIKHUB_API_KEY", None)
    env.pop("TIKHUB_API_BASE", None)
    env["TIKHUB_DISABLE_KEYCHAIN"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


class ShengjiangResearchSkillTests(unittest.TestCase):
    def test_public_package_contains_no_local_paths_or_secret_assignments(self):
        texts = []
        for path in SKILL.rglob("*"):
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
        self.assertNotIn("api_key\": \"", combined)

    def test_skill_is_api_first_and_discloses_cost(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: shengjiang-research", content)
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
            "scripts/tikhub_request.py",
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
        self.assertIn("never paste it into chat", result.stderr)

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
        self.assertGreaterEqual(len(payload["evals"]), 6)
        prompts = "\n".join(item["prompt"] for item in payload["evals"])
        self.assertIn("大概花多少钱", prompts)
        self.assertIn("没有 TikHub Key", prompts)
        self.assertIn("社媒 Excel", prompts)
        self.assertIn("逐字稿", prompts)
        self.assertIn("代理销售", prompts)


if __name__ == "__main__":
    unittest.main()
