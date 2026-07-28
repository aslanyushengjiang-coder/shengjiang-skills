#!/usr/bin/env python3
"""Read-only inventory for material sources before knowledge-base intake."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
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
    "id_rsa",
    "id_ed25519",
}

SENSITIVE_PREFIXES = (".env.", "cookies.", "secrets.", "credentials.")

KIND_BY_SUFFIX = {
    ".md": "text",
    ".txt": "text",
    ".rtf": "text",
    ".html": "web",
    ".htm": "web",
    ".pdf": "document",
    ".doc": "document",
    ".docx": "document",
    ".ppt": "document",
    ".pptx": "document",
    ".xls": "data",
    ".xlsx": "data",
    ".csv": "data",
    ".tsv": "data",
    ".json": "data",
    ".yaml": "data",
    ".yml": "data",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".webp": "image",
    ".heic": "image",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".aac": "audio",
    ".flac": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".mkv": "video",
    ".webm": "video",
    ".zip": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".7z": "archive",
}


@dataclass(frozen=True)
class Material:
    path: str
    kind: str
    suffix: str
    size_bytes: int
    modified_at: str
    blocked_sensitive: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only inventory of files before knowledge-base intake."
    )
    parser.add_argument("--source", required=True, help="Material file or folder")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def safe_source(raw_source: str) -> Path:
    source = Path(raw_source).expanduser().resolve(strict=False)
    home = Path.home().resolve()
    if source in {Path("/"), home} or source.parent == Path("/"):
        raise ValueError(
            f"Refusing broad source: {source}. Choose a dedicated file or folder."
        )
    if not source.exists():
        raise ValueError(f"Source does not exist: {source}")
    return source


def is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith((".example", ".sample", ".template")):
        return False
    if name in SENSITIVE_EXACT:
        return True
    return any(name.startswith(prefix) for prefix in SENSITIVE_PREFIXES)


def classify(path: Path) -> str:
    return KIND_BY_SUFFIX.get(path.suffix.lower(), "other")


def iter_files(source: Path) -> list[Path]:
    if source.is_file():
        return [source]
    files: list[Path] = []
    for current, dirnames, filenames in os.walk(source):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIRS and not dirname.startswith(".")
        ]
        current_path = Path(current)
        for filename in filenames:
            if filename == ".DS_Store":
                continue
            files.append(current_path / filename)
    return sorted(files)


def build_material(path: Path, source: Path) -> Material:
    stat = path.stat()
    relative = path.name if source.is_file() else path.relative_to(source).as_posix()
    return Material(
        path=relative,
        kind=classify(path),
        suffix=path.suffix.lower(),
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        blocked_sensitive=is_sensitive(path),
    )


def make_payload(source: Path, materials: list[Material]) -> dict[str, object]:
    return {
        "source": str(source),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(materials),
        "total_bytes": sum(material.size_bytes for material in materials),
        "blocked_sensitive_count": sum(
            material.blocked_sensitive for material in materials
        ),
        "materials": [asdict(material) for material in materials],
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# 待接入资料清单",
        "",
        f"- 来源：`{payload['source']}`",
        f"- 文件数：{payload['file_count']}",
        f"- 总大小：{payload['total_bytes']} bytes",
        f"- 疑似敏感文件：{payload['blocked_sensitive_count']}（只登记路径，不读取内容）",
        "",
        "| 相对路径 | 类型 | 大小 | 状态 |",
        "| --- | --- | ---: | --- |",
    ]
    for item in payload["materials"]:
        state = "禁止读取" if item["blocked_sensitive"] else "待 Agent 读取并判断"
        lines.append(
            f"| `{item['path']}` | {item['kind']} | {item['size_bytes']} | {state} |"
        )
    lines.extend(
        [
            "",
            "下一步：让 Agent 读取非敏感文件，按来源、所有权、主题、事实类型和下一步用途生成接入预览；本脚本不会复制、移动或修改任何文件。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        source = safe_source(args.source)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    materials = [build_material(path, source) for path in iter_files(source)]
    payload = make_payload(source, materials)
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
