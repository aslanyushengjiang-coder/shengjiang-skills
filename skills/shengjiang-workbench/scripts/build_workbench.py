#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = SKILL_ROOT / "assets" / "runtime"
SUPPORTED_TYPES = {
    "tasks",
    "calendar",
    "inbox",
    "habits",
    "projects",
    "journal",
    "knowledge",
    "content",
    "meetings",
    "metrics",
    "health",
    "finance",
    "home",
    "custom",
}


PRESETS: dict[str, dict[str, Any]] = {
    "personal": {
        "name": "我的日常工作台",
        "owner": "本地用户",
        "persona": "DAILY LIFE WORKBENCH",
        "primary_goal": "把今天要做的事、日程、习惯和生活记录放进一个轻量系统",
        "accent": "#2f6b57",
        "modules": [
            {
                "id": "today",
                "title": "今日",
                "type": "tasks",
                "group": "今天",
                "description": "只放今天真正要推进的下一步",
            },
            {
                "id": "calendar",
                "title": "日历",
                "type": "calendar",
                "group": "今天",
                "description": "查看预约、截止日和本周节奏",
            },
            {
                "id": "inbox",
                "title": "收集箱",
                "type": "inbox",
                "group": "日常",
                "description": "先接住想法、截图、链接和提醒，再决定是否变成计划",
            },
            {
                "id": "habits",
                "title": "习惯",
                "type": "habits",
                "group": "日常",
                "description": "记录今天是否完成，不制造额外压力",
            },
            {
                "id": "goals",
                "title": "目标与项目",
                "type": "projects",
                "group": "长期",
                "description": "把长期目标拆成当前项目和明确下一步",
            },
            {
                "id": "journal",
                "title": "记录与复盘",
                "type": "journal",
                "group": "长期",
                "description": "留下心情、发生的事和可复用的经验",
            },
        ],
        "starter_items": {
            "today": [
                {
                    "title": "确认今天最重要的一件事",
                    "status": "doing",
                    "note": "只写一个可以立刻开始的动作",
                },
                {
                    "title": "处理一条收集箱内容",
                    "status": "todo",
                    "note": "决定：删除、保存，还是变成行动",
                },
            ],
            "calendar": [
                {
                    "title": "本周回顾",
                    "status": "scheduled",
                    "note": "回看完成、调整和暂停的事情",
                }
            ],
            "inbox": [
                {
                    "title": "把脑子里惦记的一件事先记下来",
                    "status": "new",
                    "note": "先收集，不要求它立刻变成任务",
                }
            ],
            "habits": [
                {
                    "title": "活动身体 20 分钟",
                    "status": "active",
                    "note": "散步、拉伸或运动都算",
                    "completion_dates": [],
                },
                {
                    "title": "睡前离开屏幕 30 分钟",
                    "status": "active",
                    "note": "根据自己的作息调整",
                    "completion_dates": [],
                },
            ],
            "goals": [
                {
                    "title": "写下这个月真正想推进的一个目标",
                    "status": "planned",
                    "note": "补充一个本周就能完成的下一步",
                }
            ],
            "journal": [
                {
                    "title": "今天发生了什么？",
                    "status": "draft",
                    "note": "记录一件事、一个感受和一个明天想调整的地方",
                }
            ],
        },
    },
    "creator": {
        "name": "我的内容工作台",
        "owner": "内容创作者",
        "persona": "自媒体创作",
        "primary_goal": "把调研、选题、脚本、发布和复盘放进一个系统",
        "accent": "#cc5d36",
        "modules": [
            {"id": "today", "title": "今日", "type": "tasks", "description": "今天最重要的内容任务"},
            {"id": "inbox", "title": "收集箱", "type": "inbox", "description": "灵感、链接和待整理资料"},
            {"id": "topics", "title": "选题与内容", "type": "content", "description": "从想法流转到发布"},
            {"id": "benchmarks", "title": "对标调研", "type": "knowledge", "description": "保存对标与可复用结论"},
            {"id": "metrics", "title": "数据复盘", "type": "metrics", "description": "记录真实数据和下一步实验"},
        ],
    },
    "study": {
        "name": "雅思工作台",
        "owner": "个人学习系统",
        "persona": "IELTS STUDY WORKBENCH",
        "primary_goal": "把每日学习、阅读、错题和复习放进同一个系统",
        "accent": "#2f6b57",
        "modules": [
            {
                "id": "today",
                "title": "今日",
                "type": "tasks",
                "group": "今天",
                "description": "今天最重要的学习任务和完成进度",
            },
            {
                "id": "vocabulary",
                "title": "单词本",
                "type": "knowledge",
                "group": "核心学习",
                "description": "单词记忆、掌握状态和间隔复习",
            },
            {
                "id": "reading",
                "title": "每日阅读",
                "type": "knowledge",
                "group": "核心学习",
                "description": "阅读材料、中文翻译、重点词汇和理解记录",
            },
            {
                "id": "mistakes",
                "title": "错题本",
                "type": "knowledge",
                "group": "核心学习",
                "description": "错题原因、薄弱知识点和定期复习",
            },
            {
                "id": "practice",
                "title": "习题练习",
                "type": "tasks",
                "group": "核心学习",
                "description": "练习计划、正确率和自动回收错题",
            },
            {
                "id": "listening-speaking",
                "title": "听力口语",
                "type": "knowledge",
                "group": "更多",
                "description": "听力素材、跟读和口语练习记录",
            },
            {
                "id": "grammar",
                "title": "语法笔记",
                "type": "knowledge",
                "group": "更多",
                "description": "语法知识点与简明解释",
            },
            {
                "id": "inbox",
                "title": "收集箱",
                "type": "inbox",
                "group": "更多",
                "description": "承接零散资料并建议归入对应模块",
            },
        ],
        "starter_items": {
            "today": [
                {
                    "title": "完成一篇每日阅读",
                    "status": "doing",
                    "note": "阅读文章、查看重点词汇并写一句摘要",
                },
                {
                    "title": "复习 20 个薄弱单词",
                    "status": "todo",
                    "note": "优先复习“似会不会”的词",
                },
                {
                    "title": "复盘 3 道主谓一致错题",
                    "status": "done",
                    "note": "完成后更新错题本状态",
                },
            ],
            "vocabulary": [
                {
                    "title": "resilient",
                    "status": "new",
                    "note": "adj. 有韧性的；能迅速恢复的",
                },
                {
                    "title": "decline",
                    "status": "reviewed",
                    "note": "n./v. 下降；衰退",
                },
            ],
            "reading": [
                {
                    "title": "Urban Bee Decline",
                    "status": "new",
                    "note": "城市蜜蜂数量下降主题阅读；重点词：habitat、pollinators。",
                },
                {
                    "title": "Remote Work Trends",
                    "status": "reviewed",
                    "note": "分析远程办公趋势并记录三个高频表达。",
                },
            ],
            "mistakes": [
                {
                    "title": "He, along with his friends, ___ going to the cinema tonight.",
                    "status": "new",
                    "note": "你的答案：are；正确答案：is。along with 不改变主语单复数。",
                },
                {
                    "title": "The number of students ___ increasing.",
                    "status": "new",
                    "note": "你的答案：are；正确答案：is。the number of 作主语时谓语用单数。",
                },
            ],
            "practice": [
                {
                    "title": "主谓一致专项练习",
                    "status": "doing",
                    "note": "目标 10 题；答错后记录到错题本",
                }
            ],
            "inbox": [
                {
                    "title": "一篇关于城市生态的英文文章",
                    "status": "new",
                    "note": "建议归入：每日阅读",
                }
            ],
        },
    },
    "product": {
        "name": "我的产品工作台",
        "owner": "产品经理",
        "persona": "产品与项目",
        "primary_goal": "让需求、项目、会议和用户反馈保持在同一条链路",
        "accent": "#7657a8",
        "modules": [
            {"id": "today", "title": "今日", "type": "tasks", "description": "当前优先事项"},
            {"id": "inbox", "title": "收集箱", "type": "inbox", "description": "临时需求和反馈"},
            {"id": "projects", "title": "项目", "type": "projects", "description": "目标、进度和下一步"},
            {"id": "requirements", "title": "需求池", "type": "projects", "description": "需求价值、阶段和决策"},
            {"id": "meetings", "title": "会议", "type": "meetings", "description": "决议和行动项"},
            {"id": "metrics", "title": "数据复盘", "type": "metrics", "description": "指标、结论和实验"},
        ],
    },
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "personal-workbench"


def load_profile(profile_path: Path | None, preset: str | None) -> dict[str, Any]:
    if profile_path:
        try:
            payload = json.loads(profile_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ValueError(f"需求画像不存在：{profile_path}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"需求画像不是有效 JSON：{exc}")
        if not isinstance(payload, dict):
            raise ValueError("需求画像顶层必须是 JSON 对象")
        return payload
    if preset:
        return json.loads(json.dumps(PRESETS[preset], ensure_ascii=False))
    raise ValueError("必须提供 --profile 或 --preset")


def validate_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    name = profile.get("name")
    modules = profile.get("modules")
    if not isinstance(name, str) or not name.strip():
        errors.append("name 必须是非空字符串")
    if not isinstance(modules, list) or not 3 <= len(modules) <= 10:
        errors.append("modules 必须包含 3–10 个模块")
        return errors
    seen: set[str] = set()
    for index, module in enumerate(modules, start=1):
        if not isinstance(module, dict):
            errors.append(f"第 {index} 个模块必须是对象")
            continue
        module_id = module.get("id")
        title = module.get("title")
        module_type = module.get("type", "custom")
        if not isinstance(module_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", module_id):
            errors.append(f"第 {index} 个模块 id 只能使用小写字母、数字和连字符")
        elif module_id in seen:
            errors.append(f"模块 id 重复：{module_id}")
        else:
            seen.add(module_id)
        if not isinstance(title, str) or not title.strip():
            errors.append(f"第 {index} 个模块缺少 title")
        if module_type not in SUPPORTED_TYPES:
            errors.append(f"模块 {module_id or index} 的类型不支持：{module_type}")
    accent = profile.get("accent", "#2f6b57")
    if not isinstance(accent, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        errors.append("accent 必须是六位十六进制颜色，例如 #2f6b57")
    starter = profile.get("starter_items", {})
    if not isinstance(starter, dict):
        errors.append("starter_items 必须是对象")
    elif any(key not in seen for key in starter):
        errors.append("starter_items 只能引用已声明的模块 id")
    return errors


def normalized_config(profile: dict[str, Any]) -> dict[str, Any]:
    config = {
        "version": 1,
        "id": slugify(str(profile.get("id") or profile["name"])),
        "name": profile["name"].strip(),
        "owner": str(profile.get("owner") or "本地用户").strip(),
        "persona": str(profile.get("persona") or "个人工作台").strip(),
        "primary_goal": str(profile.get("primary_goal") or "把重要工作放进一个清晰的系统").strip(),
        "accent": profile.get("accent", "#2f6b57"),
        "modules": [],
        "starter_items": profile.get("starter_items", {}),
    }
    for module in profile["modules"]:
        config["modules"].append(
            {
                "id": module["id"],
                "title": module["title"].strip(),
                "type": module.get("type", "custom"),
                "group": str(module.get("group") or "工作台").strip(),
                "description": str(module.get("description") or "").strip(),
            }
        )
    return config


def guide_text(config: dict[str, Any]) -> str:
    return f"""# {config['name']}使用说明

## 打开

双击 `index.html`，或把它拖进浏览器。

## 数据保存

当前版本的数据保存在当前浏览器的本地存储中。刷新页面不会丢失，但清理浏览器数据、换浏览器或换设备不会自动同步。

请定期进入“设置与数据”，点击“导出备份”。需要恢复时使用“导入备份”。

## 当前模块

{chr(10).join(f"- {module['title']}：{module['description']}" for module in config['modules'])}

## 暂未包含

- 云同步；
- 账号登录；
- 多人协作；
- 真实 AI API。

增加这些能力时需要后端或第三方服务。API Key 禁止写入网页文件。
"""


def build(config: dict[str, Any], output: Path, apply: bool) -> int:
    files = ["index.html", "styles.css", "app.js", "config.js", "workbench.json", "使用说明.md"]
    print(f"Mode: {'APPLY' if apply else 'PREVIEW'}")
    print(f"Workbench: {config['name']}")
    print(f"Output: {output}")
    print("Modules: " + "、".join(module["title"] for module in config["modules"]))
    print("Files: " + "、".join(files))
    if not apply:
        print("No files were written. Re-run with --apply to generate.")
        return 0
    if output.exists() and any(output.iterdir()):
        print(f"ERROR: 输出目录不是空目录，拒绝覆盖：{output}", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)
    for runtime_file in ("index.html", "styles.css", "app.js"):
        shutil.copy2(RUNTIME_ROOT / runtime_file, output / runtime_file)
    serialized = json.dumps(config, ensure_ascii=False, indent=2)
    (output / "workbench.json").write_text(serialized + "\n", encoding="utf-8")
    (output / "config.js").write_text(
        "window.WORKBENCH_CONFIG = " + serialized + ";\n",
        encoding="utf-8",
    )
    (output / "使用说明.md").write_text(guide_text(config), encoding="utf-8")
    print("Generated successfully.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成本地优先的个人 AI 工作台")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--profile", type=Path, help="需求画像 JSON")
    source.add_argument("--preset", choices=sorted(PRESETS), help="内置场景")
    parser.add_argument("--output", type=Path, required=True, help="输出目录")
    parser.add_argument("--apply", action="store_true", help="真正写入；默认只预览")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        profile = load_profile(args.profile, args.preset)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    errors = validate_profile(profile)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    output = args.output.expanduser().resolve()
    return build(normalized_config(profile), output, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
