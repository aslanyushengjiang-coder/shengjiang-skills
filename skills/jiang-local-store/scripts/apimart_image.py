#!/usr/bin/env python3
"""Generate or edit images through APIMart's asynchronous GPT Image 2 API.

The adapter uses only Python's standard library. Secrets are read from
environment variables or a private local config file and are never printed.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from image2_api import atomic_write_image, image_summary, open_api_request, print_safe_json, prompt_summary, read_image_url, redact_sensitive, validate_download_url, validate_image_bytes


ALLOWED_CONFIG_KEYS = {
    "APIMART_API_KEY",
    "APIMART_BASE_URL",
    "APIMART_IMAGE_MODEL",
    "APIMART_IMAGE_RESOLUTION",
    "APIMART_IMAGE_SIZE",
}

ALLOWED_RATIOS = {
    "auto",
    "1:1",
    "3:2",
    "2:3",
    "4:3",
    "3:4",
    "5:4",
    "4:5",
    "16:9",
    "9:16",
    "2:1",
    "1:2",
    "3:1",
    "1:3",
    "21:9",
    "9:21",
}


def config_candidates() -> list[Path]:
    override = os.getenv("APIMART_CONFIG_FILE")
    if override:
        return [Path(override).expanduser().resolve()]
    return [
        Path.home() / ".config" / "jiang-local-store" / "apimart.env",
    ]


def select_config_path() -> Path:
    for path in config_candidates():
        if path.is_file():
            return path
    return config_candidates()[0]


def load_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise SystemExit(f"APIMart config path is not a file: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SystemExit(
            f"APIMart config permissions are too open ({oct(mode)}): {path}. "
            "Restrict it to the current user with chmod 600."
        )
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise SystemExit(f"Invalid config line {line_number} in {path}")
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if name not in ALLOWED_CONFIG_KEYS:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            values[name] = value
    return values


def setting(config: dict[str, str], name: str, default: str = "") -> str:
    return os.getenv(name, "").strip() or config.get(name, "").strip() or default


def resolve_settings() -> tuple[dict[str, str], Path]:
    path = select_config_path()
    config = load_config(path)
    settings = {
        "api_key": setting(config, "APIMART_API_KEY"),
        "base_url": setting(config, "APIMART_BASE_URL", "https://api.apimart.ai").rstrip("/"),
        "model": setting(config, "APIMART_IMAGE_MODEL", "gpt-image-2"),
        "resolution": setting(config, "APIMART_IMAGE_RESOLUTION", "1k").lower(),
        "size": setting(config, "APIMART_IMAGE_SIZE", "1:1"),
    }
    parsed = urllib.parse.urlparse(settings["base_url"])
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("APIMART_BASE_URL must be a complete HTTPS URL.")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise SystemExit("APIMART_BASE_URL must not contain credentials, a query or a fragment.")
    return settings, path


def looks_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in ("replace-locally", "your-key", "<本机填写>"))


def auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "jiang-local-store/1.0",
    }


def request_json(method: str, url: str, api_key: str, payload: dict | None = None, timeout: float = 120) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=auth_headers(api_key), method=method)
    try:
        with open_api_request(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict):
                raise SystemExit("APIMart returned a JSON value that is not an object.")
            return result
    except urllib.error.HTTPError as exc:
        detail = redact_sensitive(exc.read().decode("utf-8", errors="replace"), api_key)[:1000]
        raise SystemExit(f"APIMart returned HTTP {exc.code}: {detail}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SystemExit("APIMart returned invalid JSON; no image was saved.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        detail = redact_sensitive(str(getattr(exc, "reason", exc)), api_key)
        raise SystemExit(f"APIMart connection failed: {detail}") from exc


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        try:
            prompt = Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SystemExit("Prompt file could not be read as UTF-8.") from exc
    else:
        prompt = args.prompt or ""
    prompt = prompt.strip()
    if not prompt:
        raise SystemExit("Prompt cannot be empty.")
    return prompt


def image_to_data_uri(raw_path: str) -> str:
    if raw_path.startswith("https://"):
        validate_download_url(raw_path)
        return raw_path
    if raw_path.startswith("data:image/"):
        try:
            prefix, encoded = raw_path.split(",", 1)
            if not prefix.endswith(";base64") or len(encoded) >= (20 * 1024 * 1024 + 2) // 3 * 4:
                raise ValueError("invalid data URI")
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise SystemExit("Reference data URI must contain a valid base64 image under 20MB.") from exc
        if len(data) >= 20 * 1024 * 1024:
            raise SystemExit("Reference image must be under 20MB.")
        image_format = validate_image_bytes(data)
        if prefix != f"data:image/{image_format};base64":
            raise SystemExit("Reference data URI MIME type does not match its image bytes.")
        return raw_path
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"Reference image does not exist: {path}")
    if path.stat().st_size >= 20 * 1024 * 1024:
        raise SystemExit(f"Reference image must be under 20MB: {path}")
    data = path.read_bytes()
    mime = "image/" + validate_image_bytes(data)
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def validate_size(value: str) -> None:
    if value in ALLOWED_RATIOS:
        return
    parts = value.lower().split("x")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise SystemExit("Size must be a supported ratio such as 4:5 or a WIDTHxHEIGHT value.")
    if any(int(part) <= 0 for part in parts):
        raise SystemExit("Width and height must be greater than zero.")


def validate_output_name(value: str) -> None:
    """Keep provider-controlled output names inside the requested directory."""
    if value in {".", ".."} or Path(value).name != value:
        raise SystemExit("Name must be a single filename stem without path separators.")
    if not re.fullmatch(r"[\w.-]+", value, flags=re.UNICODE):
        raise SystemExit("Name may contain only letters, numbers, underscore, dot and hyphen.")


def extract_task_id(response: dict, api_key: str = "") -> str:
    if not isinstance(response, dict):
        raise SystemExit("APIMart response must be a JSON object.")
    items = response.get("data")
    if isinstance(items, list) and items and isinstance(items[0], dict):
        task_id = items[0].get("task_id")
        if task_id:
            if not isinstance(task_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
                raise SystemExit("APIMart returned an invalid task ID.")
            return str(task_id)
    detail = redact_sensitive(json.dumps(response, ensure_ascii=False), api_key)[:600]
    raise SystemExit(f"APIMart response has no task_id: {detail}")


def poll_task(base_url: str, api_key: str, task_id: str, timeout: int, interval: int) -> dict:
    if timeout <= 0 or interval <= 0:
        raise SystemExit("Timeout and polling interval must be greater than zero.")
    deadline = time.monotonic() + timeout
    task_url = f"{base_url}/v1/tasks/{task_id}"
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        response = request_json("GET", task_url, api_key, timeout=max(0.001, min(120, remaining)))
        data = response.get("data", {})
        if not isinstance(data, dict):
            raise SystemExit("APIMart task data must be a JSON object.")
        status = data.get("status") if isinstance(data, dict) else None
        if status is not None and not isinstance(status, str):
            raise SystemExit("APIMart task status must be a string.")
        if status == "completed":
            return response
        if status == "failed":
            error = data.get("error") if isinstance(data, dict) else response
            detail = redact_sensitive(json.dumps(error, ensure_ascii=False), api_key)[:1000]
            raise SystemExit(f"APIMart task failed: {detail}")
        if status not in {"pending", "submitted", "processing", None}:
            detail = redact_sensitive(str(status), api_key)
            raise SystemExit(f"Unexpected APIMart task status: {detail}")
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(interval, remaining))
    raise SystemExit(f"Timed out waiting for APIMart task {task_id}")


def extract_urls(task_response: dict, api_key: str = "") -> list[str]:
    if not isinstance(task_response, dict):
        raise SystemExit("APIMart task response must be a JSON object.")
    data = task_response.get("data", {})
    result = data.get("result", {}) if isinstance(data, dict) else {}
    images = result.get("images", []) if isinstance(result, dict) else []
    if not isinstance(images, list):
        raise SystemExit("APIMart task image result must be a list.")
    urls: list[str] = []
    for item in images:
        value = item.get("url") if isinstance(item, dict) else None
        if isinstance(value, str):
            urls.append(value)
        elif isinstance(value, list):
            urls.extend(url for url in value if isinstance(url, str))
    if not urls:
        detail = redact_sensitive(json.dumps(task_response, ensure_ascii=False), api_key)[:600]
        raise SystemExit(f"APIMart task result has no image URL: {detail}")
    return urls


def download(url: str, target: Path, api_key: str = "") -> Path:
    data = read_image_url(url, api_key)
    image_format = validate_image_bytes(data)
    suffix = ".jpg" if image_format == "jpeg" else f".{image_format}"
    return atomic_write_image(target.with_suffix(suffix), data, image_format)


def run_doctor() -> None:
    settings, path = resolve_settings()
    ready = bool(settings["api_key"] and not looks_placeholder(settings["api_key"]))
    print_safe_json(
            {
                "ready": ready,
                "provider": "APIMart",
                "base_url": settings["base_url"],
                "model": settings["model"],
                "resolution": settings["resolution"],
                "size": settings["size"],
                "api_key": "configured" if settings["api_key"] else "missing",
                "config_file": str(path),
                "config_file_exists": path.is_file(),
                "generation_endpoint": f"{settings['base_url']}/v1/images/generations",
            }, settings["api_key"], indent=2,
    )
    if not ready:
        raise SystemExit(2)


def run_generate(args: argparse.Namespace) -> None:
    if args.timeout <= 0 or args.interval <= 0:
        raise SystemExit("Timeout and polling interval must be greater than zero.")
    settings, _ = resolve_settings()
    if not args.dry_run and (not args.output_dir or not args.name):
        raise SystemExit("--output-dir and --name are required unless --dry-run is used.")
    size = args.size or settings["size"]
    resolution = (args.resolution or settings["resolution"]).lower()
    validate_size(size)
    if resolution not in {"1k", "2k", "4k"}:
        raise SystemExit("Resolution must be 1k, 2k or 4k.")
    if args.name:
        validate_output_name(args.name)
    if len(args.reference_image) > 16:
        raise SystemExit("APIMart accepts at most 16 reference images.")
    references = [image_to_data_uri(value) for value in args.reference_image]

    payload: dict[str, object] = {
        "model": args.model or settings["model"],
        "prompt": read_prompt(args),
        "n": 1,
        "size": size,
        "resolution": resolution,
    }
    if references:
        payload["image_urls"] = references

    if args.dry_run:
        summaries = []
        for index, (raw, reference) in enumerate(zip(args.reference_image, references), 1):
            if reference.startswith("https://"):
                summaries.append({"filename": Path(urllib.parse.urlsplit(reference).path).name or f"remote-reference-{index}",
                                  "sha256": None, "width": None, "height": None, "validation": "URL only; remote image was not fetched"})
            else:
                data = base64.b64decode(reference.split(",", 1)[1], validate=True)
                name = f"inline-reference-{index}" if raw.startswith("data:image/") else Path(raw).name
                summaries.append(image_summary(data, name))
        preview = {"dry_run": True, "method": "POST", "url": f"{settings['base_url']}/v1/images/generations",
                   "content_type": "application/json", "parameters": {key: value for key, value in payload.items() if key not in {"prompt", "image_urls"}},
                   "prompt": prompt_summary(str(payload["prompt"])), "references": summaries}
        print_safe_json(preview, settings["api_key"], indent=2)
        return

    if not settings["api_key"] or looks_placeholder(settings["api_key"]):
        raise SystemExit("No APIMart API key configured. Put it in a private config file, not chat.")

    submitted = request_json(
        "POST", f"{settings['base_url']}/v1/images/generations", settings["api_key"], payload
    )
    task_id = extract_task_id(submitted, settings["api_key"])
    if args.submit_only:
        print_safe_json({"provider": "APIMart", "task_id": task_id, "status": "submitted"}, settings["api_key"])
        return

    completed = poll_task(settings["base_url"], settings["api_key"], task_id, args.timeout, args.interval)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[str] = []
    for index, url in enumerate(extract_urls(completed, settings["api_key"]), 1):
        suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            suffix = ".png"
        target = output_dir / f"{args.name}-{index:02d}{suffix}"
        saved = download(url, target, settings["api_key"])
        files.append(str(saved))
    cost = completed.get("data", {}).get("cost") if isinstance(completed.get("data"), dict) else None
    print_safe_json({"provider": "APIMart", "task_id": task_id, "files": files, "reported_cost_usd": cost}, settings["api_key"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Check local configuration without making a paid request")
    generate = subparsers.add_parser("generate", help="Generate or edit one image")
    prompt_group = generate.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    generate.add_argument("--reference-image", action="append", default=[])
    generate.add_argument("--size")
    generate.add_argument("--resolution", choices=("1k", "2k", "4k"))
    generate.add_argument("--model")
    generate.add_argument("--output-dir", help="Image directory; required unless --dry-run is used")
    generate.add_argument("--name", help="Image filename stem; required unless --dry-run is used")
    generate.add_argument("--dry-run", action="store_true", help="Validate and summarize the real request without HTTP, an API key or creating tasks/images")
    generate.add_argument("--timeout", type=int, default=300)
    generate.add_argument("--interval", type=int, default=5)
    generate.add_argument("--submit-only", action="store_true")
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    if parsed.command == "doctor":
        run_doctor()
    else:
        run_generate(parsed)
