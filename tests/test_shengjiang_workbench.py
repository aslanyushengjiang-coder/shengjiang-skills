from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "shengjiang-workbench"
BUILD_SCRIPT = SKILL_ROOT / "scripts" / "build_workbench.py"
AUDIT_SCRIPT = SKILL_ROOT / "scripts" / "audit_workbench.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )


class ShengjiangWorkbenchTests(unittest.TestCase):
    def test_public_package_is_complete_and_portable(self) -> None:
        expected = [
            "SKILL.md",
            "agents/openai.yaml",
            "assets/profile.example.json",
            "assets/runtime/index.html",
            "assets/runtime/styles.css",
            "assets/runtime/app.js",
            "references/intake.md",
            "references/module-catalog.md",
            "references/quality-bar.md",
            "references/upgrade-path.md",
            "scripts/build_workbench.py",
            "scripts/audit_workbench.py",
            "evals/evals.json",
        ]
        for relative in expected:
            self.assertTrue((SKILL_ROOT / relative).is_file(), relative)
        texts = []
        for path in SKILL_ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".py", ".js", ".json", ".yaml", ".html", ".css"}:
                texts.append(path.read_text(encoding="utf-8"))
        self.assertNotIn("/Users/", "\n".join(texts))

    def test_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "preview"
            result = run(BUILD_SCRIPT, "--preset", "creator", "--output", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PREVIEW", result.stdout)
            self.assertFalse(output.exists())

    def test_creator_preset_builds_healthy_workbench(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "creator"
            result = run(
                BUILD_SCRIPT,
                "--preset",
                "creator",
                "--output",
                str(output),
                "--apply",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in (
                "index.html",
                "styles.css",
                "app.js",
                "config.js",
                "workbench.json",
                "使用说明.md",
            ):
                self.assertTrue((output / name).is_file(), name)
            config = json.loads((output / "workbench.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [module["id"] for module in config["modules"]],
                ["today", "inbox", "topics", "benchmarks", "metrics"],
            )
            audit = run(AUDIT_SCRIPT, "--root", str(output), "--format", "json")
            self.assertEqual(audit.returncode, 0, audit.stdout)
            payload = json.loads(audit.stdout)
            self.assertEqual(payload["status"], "healthy")
            self.assertEqual(payload["summary"]["P0"], 0)

    def test_custom_profile_and_runtime_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = root / "profile.json"
            output = root / "workbench"
            profile.write_text(
                json.dumps(
                    {
                        "name": "销售工作台",
                        "owner": "测试用户",
                        "persona": "销售",
                        "primary_goal": "跟进客户和行动",
                        "accent": "#336699",
                        "modules": [
                            {"id": "today", "title": "今日", "type": "tasks"},
                            {"id": "inbox", "title": "收集箱", "type": "inbox"},
                            {"id": "leads", "title": "客户线索", "type": "projects"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = run(
                BUILD_SCRIPT,
                "--profile",
                str(profile),
                "--output",
                str(output),
                "--apply",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            app = (output / "app.js").read_text(encoding="utf-8")
            self.assertIn("localStorage", app)
            self.assertIn("exportData", app)
            self.assertIn("importData", app)
            self.assertIn("globalSearch", (output / "index.html").read_text(encoding="utf-8"))

    def test_invalid_or_overwriting_build_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            invalid = root / "invalid.json"
            invalid.write_text(
                json.dumps(
                    {
                        "name": "坏配置",
                        "modules": [
                            {"id": "same", "title": "一", "type": "tasks"},
                            {"id": "same", "title": "二", "type": "tasks"},
                            {"id": "third", "title": "三", "type": "unknown"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            invalid_result = run(
                BUILD_SCRIPT,
                "--profile",
                str(invalid),
                "--output",
                str(root / "bad"),
                "--apply",
            )
            self.assertEqual(invalid_result.returncode, 2)
            self.assertIn("重复", invalid_result.stderr)
            self.assertIn("不支持", invalid_result.stderr)

            occupied = root / "occupied"
            occupied.mkdir()
            (occupied / "user-file.txt").write_text("keep", encoding="utf-8")
            occupied_result = run(
                BUILD_SCRIPT,
                "--preset",
                "personal",
                "--output",
                str(occupied),
                "--apply",
            )
            self.assertEqual(occupied_result.returncode, 2)
            self.assertEqual((occupied / "user-file.txt").read_text(encoding="utf-8"), "keep")

    def test_audit_detects_secret_and_duplicate_module(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "workbench"
            build = run(
                BUILD_SCRIPT,
                "--preset",
                "study",
                "--output",
                str(output),
                "--apply",
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            config_path = output / "workbench.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["modules"][1]["id"] = config["modules"][0]["id"]
            config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
            with (output / "app.js").open("a", encoding="utf-8") as handle:
                handle.write("\nconst api_key = '1234567890abcdef';\n")
            audit = run(AUDIT_SCRIPT, "--root", str(output), "--format", "json")
            self.assertEqual(audit.returncode, 2)
            payload = json.loads(audit.stdout)
            codes = {item["code"] for item in payload["findings"]}
            self.assertIn("DUPLICATE_MODULE_ID", codes)
            self.assertIn("GENERIC_SECRET", codes)

    def test_evals_cover_generation_iteration_and_upgrade_boundaries(self) -> None:
        payload = json.loads(
            (SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8")
        )
        self.assertEqual(payload["skill_name"], "shengjiang-workbench")
        prompts = "\n".join(item["prompt"] for item in payload["evals"])
        self.assertIn("不知道自己需要哪些模块", prompts)
        self.assertIn("手机电脑数据同步", prompts)
        self.assertIn("空壳", prompts)


if __name__ == "__main__":
    unittest.main()
