import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "shengjiang-research"
SCRIPT = SKILL / "scripts" / "tikhub_request.py"


class SocialMediaResearchSkillTests(unittest.TestCase):
    def test_public_package_contains_no_local_paths_or_secret_assignments(self):
        texts = []
        for path in SKILL.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py", ".json", ".yaml"}:
                texts.append(path.read_text(encoding="utf-8"))
        combined = "\n".join(texts)
        self.assertNotIn("/Users/", combined)
        self.assertNotIn("sk-", combined)
        self.assertNotIn("Bearer eyJ", combined)

    def test_skill_name_and_two_routes(self):
        content = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: shengjiang-research", content)
        self.assertIn("第三方 TikHub API", content)
        self.assertIn("社媒助手", content)
        self.assertIn("不自带社媒数据源", content)

    def test_dry_run_does_not_require_or_reveal_key(self):
        env = os.environ.copy()
        env.pop("TIKHUB_API_KEY", None)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--path",
                "/example",
                "--params",
                '{"keyword":"AI"}',
                "--out",
                "unused.json",
                "--dry-run",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["method"], "GET")
        self.assertIn("Bearer <TIKHUB_API_KEY from environment>", preview["authorization"])
        self.assertNotIn("unused.json", result.stderr)

    def test_request_without_key_fails_safely(self):
        env = os.environ.copy()
        env.pop("TIKHUB_API_KEY", None)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--path",
                "/example",
                "--out",
                "unused.json",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("free manual route", result.stderr)

    def test_evals_cover_paid_free_file_and_disclosure(self):
        payload = json.loads(
            (SKILL / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["skill_name"], "shengjiang-research")
        self.assertGreaterEqual(len(payload["evals"]), 4)


if __name__ == "__main__":
    unittest.main()
