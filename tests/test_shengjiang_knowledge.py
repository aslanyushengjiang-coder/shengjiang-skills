from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "shengjiang-knowledge"
INIT_SCRIPT = SKILL_ROOT / "scripts" / "init_knowledge_base.py"
AUDIT_SCRIPT = SKILL_ROOT / "scripts" / "audit_knowledge_base.py"
SCAN_SCRIPT = SKILL_ROOT / "scripts" / "scan_materials.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        check=False,
        text=True,
        capture_output=True,
    )


class ShengjiangKnowledgeTests(unittest.TestCase):
    def test_skill_package_is_complete(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: shengjiang-knowledge\n"))
        self.assertLessEqual(len(skill_text.splitlines()), 500)
        self.assertIn("references/architecture.md", skill_text)
        self.assertIn("references/audit-rules.md", skill_text)
        self.assertIn("references/material-intake.md", skill_text)
        self.assertIn("references/health-cycle.md", skill_text)
        self.assertTrue((SKILL_ROOT / "references" / "architecture.md").is_file())
        self.assertTrue((SKILL_ROOT / "references" / "audit-rules.md").is_file())
        self.assertTrue((SKILL_ROOT / "references" / "material-intake.md").is_file())
        self.assertTrue((SKILL_ROOT / "references" / "health-cycle.md").is_file())
        self.assertTrue(SCAN_SCRIPT.is_file())

        evals = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(evals["skill_name"], "shengjiang-knowledge")
        self.assertEqual(len(evals["evals"]), 6)
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
            self.assertTrue((root / "system" / "HEALTH.md").is_file())
            self.assertTrue((root / "01.资料库" / "_资料索引.md").is_file())
            self.assertTrue((root / "03.项目档案" / "README.md").is_file())
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
            self.assertEqual(payload["status"], "healthy")

    def test_creator_profile_builds_content_workbench(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "creator-knowledge-base"
            apply_result = run(
                str(INIT_SCRIPT),
                "--root",
                str(root),
                "--name",
                "自媒体知识库",
                "--profile",
                "creator",
                "--apply",
            )
            self.assertEqual(apply_result.returncode, 0, apply_result.stderr)
            self.assertIn("Profile: creator", apply_result.stdout)
            expected_files = [
                "01.资料库/01.账号定位/README.md",
                "01.资料库/02.对标调研/_调研索引.md",
                "01.资料库/03.用户洞察/_用户洞察索引.md",
                "01.资料库/04.素材库/_素材索引.md",
                "02.输出区/01.选题池/_选题索引.md",
                "02.输出区/02.草稿/README.md",
                "02.输出区/03.审核/README.md",
                "02.输出区/04.定稿/README.md",
                "02.输出区/05.待发布/README.md",
                "02.输出区/06.已发布与复盘/_发布复盘索引.md",
            ]
            for relative in expected_files:
                self.assertTrue((root / relative).is_file(), relative)

            audit_result = run(
                str(AUDIT_SCRIPT), "--root", str(root), "--format", "json"
            )
            self.assertEqual(audit_result.returncode, 0, audit_result.stdout)
            payload = json.loads(audit_result.stdout)
            self.assertEqual(payload["status"], "healthy")

    def test_health_check_can_save_latest_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "knowledge-base"
            apply_result = run(
                str(INIT_SCRIPT), "--root", str(root), "--name", "测试知识库", "--apply"
            )
            self.assertEqual(apply_result.returncode, 0, apply_result.stderr)
            audit_result = run(
                str(AUDIT_SCRIPT),
                "--root",
                str(root),
                "--format",
                "json",
                "--save-state",
            )
            self.assertEqual(audit_result.returncode, 0, audit_result.stdout)
            latest = root / "system" / "state" / "latest-health.json"
            self.assertTrue(latest.is_file())
            payload = json.loads(latest.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "healthy")
            dated_reports = list(
                (root / "system" / "state").glob("*-知识库健康检查.md")
            )
            self.assertEqual(len(dated_reports), 1)

    def test_material_scan_is_read_only_and_blocks_sensitive_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "materials"
            source.mkdir()
            (source / "访谈.md").write_text("真实访谈内容\n", encoding="utf-8")
            (source / "数据.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (source / ".env").write_text("TOKEN=test-only\n", encoding="utf-8")
            before = sorted(path.relative_to(source) for path in source.rglob("*"))
            result = run(
                str(SCAN_SCRIPT), "--source", str(source), "--format", "json"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["file_count"], 3)
            self.assertEqual(payload["blocked_sensitive_count"], 1)
            kinds = {item["path"]: item["kind"] for item in payload["materials"]}
            self.assertEqual(kinds["访谈.md"], "text")
            self.assertEqual(kinds["数据.csv"], "data")
            blocked = {
                item["path"]
                for item in payload["materials"]
                if item["blocked_sensitive"]
            }
            self.assertEqual(blocked, {".env"})
            after = sorted(path.relative_to(source) for path in source.rglob("*"))
            self.assertEqual(before, after)

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
