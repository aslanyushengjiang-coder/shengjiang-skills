#!/usr/bin/env python3
"""Preview, estimate, and send TikHub requests with persistent Skill configuration."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import platform
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = {
    "api_base": "https://api.tikhub.io",
    "timeout_seconds": 45,
    "api_key_env": "TIKHUB_API_KEY",
    "local_key_file": str(SKILL_ROOT / "scripts" / ".tikhub_api_key"),
    "macos_keychain_service": "tikhub-api",
    "macos_keychain_account": "tikhub",
}

PRICE_TIERS = (
    (1_000, Decimal("0")),
    (5_000, Decimal("0.10")),
    (10_000, Decimal("0.20")),
    (20_000, Decimal("0.30")),
    (30_000, Decimal("0.40")),
    (None, Decimal("0.50")),
)

SENSITIVE_KEYS = {
    "authorization",
    "token",
    "key",
    "api_key",
    "apikey",
    "secret",
    "sign",
    "cache_url",
}


def load_config(path: str | None, key_file: str | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config_path = Path(path).expanduser() if path else SKILL_ROOT / "config.json"
    if path or config_path.is_file():
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("--config must contain a JSON object")
        config.update(payload)
        if payload.get("local_key_file"):
            local_path = Path(str(payload["local_key_file"])).expanduser()
            if not local_path.is_absolute():
                local_path = config_path.resolve().parent / local_path
            config["local_key_file"] = str(local_path)
    if key_file is not None:
        config["local_key_file"] = str(Path(key_file).expanduser().resolve())
        config.pop("api_key", None)
    if config.get("api_key") is not None and not isinstance(config["api_key"], str):
        raise ValueError("api_key must be a string")
    config["api_base"] = os.environ.get(
        "TIKHUB_API_BASE", str(config["api_base"])
    ).rstrip("/")
    return config


def read_keychain(service: str, account: str) -> str:
    if platform.system() != "Darwin":
        return ""
    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                service,
                "-a",
                account,
                "-w",
            ],
            check=False,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def read_local_key(path: str) -> str:
    key_path = Path(path).expanduser()
    try:
        return key_path.read_text(encoding="utf-8-sig").strip()
    except (FileNotFoundError, OSError, UnicodeError):
        return ""


def configure_local_key(path: str) -> Path:
    key_path = Path(path).expanduser()
    value = (
        getpass.getpass("TikHub API key: ")
        if sys.stdin.isatty()
        else sys.stdin.readline()
    ).strip()
    if not value:
        raise ValueError("API key cannot be empty")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(value + "\n", encoding="utf-8")
    return key_path


def resolve_api_key(config: dict[str, Any]) -> tuple[str, str]:
    # 每次调用重新读文件，云电脑切换会话或修改 Key 后无需刷新环境。
    value = (config.get("api_key") or "").strip()
    if value:
        return value, "config:api_key"
    for key_path in (
        Path(str(config["local_key_file"])).expanduser(),
        SKILL_ROOT / ".local" / "tikhub-api-key",
    ):
        value = read_local_key(str(key_path))
        if value:
            return value, f"file:{key_path.resolve()}"
    env_name = str(config["api_key_env"])
    value = os.environ.get(env_name, "").strip()
    if value:
        return value, f"environment:{env_name}"
    if os.environ.get("TIKHUB_DISABLE_KEYCHAIN") == "1":
        return "", "missing"
    value = read_keychain(
        str(config["macos_keychain_service"]),
        str(config["macos_keychain_account"]),
    )
    if value:
        return value, "macOS Keychain"
    return "", "missing"


def parse_json_arg(raw: str | None) -> Any:
    if not raw:
        return None
    if raw.startswith("@"):
        return json.loads(Path(raw[1:]).read_text(encoding="utf-8"))
    return json.loads(raw)


def validate_path(path: str) -> None:
    if not path.startswith("/api/") or path.startswith("//"):
        raise ValueError("--path must begin with exactly one '/api/'")


def build_url(base_url: str, path: str, params: Any) -> str:
    validate_path(path)
    if params is not None and not isinstance(params, dict):
        raise ValueError("--params must be a JSON object")
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    return url


def redact_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    safe_pairs = [
        (key, "***" if key.lower() in SENSITIVE_KEYS else value)
        for key, value in pairs
    ]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urllib.parse.urlencode(safe_pairs),
            "",
        )
    )


def redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("<redacted>" if key.lower() in SENSITIVE_KEYS else redact_payload(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    return value


def estimate_cost(requests: int, unit_price: Decimal) -> dict[str, Any]:
    if requests < 1:
        raise ValueError("--estimate-requests must be a positive integer")
    if unit_price <= 0:
        raise ValueError("--unit-price must be greater than zero")

    remaining = requests
    lower = 0
    total = Decimal("0")
    breakdown = []
    for upper, discount in PRICE_TIERS:
        if remaining <= 0:
            break
        capacity = remaining if upper is None else max(0, upper - lower)
        count = min(remaining, capacity)
        discounted_price = unit_price * (Decimal("1") - discount)
        tier_cost = discounted_price * count
        breakdown.append(
            {
                "requests": count,
                "discount_percent": float(discount * 100),
                "unit_price_usd": float(discounted_price),
                "cost_usd": float(tier_cost),
            }
        )
        total += tier_cost
        remaining -= count
        if upper is not None:
            lower = upper

    return {
        "requests": requests,
        "base_unit_price_usd": float(unit_price),
        "estimated_total_usd": float(total),
        "average_unit_price_usd": float(total / requests),
        "tiers": breakdown,
        "disclaimer": "Estimate only. Verify the endpoint price with TikHub before paid batch requests.",
    }


def price_preview(requests: int, unit_price_raw: str | None) -> dict[str, Any]:
    if unit_price_raw:
        try:
            unit_price = Decimal(unit_price_raw)
        except InvalidOperation as exc:
            raise ValueError("--unit-price must be a valid decimal") from exc
        return {"exact_input": estimate_cost(requests, unit_price)}
    return {
        "typical_range": {
            "low": estimate_cost(requests, Decimal("0.001")),
            "high": estimate_cost(requests, Decimal("0.01")),
        },
        "warning": "Some special endpoints cost more than 0.01 USD/request. Check the selected endpoint.",
    }


def request_json(
    *,
    config: dict[str, Any],
    api_key: str,
    method: str,
    path: str,
    params: Any = None,
    body: Any = None,
    timeout: int | None = None,
) -> Any:
    url = build_url(str(config["api_base"]), path, params)
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "User-Agent": "Shengjiang-Research/1.0",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    request_timeout = int(timeout or config["timeout_seconds"])
    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").replace(
            api_key, "<redacted>"
        )
        print(f"TikHub HTTP {exc.code}: {detail[:1000]}", file=sys.stderr)
        raise SystemExit(1) from exc
    except urllib.error.URLError as exc:
        print(f"TikHub request failed: {exc.reason}", file=sys.stderr)
        raise SystemExit(1) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw_text": raw.decode("utf-8", errors="replace")}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="JSON config; defaults to config.json in the Skill")
    parser.add_argument("--key-file", help="Read or save the API key at any chosen file path")
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument(
        "--configure-local-key",
        action="store_true",
        help="Save the key once in scripts/.tikhub_api_key (or --key-file) for future sessions",
    )
    parser.add_argument("--method", choices=("GET", "POST"), default="GET")
    parser.add_argument("--path", help="Official TikHub API path beginning with /api/")
    parser.add_argument("--params", help="JSON object or @file for query parameters")
    parser.add_argument("--body", help="JSON value or @file for POST body")
    parser.add_argument("--out", help="Output JSON path for a real data request")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--estimate-requests",
        type=int,
        help="Planned successful requests for a cost preview",
    )
    parser.add_argument(
        "--unit-price",
        help="Known endpoint price in USD/request; omit for a 0.001–0.01 range",
    )
    parser.add_argument(
        "--official-price",
        action="store_true",
        help="Call TikHub's official calculate_price endpoint",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config, args.key_file)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid config: {exc}", file=sys.stderr)
        return 2

    if args.configure_local_key:
        try:
            saved_path = configure_local_key(str(config["local_key_file"]))
            # 配置命令写入的新文件应立即接管，不能继续被 JSON 内的旧 Key 覆盖。
            if config.get("api_key"):
                config_path = Path(args.config).expanduser() if args.config else SKILL_ROOT / "config.json"
                payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
                payload.pop("api_key", None)
                config_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        except (OSError, ValueError) as exc:
            print(f"Could not save local API key: {exc}", file=sys.stderr)
            return 2
        print(
            json.dumps(
                {
                    "configured": True,
                    "source": f"file:{saved_path.resolve()}",
                    "saved": str(saved_path.resolve()),
                },
                ensure_ascii=False,
            )
        )
        return 0

    api_key, source = resolve_api_key(config)
    if args.check_config:
        print(
            json.dumps(
                {
                    "configured": bool(api_key),
                    "source": source,
                    "variable": config["api_key_env"],
                    "api_base": config["api_base"],
                },
                ensure_ascii=False,
            )
        )
        return 0

    if not args.path:
        print("--path is required unless --check-config is used", file=sys.stderr)
        return 2

    try:
        validate_path(args.path)
        params = parse_json_arg(args.params)
        body = parse_json_arg(args.body)
        preview = None
        if args.estimate_requests is not None:
            preview = price_preview(args.estimate_requests, args.unit_price)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"Invalid request: {exc}", file=sys.stderr)
        return 2

    if args.official_price:
        if args.estimate_requests is None:
            print("--official-price requires --estimate-requests", file=sys.stderr)
            return 2
        if not api_key:
            print(
                "TikHub API key not found. Run --configure-local-key once to save it "
                "in the Skill, choose --key-file, or use --dry-run for an estimate.",
                file=sys.stderr,
            )
            return 2
        payload = request_json(
            config=config,
            api_key=api_key,
            method="GET",
            path="/api/v1/tikhub/user/calculate_price",
            params={
                "endpoint": args.path,
                "request_per_day": args.estimate_requests,
            },
            timeout=args.timeout,
        )
        print(
            json.dumps(
                {
                    "endpoint": args.path,
                    "request_per_day": args.estimate_requests,
                    "source": "TikHub official calculate_price API",
                    "result": redact_payload(payload),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    try:
        url = build_url(str(config["api_base"]), args.path, params)
    except ValueError as exc:
        print(f"Invalid request: {exc}", file=sys.stderr)
        return 2

    request_preview = {
        "method": args.method,
        "url": redact_url(url),
        "body": redact_payload(body),
        "out": args.out,
        "authorization": "Bearer <configured TikHub API key>",
        "pricing": preview,
    }
    if args.dry_run:
        print(json.dumps(request_preview, ensure_ascii=False, indent=2))
        return 0

    if not api_key:
        print(
            "TikHub API key not found. This skill uses a third-party paid API. "
            "Run --configure-local-key once to save it in the Skill, choose "
            "--key-file, or use --dry-run.",
            file=sys.stderr,
        )
        return 2
    if not args.out:
        print("--out is required for a real data request", file=sys.stderr)
        return 2

    payload = request_json(
        config=config,
        api_key=api_key,
        method=args.method,
        path=args.path,
        params=params,
        body=body,
        timeout=args.timeout,
    )
    output_path = Path(args.out).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "saved": str(output_path.resolve()),
                "code": payload.get("code") if isinstance(payload, dict) else None,
                "message": payload.get("message") if isinstance(payload, dict) else "",
                "pricing_preview": preview,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
