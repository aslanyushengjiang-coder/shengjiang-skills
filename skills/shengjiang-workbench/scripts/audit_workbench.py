#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


REQUIRED_FILES = {
    "index.html",
    "styles.css",
    "app.js",
    "config.js",
    "workbench.json",
    "使用说明.md",
}
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
SECRET_PATTERNS = {
    "OPENAI_KEY": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GENERIC_SECRET": re.compile(
        r"""(?ix)
        (api[_-]?key|access[_-]?token|client[_-]?secret|password)
        \s*[:=]\s*
        ["']?[A-Za-z0-9_./+=-]{12,}
        """
    ),
}


def finding(severity: str, code: str, message: str, path: str = "") -> dict[str, str]:
    return {"severity": severity, "code": code, "message": message, "path": path}


def audit(root: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for name in sorted(REQUIRED_FILES):
        if not (root / name).is_file():
            findings.append(finding("P0", "MISSING_FILE", f"缺少核心文件：{name}", name))

    config_path = root / "workbench.json"
    config: dict[str, Any] | None = None
    if config_path.is_file():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                config = payload
            else:
                findings.append(finding("P0", "INVALID_CONFIG", "workbench.json 顶层必须是对象", "workbench.json"))
        except json.JSONDecodeError as exc:
            findings.append(finding("P0", "INVALID_CONFIG", f"workbench.json 无法解析：{exc}", "workbench.json"))

    if config is not None:
        modules = config.get("modules")
        if not isinstance(modules, list) or not modules:
            findings.append(finding("P0", "NO_MODULES", "配置中没有有效模块", "workbench.json"))
        else:
            seen: set[str] = set()
            for module in modules:
                if not isinstance(module, dict):
                    findings.append(finding("P0", "INVALID_MODULE", "模块必须是对象", "workbench.json"))
                    continue
                module_id = str(module.get("id") or "")
                module_type = str(module.get("type") or "")
                if module_id in seen:
                    findings.append(finding("P0", "DUPLICATE_MODULE_ID", f"模块 ID 重复：{module_id}", "workbench.json"))
                seen.add(module_id)
                if module_type not in SUPPORTED_TYPES:
                    findings.append(finding("P0", "UNSUPPORTED_MODULE", f"不支持的模块类型：{module_type}", "workbench.json"))

    index_path = root / "index.html"
    if index_path.is_file():
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
        for reference in ("./styles.css", "./config.js", "./app.js"):
            if reference not in index_text:
                findings.append(finding("P0", "BROKEN_ENTRY", f"index.html 未加载 {reference}", "index.html"))

    config_js = root / "config.js"
    if config_js.is_file() and "window.WORKBENCH_CONFIG" not in config_js.read_text(
        encoding="utf-8", errors="replace"
    ):
        findings.append(finding("P0", "BROKEN_CONFIG_JS", "config.js 未设置 WORKBENCH_CONFIG", "config.js"))

    for path in root.rglob("*"):
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        if path.suffix.lower() not in {".js", ".json", ".html", ".css", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for code, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(
                    finding("P0", code, "发现疑似密钥或密码，禁止把凭证保存在前端工作台", str(path.relative_to(root)))
                )

    if not (root / "使用说明.md").is_file():
        findings.append(finding("P1", "MISSING_GUIDE", "缺少数据保存和备份说明", "使用说明.md"))

    summary = {"P0": 0, "P1": 0, "P2": 0}
    for item in findings:
        summary[item["severity"]] += 1
    return {
        "root": str(root),
        "status": "healthy" if summary["P0"] == 0 else "unhealthy",
        "summary": summary,
        "findings": findings,
        "note": "结构检查不替代浏览器交互验证。",
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Status: {payload['status']}",
        f"Root: {payload['root']}",
        f"P0={payload['summary']['P0']} P1={payload['summary']['P1']} P2={payload['summary']['P2']}",
    ]
    for item in payload["findings"]:
        lines.append(f"[{item['severity']}] {item['code']}: {item['message']} ({item['path']})")
    lines.append(payload["note"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="只读检查生姜个人 AI 工作台")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: 工作台目录不存在：{root}", file=sys.stderr)
        return 2
    payload = audit(root)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(payload))
    return 0 if payload["status"] == "healthy" else 2


if __name__ == "__main__":
    raise SystemExit(main())
