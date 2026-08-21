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

    def test_recruiting_report_defaults_to_word_with_embedded_charts(self) -> None:
        content = (SKILL / "references" / "recruiting-report.md").read_text(encoding="utf-8")
        for term in ["Word 招聘进度周报", "总招聘漏斗", "岗位招聘漏斗", "渠道招聘漏斗", "高清 PNG", "招聘优化建议"]:
            self.assertIn(term, content)

    def test_recruiting_report_can_reuse_approved_excel_results(self) -> None:
        content = (SKILL / "references" / "recruiting-report.md").read_text(encoding="utf-8")
        for term in ["已有 Excel 结果复用模式", "唯一获批结果源", "不重算公式", "不重新汇总台账", "不展示文件扫描"]:
            self.assertIn(term, content)

    def test_payroll_defaults_to_one_clean_excel_summary(self) -> None:
        content = (SKILL / "references" / "payroll-analysis.md").read_text(encoding="utf-8")
        for term in ["薪酬核算.xlsx", "薪酬汇总", "不在文件名前加序号", "不追加“虚拟演示”", "不额外生成 Word"]:
            self.assertIn(term, content)

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
            "https://github.com/aslanyushengjiang-coder/shengjiang-skills/tree/codex/hr-workbuddy-skills/skills/jiang-hr",
            readme,
        )
        self.assertNotIn("--skill jiang-hr", readme)


if __name__ == "__main__":
    unittest.main()
