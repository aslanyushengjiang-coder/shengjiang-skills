#!/usr/bin/env python3
"""Preview or create the shengjiang-knowledge minimal folder structure."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or create a minimal local AI knowledge base."
    )
    parser.add_argument("--root", required=True, help="Knowledge-base root path")
    parser.add_argument("--name", help="Human-readable knowledge-base name")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create missing files. Without this flag the command is read-only.",
    )
    return parser.parse_args()


def safe_root(raw_root: str) -> Path:
    root = Path(raw_root).expanduser().resolve(strict=False)
    home = Path.home().resolve()
    if root == Path("/") or root == home or root.parent == Path("/"):
        raise ValueError(
            f"Refusing broad root: {root}. Choose a dedicated project folder."
        )
    return root


def render(text: str, name: str) -> str:
    return (
        text.replace("{{KNOWLEDGE_BASE_NAME}}", name)
        .replace("{{CURRENT_DATE}}", date.today().isoformat())
    )


def main() -> int:
    args = parse_args()
    try:
        root = safe_root(args.root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    template_root = Path(__file__).resolve().parent.parent / "assets" / "minimal-template"
    if not template_root.is_dir():
        print(f"ERROR: template directory not found: {template_root}", file=sys.stderr)
        return 2

    name = args.name or root.name
    template_files = sorted(path for path in template_root.rglob("*") if path.is_file())
    plan: list[tuple[str, Path]] = []

    for source in template_files:
        relative = source.relative_to(template_root)
        destination = root / relative
        action = "skip" if destination.exists() else "create"
        plan.append((action, relative))

    mode = "APPLY" if args.apply else "PREVIEW"
    print(f"{mode}: {root}")
    print(f"Knowledge base: {name}")
    for action, relative in plan:
        print(f"{action:>6}  {relative}")

    if not args.apply:
        print("No files changed. Re-run with --apply after confirmation.")
        return 0

    created = 0
    skipped = 0
    for action, relative in plan:
        destination = root / relative
        if action == "skip":
            skipped += 1
            continue
        source = template_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(render(source.read_text(encoding="utf-8"), name), encoding="utf-8")
        created += 1

    print(f"Created {created} files; skipped {skipped} existing files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
