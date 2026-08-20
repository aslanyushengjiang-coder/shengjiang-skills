import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "jiang-resume-screening": ["不自动联系", "原文证据", "待确认"],
    "jiang-recruiting-report": ["不修改原始", "数据来源", "异常差额"],
    "jiang-payroll-analysis": ["不自动发薪", "敏感信息", "公式错误"],
}


class HrSkillsPackageTests(unittest.TestCase):
    def test_skill_packages_are_complete(self) -> None:
        for name, required_terms in SKILLS.items():
            skill_root = ROOT / "skills" / name
            skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(skill_text.startswith(f"---\nname: {name}\n"), name)
            self.assertLessEqual(len(skill_text.splitlines()), 220, name)
            for term in required_terms:
                self.assertIn(term, skill_text, f"{name}: {term}")

            eval_path = skill_root / "evals" / "evals.json"
            payload = json.loads(eval_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["skill_name"], name)
            self.assertGreaterEqual(len(payload["evals"]), 3)
            self.assertTrue(all(item["assertions"] for item in payload["evals"]))

    def test_public_packages_do_not_expose_local_project_paths(self) -> None:
        forbidden = ["/Users/", "13.团队共享知识库", "03-幕后校验", "右侧独立任务"]
        for name in SKILLS:
            for path in (ROOT / "skills" / name).rglob("*"):
                if path.is_file():
                    content = path.read_text(encoding="utf-8")
                    for term in forbidden:
                        self.assertNotIn(term, content, f"{path}: {term}")

    def test_readme_lists_all_hr_skills(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for name in SKILLS:
            self.assertIn(f"skills/{name}/", readme)


if __name__ == "__main__":
    unittest.main()
