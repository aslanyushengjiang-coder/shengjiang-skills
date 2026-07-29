#!/usr/bin/env python3
"""Send one portable TikHub API request without exposing credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def json_value(raw: str | None) -> Any:
    if raw is None:
        return None
    if raw.startswith("@"):
        return json.loads(Path(raw[1:]).read_text(encoding="utf-8"))
    return json.loads(raw)


def build_url(base_url: str, path: str, params: Any) -> str:
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("--path must start with one '/'")
    url = base_url.rstrip("/") + path
    if params is not None:
        if not isinstance(params, dict):
            raise ValueError("--params must be a JSON object")
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    return url


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    sensitive = {"token", "key", "api_key", "apikey", "secret", "authorization"}
    safe_pairs = [
        (key, "***" if key.lower() in sensitive else value) for key, value in pairs
    ]
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(safe_pairs), "")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("GET", "POST"), default="GET")
    parser.add_argument("--path", required=True, help="Official TikHub API path")
    parser.add_argument("--params", help="JSON object or @file for query parameters")
    parser.add_argument("--body", help="JSON value or @file for POST body")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--base-url", default="https://api.tikhub.io")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        params = json_value(args.params)
        body = json_value(args.body)
        url = build_url(args.base_url, args.path, params)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid request: {exc}", file=sys.stderr)
        return 2

    preview = {
        "method": args.method,
        "url": redact_url(url),
        "body": body,
        "out": str(Path(args.out)),
        "authorization": "Bearer <TIKHUB_API_KEY from environment>",
    }
    if args.dry_run:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("TIKHUB_API_KEY")
    if not api_key:
        print(
            "TIKHUB_API_KEY is not set. Use --dry-run or choose the free manual route.",
            file=sys.stderr,
        )
        return 2

    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=args.method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "shengjiang-social-media-research/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        print(f"TikHub HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"TikHub request failed: {exc.reason}", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {"raw_text": raw.decode("utf-8", errors="replace")}

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Saved response to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

