#!/usr/bin/env python3
"""Call GPT Image 2 through an OpenAI-compatible official or relay API.

Configuration is read from environment variables or a private local config
file. Secrets and custom authentication headers are never printed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import os
import re
import stat
import struct
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from pathlib import Path


CONFIG_KEYS = {
    "IMAGE2_API_KEY",
    "IMAGE2_BASE_URL",
    "IMAGE2_MODEL",
    "IMAGE2_PROVIDER_NAME",
    "IMAGE2_AUTH_HEADER",
    "IMAGE2_AUTH_PREFIX",
    "IMAGE2_EXTRA_HEADERS_JSON",
    "IMAGE2_GENERATIONS_PATH",
    "IMAGE2_EDITS_PATH",
    "IMAGE2_MODELS_PATH",
    "IMAGE2_IMAGE_FIELD",
    "IMAGE2_MASK_FIELD",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_IMAGE_MODEL",
}

MAX_IMAGE_BYTES = 64 * 1024 * 1024
MAX_DECODED_IMAGE_BYTES = 256 * 1024 * 1024


def redact_sensitive(value: str, *secrets: str) -> str:
    """Redact the actual configured secret, not only one vendor's key prefix."""
    for secret in secrets:
        if secret:
            for representation in {secret, json.dumps(secret)[1:-1], urllib.parse.quote(secret, safe="")}:
                value = value.replace(representation, "***")
    value = re.sub(r"\bsk-[A-Za-z0-9_*.-]{6,}\b", "sk-***", value)
    return re.sub(r"(?i)Bearer\s+[A-Za-z0-9._*+-]{6,}", "Bearer ***", value)


def print_safe_json(value: object, *secrets: str, indent: int | None = None) -> None:
    print(redact_sensitive(json.dumps(value, ensure_ascii=False, indent=indent), *secrets))


def validate_download_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise SystemExit("Image download URL must be a complete HTTP(S) URL.")
    if parsed.username is not None or parsed.password is not None:
        raise SystemExit("Image download URL must not contain embedded credentials.")


class SafeImageRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_download_url(newurl)
        if urllib.parse.urlsplit(req.full_url).scheme == "https" and urllib.parse.urlsplit(newurl).scheme != "https":
            raise SystemExit("Image download redirect must not downgrade HTTPS.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RejectApiRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward API credentials or replay paid request bodies on redirects."""

    def http_error_302(self, req, fp, code, msg, headers):
        fp.close()
        raise SystemExit(
            "Authenticated API redirect rejected; verify the configured endpoint. "
            "No redirected request was sent."
        )

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def open_api_request(request: urllib.request.Request, timeout: float):
    """Use a private no-redirect opener, separate from unauthenticated downloads."""
    return urllib.request.build_opener(RejectApiRedirectHandler()).open(request, timeout=timeout)


def _validate_png(data: bytes) -> None:
    """Validate PNG framing, CRCs and the entire bounded pixel/filter stream."""
    offset, header, idat, ended, palette, seen_idat = 8, None, bytearray(), False, False, False
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError("truncated PNG chunk")
        length, kind = struct.unpack_from("!I4s", data, offset)
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated PNG payload")
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack_from("!I", data, offset + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != crc:
            raise ValueError("PNG checksum mismatch")
        if header is None and kind != b"IHDR":
            raise ValueError("PNG must begin with IHDR")
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise ValueError("invalid PNG header")
            header = struct.unpack("!IIBBBBB", payload)
        elif kind == b"PLTE":
            if seen_idat or not length or length % 3 or length > 768:
                raise ValueError("invalid PNG palette")
            palette = True
        elif kind == b"IDAT":
            seen_idat = True
            idat.extend(payload)
        elif kind == b"IEND":
            if length or end != len(data):
                raise ValueError("invalid PNG end")
            ended = True
            break
        elif kind[0] & 0x20 == 0:
            raise ValueError("unsupported critical PNG chunk")
        offset = end
    if not header or not ended or not idat:
        raise ValueError("incomplete PNG")
    width, height, depth, color, compression, filtering, interlace = header
    depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if not width or not height or color not in depths or depth not in depths[color] or compression or filtering or interlace not in {0, 1}:
        raise ValueError("invalid PNG pixel header")
    if color == 3 and not palette:
        raise ValueError("indexed PNG has no palette")
    passes = [(0, 0, 1, 1)] if not interlace else [(0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
    rows = []
    expected = 0
    for x, y, dx, dy in passes:
        pw, ph = max(0, (width - x + dx - 1) // dx), max(0, (height - y + dy - 1) // dy)
        if pw and ph:
            row_size = (pw * channels[color] * depth + 7) // 8 + 1
            expected += row_size * ph
            rows.append((row_size, ph))
    if expected > MAX_DECODED_IMAGE_BYTES:
        raise ValueError("decoded PNG exceeds the safety size limit")
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(idat, expected + 1)
    if len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("invalid or incomplete PNG pixel stream")
    offset = 0
    for row_size, count in rows:
        for _ in range(count):
            if pixels[offset] > 4:
                raise ValueError("invalid PNG scanline filter")
            offset += row_size


def validate_image_bytes(data: bytes, expected_format: str | None = None) -> str:
    """Never accept an HTML page, a signature alone or undecodable image bytes."""
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise SystemExit("Image is empty or exceeds the 64MB safety limit.")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        image_format = "png"
        try:
            _validate_png(data)
        except (ValueError, struct.error, zlib.error, IndexError) as exc:
            raise SystemExit(f"Invalid PNG image: {exc}") from exc
    elif data.startswith(b"\xff\xd8\xff") or (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        image_format = "jpeg" if data.startswith(b"\xff\xd8\xff") else "webp"
        try:
            from PIL import Image
        except ImportError as exc:
            raise SystemExit("JPEG/WebP validation needs an already-installed Pillow decoder. Use PNG with this standard-library client; no image was saved.") from exc
        try:
            with Image.open(io.BytesIO(data)) as candidate:
                if candidate.format.lower() != image_format or candidate.width * candidate.height * 4 > MAX_DECODED_IMAGE_BYTES:
                    raise ValueError("image format or decoded size is invalid")
                candidate.verify()
            with Image.open(io.BytesIO(data)) as candidate:
                candidate.load()
        except Exception as exc:
            raise SystemExit("Image decoder rejected invalid JPEG/WebP bytes.") from exc
    else:
        raise SystemExit("Response is not a valid PNG, JPEG or WebP image.")
    if expected_format and image_format != expected_format:
        raise SystemExit(f"Image API returned {image_format}, expected {expected_format}; no image was saved.")
    return image_format


def image_summary(data: bytes, filename: str) -> dict[str, object]:
    image_format = validate_image_bytes(data)
    if image_format == "png":
        width, height = struct.unpack_from("!II", data, 16)
    else:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as candidate:
            width, height = candidate.size
    return {"filename": filename, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "width": width, "height": height, "format": image_format}


def prompt_summary(prompt: str) -> dict[str, object]:
    return {"characters": len(prompt), "sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest()}


def atomic_write_image(target: Path, data: bytes, expected_format: str | None = None) -> Path:
    validate_image_bytes(data, expected_format)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        raise SystemExit(f"Unable to save validated image: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target.resolve()


def read_image_url(url: str, *secrets: str) -> bytes:
    validate_download_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "jiang-local-store/1.0"})
    opener = urllib.request.build_opener(SafeImageRedirectHandler())
    try:
        with opener.open(request, timeout=300) as response:
            validate_download_url(response.geturl())
            data = response.read(MAX_IMAGE_BYTES + 1)
            if response.headers.get_content_type().startswith("text/") or response.headers.get_content_type() == "application/json":
                raise SystemExit("Image URL returned a text/JSON response; no image was saved.")
            return data
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        reason = redact_sensitive(str(getattr(exc, "reason", exc)), *secrets)
        raise SystemExit(f"Failed to download generated image: {reason}") from exc


def env_first(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return default


def config_path() -> Path:
    override = env_first("IMAGE2_CONFIG_FILE")
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".config" / "jiang-local-store" / "image2.env"


def load_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise SystemExit(f"Image 2 config path is not a file: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SystemExit(
            f"Image 2 config permissions are too open ({oct(mode)}): {path}. "
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
        if name not in CONFIG_KEYS:
            raise SystemExit(f"Unsupported config key on line {line_number}: {name}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if value:
            values[name] = value
    return values


def setting(config: dict[str, str], *names: str, default: str | None = None) -> str | None:
    value = env_first(*names)
    if value:
        return value
    for name in names:
        value = config.get(name)
        if value:
            return value
    return default


def validate_base_url(value: str) -> str:
    value = value.rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("IMAGE2_BASE_URL must be a complete http(s) URL.")
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise SystemExit("IMAGE2_BASE_URL must not contain credentials, a query or a fragment.")
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and parsed.hostname not in local_hosts:
        raise SystemExit("Third-party Image 2 relays must use HTTPS.")
    return value


def looks_placeholder(value: str) -> bool:
    lowered = value.lower()
    markers = ("replace-locally", "relay.example.com", "your relay", "your-key", "<本机填写>")
    return any(marker in lowered for marker in markers)


def join_endpoint(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def auth_headers(settings: dict[str, str]) -> dict[str, str]:
    header = settings["auth_header"]
    prefix = settings["auth_prefix"]
    headers = {header: f"{prefix}{settings['api_key']}", "User-Agent": "jiang-local-store/1.0"}
    raw_extra = settings.get("extra_headers", "")
    if raw_extra:
        try:
            extra = json.loads(raw_extra)
        except json.JSONDecodeError as exc:
            raise SystemExit("IMAGE2_EXTRA_HEADERS_JSON must be a JSON object.") from exc
        if not isinstance(extra, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in extra.items()
        ):
            raise SystemExit("IMAGE2_EXTRA_HEADERS_JSON must contain string header values.")
        protected = {header.lower(), "content-type", "content-length"}
        for name, value in extra.items():
            if name.lower() in protected:
                raise SystemExit(f"Extra headers cannot override protected header: {name}")
            headers[name] = value
    return headers


def resolve_settings(model_override: str | None = None) -> tuple[dict[str, str], Path]:
    path = config_path()
    config = load_config(path)
    base_url = validate_base_url(
        setting(config, "IMAGE2_BASE_URL", "OPENAI_BASE_URL", default="https://api.openai.com/v1")
    )
    auth_prefix = os.environ.get("IMAGE2_AUTH_PREFIX", config.get("IMAGE2_AUTH_PREFIX", "Bearer "))
    if auth_prefix.strip().lower() in {"none", "null", "no-prefix"}:
        auth_prefix = ""
    elif auth_prefix.strip().lower() == "bearer":
        auth_prefix = "Bearer "
    if "\r" in auth_prefix or "\n" in auth_prefix:
        raise SystemExit("IMAGE2_AUTH_PREFIX cannot contain line breaks.")
    settings = {
        "api_key": setting(config, "IMAGE2_API_KEY", "OPENAI_API_KEY", default=""),
        "base_url": base_url,
        "model": model_override
        or setting(config, "IMAGE2_MODEL", "OPENAI_IMAGE_MODEL", default="gpt-image-2"),
        "provider": setting(config, "IMAGE2_PROVIDER_NAME", default="OpenAI-compatible"),
        "auth_header": setting(config, "IMAGE2_AUTH_HEADER", default="Authorization"),
        "auth_prefix": auth_prefix,
        "extra_headers": setting(config, "IMAGE2_EXTRA_HEADERS_JSON", default=""),
        "generations_path": setting(config, "IMAGE2_GENERATIONS_PATH", default="/images/generations"),
        "edits_path": setting(config, "IMAGE2_EDITS_PATH", default="/images/edits"),
        "models_path": setting(config, "IMAGE2_MODELS_PATH", default="/models"),
        "image_field": setting(config, "IMAGE2_IMAGE_FIELD", default="image[]"),
        "mask_field": setting(config, "IMAGE2_MASK_FIELD", default="mask"),
    }
    return settings, path


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        try:
            text = Path(args.prompt_file).expanduser().read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise SystemExit("Prompt file could not be read as UTF-8.") from exc
    else:
        text = args.prompt or ""
    text = text.strip()
    if not text:
        raise SystemExit("Prompt cannot be empty.")
    return text


def validate_size(size: str) -> None:
    if size == "auto":
        return
    match = re.fullmatch(r"(\d+)x(\d+)", size)
    if not match:
        raise SystemExit("Size must be 'auto' or WIDTHxHEIGHT.")
    width, height = map(int, match.groups())
    if width <= 0 or height <= 0:
        raise SystemExit("gpt-image-2 width and height must be greater than zero.")
    pixels = width * height
    if width % 16 or height % 16:
        raise SystemExit("gpt-image-2 width and height must be multiples of 16.")
    if max(width, height) > 3840:
        raise SystemExit("gpt-image-2 maximum edge is 3840px.")
    if max(width, height) / min(width, height) > 3:
        raise SystemExit("gpt-image-2 long-to-short edge ratio cannot exceed 3:1.")
    if not 655_360 <= pixels <= 8_294_400:
        raise SystemExit("gpt-image-2 total pixels must be 655,360 to 8,294,400.")


def request_json(url: str, headers: dict[str, str], payload: dict, secrets: tuple[str, ...] = ()) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    return perform_request(request, secrets)


def multipart_body(fields: dict[str, str], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----jiang-local-store-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for field_name, path in files:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode(),
                f"Content-Type: {mime}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def request_multipart(
    url: str, headers: dict[str, str], fields: dict[str, str], files: list[tuple[str, Path]], secrets: tuple[str, ...] = ()
) -> dict:
    body, boundary = multipart_body(fields, files)
    request = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    return perform_request(request, secrets)


def perform_request(request: urllib.request.Request, secrets: tuple[str, ...] = ()) -> dict:
    secrets = (*secrets, *(value for name, value in request.header_items() if name.lower() not in {"content-type", "content-length", "user-agent", "accept"}))
    try:
        with open_api_request(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict):
                raise SystemExit("Image API returned a JSON value that is not an object.")
            return result
    except urllib.error.HTTPError as exc:
        detail = redact_sensitive(exc.read().decode("utf-8", errors="replace"), *secrets)[:1000]
        raise SystemExit(f"Image API returned HTTP {exc.code}: {detail}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise SystemExit("Image API returned invalid JSON; no image was saved.") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        detail = redact_sensitive(str(getattr(exc, "reason", exc)), *secrets)
        raise SystemExit(f"Image API connection failed: {detail}") from exc


def fetch_url(url: str, secrets: tuple[str, ...] = ()) -> bytes:
    return read_image_url(url, *secrets)


def output_paths(base: Path, count: int, output_format: str) -> list[Path]:
    suffix = ".jpg" if output_format == "jpeg" else f".{output_format}"
    accepted_suffixes = {
        "png": {".png"},
        "jpeg": {".jpg", ".jpeg"},
        "webp": {".webp"},
    }[output_format]
    if base.suffix.lower() not in accepted_suffixes:
        base = base.with_suffix(suffix)
    if count == 1:
        return [base]
    return [base.with_name(f"{base.stem}-{index:02d}{suffix}") for index in range(1, count + 1)]


def save_images(response: dict, output: Path, output_format: str, secrets: tuple[str, ...] = ()) -> list[Path]:
    if not isinstance(response, dict):
        raise SystemExit("Image API response must be a JSON object.")
    items = response.get("data")
    if not isinstance(items, list) or not items:
        detail = redact_sensitive(str(response), *secrets)[:600]
        raise SystemExit(f"Image API response has no data array: {detail}")
    paths = output_paths(output, len(items), output_format)
    saved: list[Path] = []
    for item, path in zip(items, paths):
        if not isinstance(item, dict):
            raise SystemExit("Image API data item must be an object.")
        if item.get("b64_json"):
            encoded = item["b64_json"]
            if not isinstance(encoded, str) or len(encoded) > (MAX_IMAGE_BYTES + 2) // 3 * 4:
                raise SystemExit("Image API base64 payload is invalid or exceeds the safety limit.")
            try:
                image_bytes = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as exc:
                raise SystemExit("Image API returned invalid base64 data.") from exc
        elif item.get("url"):
            if not isinstance(item["url"], str):
                raise SystemExit("Image API URL must be a string.")
            image_bytes = fetch_url(item["url"], secrets)
        else:
            raise SystemExit("Image API item contains neither b64_json nor url.")
        saved.append(atomic_write_image(path, image_bytes, output_format))
    return saved


def common_payload(args: argparse.Namespace, prompt: str, model: str) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "n": args.n,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.output_format,
        "moderation": args.moderation,
    }
    if args.background != "auto":
        payload["background"] = args.background
    if args.output_compression is not None:
        payload["output_compression"] = args.output_compression
    return payload


def run_doctor(args: argparse.Namespace) -> None:
    settings, path = resolve_settings()
    parsed = urllib.parse.urlparse(settings["base_url"])
    ready = bool(
        settings["api_key"]
        and settings["model"]
        and settings["base_url"]
        and not looks_placeholder(settings["api_key"])
        and not looks_placeholder(settings["base_url"])
        and not looks_placeholder(settings["provider"])
    )
    summary: dict[str, object] = {
        "ready": ready,
        "provider": settings["provider"],
        "base_url": settings["base_url"],
        "third_party_relay": parsed.hostname != "api.openai.com",
        "model": settings["model"],
        "api_key": "configured" if settings["api_key"] else "missing",
        "config_file": str(path),
        "config_file_exists": path.is_file(),
        "generation_endpoint": join_endpoint(settings["base_url"], settings["generations_path"]),
        "edit_endpoint": join_endpoint(settings["base_url"], settings["edits_path"]),
    }
    if args.probe_models:
        if not settings["api_key"]:
            raise SystemExit("Cannot probe relay models without an API key.")
        request = urllib.request.Request(
            join_endpoint(settings["base_url"], settings["models_path"]),
            headers=auth_headers(settings),
            method="GET",
        )
        response = perform_request(request, (settings["api_key"],))
        data = response.get("data", [])
        if not isinstance(data, list):
            raise SystemExit("Image API model list must be an array.")
        model_ids = [item.get("id") for item in data if isinstance(item, dict) and item.get("id")]
        summary["models_probe"] = {
            "returned": len(model_ids),
            "target_model_visible": settings["model"] in model_ids,
        }
    print_safe_json(summary, settings["api_key"], indent=2)
    if not ready:
        raise SystemExit(2)


def run_image(args: argparse.Namespace) -> None:
    settings, _ = resolve_settings(args.model)
    if not args.output and not args.dry_run:
        raise SystemExit("--output is required unless --dry-run is used.")
    model = settings["model"]
    validate_size(args.size)
    if args.background == "transparent":
        raise SystemExit(
            "gpt-image-2 does not support background=transparent in the Image API. "
            "Use a deterministic alpha overlay or chroma-key removal instead."
        )

    prompt = read_prompt(args)
    payload = common_payload(args, prompt, model)
    headers = auth_headers(settings)
    files: list[tuple[str, Path]] = []
    references: list[dict[str, object]] = []
    mask_summary = None
    if args.command == "edit":
        image_paths = [Path(path).expanduser().resolve() for path in args.image]
        if len(image_paths) > 16:
            raise SystemExit("Image edits accept at most 16 reference images.")
        for path in image_paths:
            if not path.is_file():
                raise SystemExit(f"Reference image does not exist: {path}")
            if path.stat().st_size >= 50 * 1024 * 1024:
                raise SystemExit(f"Reference image must be under 50MB: {path}")
            references.append(image_summary(path.read_bytes(), path.name))
        files = [(settings["image_field"], path) for path in image_paths]
        if args.mask:
            mask = Path(args.mask).expanduser().resolve()
            if not mask.is_file():
                raise SystemExit(f"Mask does not exist: {mask}")
            if mask.stat().st_size >= 50 * 1024 * 1024:
                raise SystemExit("Mask must be under 50MB.")
            validate_image_bytes(mask.read_bytes(), "png")
            mask_summary = image_summary(mask.read_bytes(), mask.name)
            files.append((settings["mask_field"], mask))
    endpoint = join_endpoint(settings["base_url"], settings["generations_path"] if args.command == "generate" else settings["edits_path"])
    if args.dry_run:
        preview = {"dry_run": True, "method": "POST", "url": endpoint,
                   "content_type": "application/json" if args.command == "generate" else "multipart/form-data",
                   "parameters": {key: value for key, value in payload.items() if key != "prompt"},
                   "prompt": prompt_summary(prompt), "references": references}
        if mask_summary is not None:
            preview["mask"] = mask_summary
        print_safe_json(preview, settings["api_key"], indent=2)
        return
    if not settings["api_key"] or looks_placeholder(settings["api_key"]):
        raise SystemExit("No Image 2 API key configured. Set it in private local config or environment; do not paste it into chat.")
    if looks_placeholder(settings["base_url"]):
        raise SystemExit("Replace the example IMAGE2_BASE_URL before calling the relay.")
    if args.command == "generate":
        response = request_json(endpoint, headers, payload, (settings["api_key"],))
    else:
        fields = {key: str(value) for key, value in payload.items()}
        response = request_multipart(
            endpoint, headers, fields, files, (settings["api_key"],)
        )

    paths = save_images(response, Path(args.output).expanduser(), args.output_format, (settings["api_key"],))
    print_safe_json({"provider": settings["provider"], "model": model, "files": [str(path) for path in paths]}, settings["api_key"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GPT Image 2 official/relay API client")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="Check local relay configuration without generating")
    doctor.add_argument("--probe-models", action="store_true", help="Call the relay's models endpoint")
    for command in ("generate", "edit"):
        sub = subparsers.add_parser(command)
        prompt_group = sub.add_mutually_exclusive_group(required=True)
        prompt_group.add_argument("--prompt")
        prompt_group.add_argument("--prompt-file")
        sub.add_argument("--model")
        sub.add_argument("--size", default="auto")
        sub.add_argument("--quality", choices=("low", "medium", "high", "auto"), default="auto")
        sub.add_argument("--background", choices=("auto", "opaque", "transparent"), default="auto")
        sub.add_argument("--output-format", choices=("png", "jpeg", "webp"), default="png")
        sub.add_argument("--output-compression", type=int, choices=range(0, 101))
        sub.add_argument("--moderation", choices=("auto", "low"), default="auto")
        sub.add_argument("--n", type=int, choices=range(1, 11), default=1)
        sub.add_argument("--output", help="Image path; required unless --dry-run is used")
        sub.add_argument("--dry-run", action="store_true", help="Validate and summarize the real request without HTTP, an API key or creating images")
        if command == "edit":
            sub.add_argument("--image", action="append", required=True, help="Repeat up to 16 times")
            sub.add_argument("--mask")
    return parser


if __name__ == "__main__":
    parsed_args = build_parser().parse_args()
    if parsed_args.command == "doctor":
        run_doctor(parsed_args)
    else:
        run_image(parsed_args)
