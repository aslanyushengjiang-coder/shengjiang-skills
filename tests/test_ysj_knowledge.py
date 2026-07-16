from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ysj-knowledge"
INIT_SCRIPT = SKILL_ROOT / "scripts" / "init_knowledge_base.py"
AUDIT_SCRIPT = SKILL_ROOT / "scripts" / "audit_knowledge_base.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        check=False,
        text=True,
        capture_output=True,
    )


class YsjKnowledgeTests(unittest.TestCase):
    def test_skill_package_is_complete(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: ysj-knowledge\n"))
        self.assertIn("\nlicense: MIT\n---\n", skill_text)
        self.assertLessEqual(len(skill_text.splitlines()), 500)
        self.assertIn("references/architecture.md", skill_text)
        self.assertIn("references/audit-rules.md", skill_text)
        self.assertTrue((SKILL_ROOT / "references" / "architecture.md").is_file())
        self.assertTrue((SKILL_ROOT / "references" / "audit-rules.md").is_file())

        evals = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(evals["skill_name"], "ysj-knowledge")
        self.assertEqual(len(evals["evals"]), 3)
        self.assertTrue(all(item["assertions"] for item in evals["evals"]))

    def test_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge-base"
            result = run(str(INIT_SCRIPT), "--root", str(root), "--name", "测试知识库")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PREVIEW", result.stdout)
            self.assertFalse(root.exists())

    def test_apply_creates_mirrored_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge-base"
            result = run(
                str(INIT_SCRIPT),
                "--root",
                str(root),
                "--name",
                "测试知识库",
                "--apply",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((root / "INDEX.md").is_file())
            self.assertTrue((root / "system" / "USER.md").is_file())
            self.assertEqual(
                (root / "AGENT.md").read_bytes(),
                (root / "AGENTS.md").read_bytes(),
            )

    def test_fresh_template_has_no_p0_or_p1(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge-base"
            apply_result = run(
                str(INIT_SCRIPT), "--root", str(root), "--name", "测试知识库", "--apply"
            )
            self.assertEqual(apply_result.returncode, 0, apply_result.stderr)
            audit_result = run(
                str(AUDIT_SCRIPT), "--root", str(root), "--format", "json"
            )
            self.assertEqual(audit_result.returncode, 0, audit_result.stdout)
            payload = json.loads(audit_result.stdout)
            self.assertEqual(payload["summary"]["P0"], 0)
            self.assertEqual(payload["summary"]["P1"], 0)

    def test_broken_base_detects_core_risks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge-base"
            apply_result = run(
                str(INIT_SCRIPT), "--root", str(root), "--name", "测试知识库", "--apply"
            )
            self.assertEqual(apply_result.returncode, 0, apply_result.stderr)

            (root / "AGENTS.md").write_text("# conflicting entry\n", encoding="utf-8")
            with (root / "INDEX.md").open("a", encoding="utf-8") as handle:
                handle.write("\n- `不存在/事实源.md`\n")
            (root / ".env").write_text("DO_NOT_READ=this-is-a-test\n", encoding="utf-8")
            versions = root / "01.资料库" / "版本测试"
            versions.mkdir(parents=True)
            (versions / "方案-final.md").write_text("old\n", encoding="utf-8")
            (versions / "方案-latest.md").write_text("new\n", encoding="utf-8")

            audit_result = run(
                str(AUDIT_SCRIPT), "--root", str(root), "--format", "json"
            )
            self.assertEqual(audit_result.returncode, 2, audit_result.stdout)
            payload = json.loads(audit_result.stdout)
            codes = {finding["code"] for finding in payload["findings"]}
            self.assertIn("ENTRY_MIRROR_MISMATCH", codes)
            self.assertIn("BROKEN_REFERENCE", codes)
            self.assertIn("SENSITIVE_FILE", codes)
            self.assertIn("VERSION_CONFLICT", codes)


if __name__ == "__main__":
    unittest.main()
