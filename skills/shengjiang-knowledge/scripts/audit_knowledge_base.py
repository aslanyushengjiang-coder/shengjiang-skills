#!/usr/bin/env python3
"""Read-only health check for folder-based AI knowledge bases."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".codex-tmp",
    ".quartz",
    ".wrangler",
    ".trash",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

DEPENDENCY_OR_CACHE_DIRS = {
    "node_modules",
    "__pycache__",
    ".cache",
    ".pytest_cache",
    "dist",
    "build",
}

CORE_FILES = {
    "AGENT.md",
    "AGENTS.md",
    "CLAUDE.md",
    "INDEX.md",
    "_本周.md",
}

REQUIRED_P0 = {
    "AGENTS.md": "缺少 Codex 项目入口。",
    "INDEX.md": "缺少知识库导航。",
    "system/SOUL.md": "缺少 AI 协作风格。",
    "system/USER.md": "缺少用户和业务背景。",
    "system/PROCEDURES.md": "缺少程序性规则。",
}

RECOMMENDED_P1 = {
    "AGENT.md": "缺少跨 Agent 的镜像入口。",
    "CLAUDE.md": "缺少 Claude Code 入口。",
    "_本周.md": "缺少当前工作文件。",
    "01.资料库/_资料索引.md": "缺少可追溯的资料接入索引。",
    "system/HEALTH.md": "缺少知识库健康检查频率和状态处理规则。",
    "system/log.md": "缺少知识库变更日志。",
    "system/MEMORY_LOG.md": "缺少用户纠正记录。",
    "system/state/README.md": "缺少巡检状态目录。",
}

SENSITIVE_EXACT = {
    ".env",
    "credentials.json",
    "credential.json",
    "cookies.json",
    "cookie.json",
    "secrets.json",
    "secret.json",
    "passwords.json",
    "password.json",
    "all_keys.json",
    "id_rsa",
    "id_ed25519",
}

SENSITIVE_PREFIXES = (".env.", "cookies.", "secrets.", "credentials.")
VERSION_WORDS = re.compile(r"最终版|最新版|\bfinal\b|\blatest\b", re.IGNORECASE)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str
    recommendation: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only AI knowledge-base audit")
    parser.add_argument("--root", required=True, help="Knowledge-base root path")
    parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown"
    )
    parser.add_argument(
        "--inbox-days", type=int, default=30, help="Age threshold for inbox reminders"
    )
    parser.add_argument(
        "--current-days", type=int, default=14, help="Age threshold for current-work reminders"
    )
    parser.add_argument(
        "--save-state",
        action="store_true",
        help=(
            "Save the Markdown report and latest-health.json under system/state. "
            "Without this flag the command remains read-only."
        ),
    )
    return parser.parse_args()


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def add(
    findings: list[Finding],
    severity: str,
    code: str,
    path: str,
    message: str,
    recommendation: str,
) -> None:
    findings.append(Finding(severity, code, path, message, recommendation))


def collect_files(root: Path, findings: list[Finding]) -> list[Path]:
    files: list[Path] = []
    generated_directories: list[str] = []
    nested_repositories: list[str] = []
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        kept: list[str] = []
        for dirname in dirnames:
            child = current_path / dirname
            if dirname == ".git":
                if child != root / ".git":
                    nested_repositories.append(rel(child, root))
                continue
            if dirname in IGNORED_DIRS:
                if dirname in DEPENDENCY_OR_CACHE_DIRS:
                    generated_directories.append(rel(child, root))
                continue
            kept.append(dirname)
        dirnames[:] = kept
        for filename in filenames:
            files.append(current_path / filename)
    if generated_directories:
        preview = ", ".join(sorted(generated_directories)[:8])
        add(
            findings,
            "P1",
            "GENERATED_DIRECTORIES",
            ".",
            f"发现 {len(generated_directories)} 个依赖、缓存或构建目录。示例：{preview}。",
            "先确认哪些路径属于活跃代码项目，只排除或清理不应长期保留的生成目录。",
        )
    if nested_repositories:
        preview = ", ".join(sorted(nested_repositories)[:8])
        add(
            findings,
            "P1",
            "NESTED_GIT_REPOSITORIES",
            ".",
            f"发现 {len(nested_repositories)} 个嵌套 Git 仓库。示例：{preview}。",
            "只保留有明确用途且已经记录边界的嵌套项目。",
        )
    return files


def check_required(root: Path, files: list[Path], findings: list[Finding]) -> None:
    for relative, message in REQUIRED_P0.items():
        if not (root / relative).exists():
            add(
                findings,
                "P0",
                "MISSING_CORE_FILE",
                relative,
                message,
                "创建或恢复该文件，再重新验证启动链路。",
            )
    for relative, message in RECOMMENDED_P1.items():
        exists = (root / relative).exists()
        if relative == "_本周.md" and any(path.name == "_本周.md" for path in files):
            exists = True
        if relative == "system/state/README.md" and (root / "system/state").is_dir():
            exists = True
        if not exists:
            add(
                findings,
                "P1",
                "MISSING_RECOMMENDED_FILE",
                relative,
                message,
                "仅在这套知识库确实需要该能力时补充。",
            )


def check_entry_consistency(root: Path, findings: list[Finding]) -> None:
    agent = root / "AGENT.md"
    agents = root / "AGENTS.md"
    if agent.is_file() and agents.is_file():
        if agent.read_bytes() != agents.read_bytes():
            add(
                findings,
                "P0",
                "ENTRY_MIRROR_MISMATCH",
                "AGENT.md / AGENTS.md",
                "镜像入口内容不一致，不同 Agent 可能加载到不同规则。",
                "确定一个主入口，同步镜像后再次比较。",
            )

    claude = root / "CLAUDE.md"
    if claude.is_file():
        text = claude.read_text(encoding="utf-8", errors="replace")
        if "@AGENT.md" not in text and "@AGENTS.md" not in text and "system/SOUL.md" not in text:
            add(
                findings,
                "P1",
                "CLAUDE_ENTRY_NOT_CONNECTED",
                "CLAUDE.md",
                "Claude Code 入口没有明显导入主入口，也没有等价启动链路。",
                "使用薄导入，或补充等价的启动规则。",
            )


def inline_path_candidate(value: str) -> bool:
    value = value.strip()
    if not value or value.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if any(token in value for token in ("<", ">", "{", "}", "*", "|", "$", " -- ")):
        return False
    if " / " in value or " → " in value or any(character.isspace() for character in value):
        return False
    return value.endswith(".md") or "/" in value


def normalize_target(raw: str) -> str:
    target = raw.strip().strip("<>")
    target = target.split("#", 1)[0]
    return target.rstrip("/")


def check_reference(
    source: Path, raw: str, root: Path, findings: list[Finding], strict: bool
) -> None:
    target = normalize_target(raw)
    if not target or target.startswith(("http://", "https://", "mailto:", "#")):
        return
    first_part = Path(target).parts[0] if Path(target).parts else ""
    if first_part in IGNORED_DIRS:
        return
    candidate = Path(target).expanduser()
    resolved = candidate if candidate.is_absolute() else source.parent / candidate
    resolved = resolved.resolve(strict=False)
    if not strict and len(candidate.parts) == 1 and not resolved.exists():
        return
    if not resolved.exists():
        add(
            findings,
            "P0",
            "BROKEN_REFERENCE",
            f"{rel(source, root)} -> {target}",
            "入口或导航引用的本地路径不存在。",
            "修改链接前，先确认目标是否被移动、改名，或者只是模板示例。",
        )


def markdown_scan_candidates(root: Path, files: list[Path]) -> list[Path]:
    candidates: set[Path] = set()
    for name in CORE_FILES:
        path = root / name
        if path.is_file():
            candidates.add(path)
    for path in files:
        if path.suffix.lower() != ".md":
            continue
        relative = path.relative_to(root)
        if len(relative.parts) <= 3 and (
            path.name == "README.md" or path.name == "00.agent.md"
        ):
            candidates.add(path)
    return sorted(candidates)


def check_markdown_references(
    root: Path, files: list[Path], findings: list[Finding]
) -> None:
    seen: set[tuple[str, str]] = set()
    for source in markdown_scan_candidates(root, files):
        text = source.read_text(encoding="utf-8", errors="replace")
        linked_values = list(MARKDOWN_LINK.findall(text))
        inline_values: list[str] = []
        if source.name in CORE_FILES:
            inline_values = [
                value for value in INLINE_CODE.findall(text) if inline_path_candidate(value)
            ]
        for value, strict in [
            *((value, True) for value in linked_values),
            *((value, False) for value in inline_values),
        ]:
            key = (str(source), value)
            if key in seen:
                continue
            seen.add(key)
            check_reference(source, value, root, findings, strict)


def check_navigation_coverage(root: Path, findings: list[Finding]) -> None:
    index = root / "INDEX.md"
    if not index.is_file():
        return
    text = index.read_text(encoding="utf-8", errors="replace")
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name in IGNORED_DIRS:
            continue
        if child.name not in text:
            add(
                findings,
                "P1",
                "UNINDEXED_TOP_DIRECTORY",
                child.name,
                "这个顶层目录没有出现在 INDEX.md 中。",
                "把目录职责写进导航，或说明为什么有意排除。",
            )


def is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith((".example", ".sample", ".template")):
        return False
    if name in SENSITIVE_EXACT:
        return True
    return any(name.startswith(prefix) for prefix in SENSITIVE_PREFIXES)


def check_sensitive(files: list[Path], root: Path, findings: list[Finding]) -> None:
    for path in files:
        if is_sensitive(path):
            add(
                findings,
                "P0",
                "SENSITIVE_FILE",
                rel(path, root),
                "知识库中出现了疑似凭证、Cookie、密钥或密码文件。",
                "不要输出内容。将其移到合适的密钥存储位置，并从同步和版本控制中排除。",
            )


def check_version_conflicts(files: list[Path], root: Path, findings: list[Finding]) -> None:
    by_topic: dict[tuple[Path, str], list[Path]] = defaultdict(list)
    for path in files:
        if VERSION_WORDS.search(path.stem):
            topic = VERSION_WORDS.sub("", path.stem.lower())
            topic = re.sub(r"[-_.\s]+", "-", topic).strip("-")
            if topic:
                by_topic[(path.parent, topic)].append(path)
    for (directory, _topic), matches in sorted(by_topic.items(), key=lambda item: str(item[0])):
        if len(matches) < 2:
            continue
        names = ", ".join(sorted(path.name for path in matches)[:8])
        add(
            findings,
            "P0",
            "VERSION_CONFLICT",
            rel(directory, root) or ".",
            f"同一主题存在多个最终版或最新版：{names}。",
            "读取局部索引或状态说明；没有规则时询问用户当前使用哪个版本。",
        )


def check_staleness(
    files: list[Path], root: Path, findings: list[Finding], inbox_days: int, current_days: int
) -> None:
    now = time.time()
    inbox = root / "00.收件箱"
    if inbox.is_dir():
        stale = [
            path
            for path in files
            if inbox in path.parents and now - path.stat().st_mtime > inbox_days * 86400
        ]
        if stale:
            add(
                findings,
                "P1",
                "STALE_INBOX",
                rel(inbox, root),
                f"有 {len(stale)} 个收件箱文件超过 {inbox_days} 天未处理。",
                "确认归属和目标位置，不自动删除。",
            )

    current = root / "_本周.md"
    if current.is_file() and now - current.stat().st_mtime > current_days * 86400:
        add(
            findings,
            "P1",
            "STALE_CURRENT_WORK",
            "_本周.md",
            f"当前工作文件已经超过 {current_days} 天没有更新。",
            "确认它是否仍然代表用户当前的真实优先级。",
        )


def check_root_clutter(root: Path, findings: list[Finding]) -> None:
    allowed = CORE_FILES | {"README.md", "LICENSE", "VERSION", "CHANGELOG.md"}
    loose = [
        child.name
        for child in root.iterdir()
        if child.is_file() and child.name not in allowed and not child.name.startswith(".")
    ]
    if len(loose) > 8:
        add(
            findings,
            "P1",
            "ROOT_FILE_CLUTTER",
            ".",
            f"根目录散落了 {len(loose)} 个非入口文件。",
            "职责明确时再归类；无法判断的文件经确认后先进入收件箱。",
        )


def check_duplicate_names(files: list[Path], root: Path, findings: list[Finding]) -> None:
    counts = Counter(
        path.name
        for path in files
        if path.suffix.lower() == ".md"
        and len(path.stem) >= 10
        and not path.name.startswith((".", "00-", "00_"))
        and path.name
        not in {
            "README.md",
            "AGENT.md",
            "AGENTS.md",
            "CLAUDE.md",
            "INDEX.md",
            "SKILL.md",
            "MEMORY_LOG.md",
            "PROCEDURES.md",
        }
    )
    crowded = sorted((name, count) for name, count in counts.items() if count >= 4)
    for name, count in crowded[:20]:
        add(
            findings,
            "P1",
            "REPEATED_FILENAME",
            name,
            f"同名文件出现在 {count} 个位置，检索时可能无法区分。",
            "目录上下文足够清楚时保持现状；否则补日期、来源或局部索引。",
        )


def summary(findings: list[Finding]) -> dict[str, int]:
    counts = Counter(finding.severity for finding in findings)
    return {"P0": counts["P0"], "P1": counts["P1"], "P2": counts["P2"]}


def health_status(findings: list[Finding]) -> str:
    counts = summary(findings)
    if counts["P0"]:
        return "critical"
    if counts["P1"]:
        return "attention"
    return "healthy"


def render_markdown(root: Path, findings: list[Finding]) -> str:
    counts = summary(findings)
    if counts["P0"]:
        conclusion = "当前存在会让 Agent 读错或泄露敏感信息的风险，先处理 P0。"
    elif counts["P1"]:
        conclusion = "知识库可以使用，但有维护风险，建议按 P1 逐项确认。"
    else:
        conclusion = "未发现确定性的入口、断链、版本或敏感文件风险。"

    lines = [
        "# 知识库自检",
        "",
        f"- 根目录：`{root}`",
        f"- 结论：{conclusion}",
        f"- 统计：P0 {counts['P0']} / P1 {counts['P1']} / P2 {counts['P2']}",
    ]
    labels = {"P0": "立即处理（P0）", "P1": "建议处理（P1）", "P2": "保持现状（P2）"}
    for severity in ("P0", "P1", "P2"):
        group = [finding for finding in findings if finding.severity == severity]
        if not group:
            continue
        lines.extend(["", f"## {labels[severity]}", ""])
        for finding in group:
            lines.append(
                f"- `{finding.path}` [{finding.code}]：{finding.message} 建议：{finding.recommendation}"
            )
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "本报告由只读脚本生成。模板示例、合法归档和嵌套代码项目可能产生误报；修复前继续读取相关入口和原始文件确认。",
        ]
    )
    return "\n".join(lines) + "\n"


def make_payload(root: Path, findings: list[Finding]) -> dict[str, object]:
    return {
        "root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": health_status(findings),
        "summary": summary(findings),
        "findings": [asdict(finding) for finding in findings],
    }


def save_state(root: Path, payload: dict[str, object], markdown: str) -> tuple[Path, Path]:
    state_dir = root / "system" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    report_path = state_dir / f"{datetime.now().astimezone().date().isoformat()}-知识库健康检查.md"
    latest_path = state_dir / "latest-health.json"
    report_path.write_text(markdown, encoding="utf-8")
    latest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_path, latest_path


def main() -> int:
    args = parse_args()
    root = Path(args.root).expanduser().resolve(strict=False)
    if not root.is_dir():
        print(f"ERROR: knowledge-base root does not exist: {root}", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    files = collect_files(root, findings)
    check_required(root, files, findings)
    check_entry_consistency(root, findings)
    check_markdown_references(root, files, findings)
    check_navigation_coverage(root, findings)
    check_sensitive(files, root, findings)
    check_version_conflicts(files, root, findings)
    check_staleness(files, root, findings, args.inbox_days, args.current_days)
    check_root_clutter(root, findings)
    check_duplicate_names(files, root, findings)

    findings = sorted(findings, key=lambda item: (item.severity, item.code, item.path))
    payload = make_payload(root, findings)
    markdown = render_markdown(root, findings)

    if args.save_state:
        report_path, latest_path = save_state(root, payload, markdown)
        print(f"Saved health report: {report_path}", file=sys.stderr)
        print(f"Saved latest state: {latest_path}", file=sys.stderr)

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(markdown, end="")

    counts = summary(findings)
    if counts["P0"]:
        return 2
    if counts["P1"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
