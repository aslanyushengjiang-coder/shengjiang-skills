import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "jiang-hr"
REFERENCES = {
    "resume-screening.md": ["第一轮评分", "原文证据", "横向对比"],
    "recruiting-report.md": ["数据来源", "异常差额", "渠道A"],
    "payroll-analysis.md": ["不补写", "异常清单", "公式错误"],
}


class JiangHrPackageTests(unittest.TestCase):
    def test_package_routes_three_hr_modes(self) -> None:
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\nname: jiang-hr\n"))
        self.assertLessEqual(len(skill_text.splitlines()), 120)
        for filename in REFERENCES:
            self.assertIn(f"references/{filename}", skill_text)
            self.assertTrue((SKILL / "references" / filename).is_file())

    def test_references_keep_operational_boundaries(self) -> None:
        for filename, required_terms in REFERENCES.items():
            content = (SKILL / "references" / filename).read_text(encoding="utf-8")
            for term in required_terms:
                self.assertIn(term, content, f"{filename}: {term}")

    def test_evals_cover_all_modes(self) -> None:
        payload = json.loads((SKILL / "evals" / "evals.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["skill_name"], "jiang-hr")
        self.assertEqual({item["mode"] for item in payload["evals"]}, {
            "resume-screening",
            "recruiting-report",
            "payroll-analysis",
        })
        self.assertGreaterEqual(len(payload["evals"]), 6)
        self.assertTrue(all(item["assertions"] for item in payload["evals"]))

    def test_public_package_contains_no_internal_paths(self) -> None:
        forbidden = ["/Users/", "13.团队共享知识库", "03-幕后校验", "右侧独立任务"]
        for path in SKILL.rglob("*"):
            if path.is_file():
                content = path.read_text(encoding="utf-8")
                for term in forbidden:
                    self.assertNotIn(term, content, f"{path}: {term}")

    def test_readme_has_one_install_entry(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("skills/jiang-hr/", readme)
        self.assertIn("在 WorkBuddy 对话框中发送", readme)
        self.assertIn(
            "https://github.com/aslanyushengjiang-coder/shengjiang-skills/tree/main/skills/jiang-hr",
            readme,
        )
        self.assertNotIn("--skill jiang-hr", readme)


if __name__ == "__main__":
    unittest.main()
