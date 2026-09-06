#!/usr/bin/env python3
"""Download public social videos and create transcripts with minimal orchestration.

Supported fast paths:
- Douyin share URL -> TikHub detail -> MP4 download -> Volc AUC URL ASR
- Xiaohongshu video URL -> TikHub detail -> MP4 download -> Volc AUC audio URL ASR
- WeChat Channels share URL -> TikHub detail -> optional external decrypting downloader

Batch runs are resumable by source URL. Completed items are skipped before a
new paid TikHub request is made.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import tikhub_request
import volc_auc


PLATFORM_ROUTES = {
    "douyin": {
        "path": "/api/v1/douyin/web/fetch_one_video_by_share_url",
        "param": "share_url",
    },
    "xiaohongshu": {
        "path": "/api/v1/xiaohongshu/app_v2/get_video_note_detail",
        "param": "share_text",
    },
    "wechat_channels": {
        "path": "/api/v1/wechat_channels/v2/fetch_video_detail",
        "param": "share_url",
    },
}

TEMPORARY_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "cache_url",
    "decode_key",
    "full_url",
    "key",
    "secret",
    "sign",
    "token",
    "url_token",
}


@dataclass
class VideoRecord:
    platform: str
    source_url: str
    content_id: str
    title: str
    author_name: str
    published_at: str
    endpoint: str
    video_url: str = ""
    video_url_source: str = ""
    asr_url: str = ""
    asr_format: str = "mp4"
    decode_key: str = ""
    official_transcript: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def safe_component(value: str, fallback: str) -> str:
    text = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "-", value).strip("-.")
    return (text[:80] or fallback).strip("-.")


def redact_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return "<redacted-url>"
    if not parsed.scheme or not parsed.netloc:
        return "<redacted-url>"
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, "", "")
    )


def sanitize_payload(value: Any, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            lowered = key.lower()
            if lowered in TEMPORARY_SECRET_KEYS:
                output[key] = "<redacted>"
            elif lowered in {"master_url", "backup_urls", "url_list"}:
                if isinstance(item, str):
                    output[key] = redact_url(item)
                elif isinstance(item, list):
                    output[key] = [
                        redact_url(entry) if isinstance(entry, str) else "<redacted>"
                        for entry in item
                    ]
                else:
                    output[key] = "<redacted>"
            else:
                output[key] = sanitize_payload(item, lowered)
        return output
    if isinstance(value, list):
        return [sanitize_payload(item, parent_key) for item in value]
    if isinstance(value, str) and parent_key.endswith("url"):
        return redact_url(value)
    return value


def redact_error(message: str) -> str:
    return re.sub(r"https?://[^\s]+", "<redacted-url>", message)[:1000]


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def first_nonempty(mapping: dict[str, Any], names: Iterable[str]) -> str:
    for name in names:
        value = mapping.get(name)
        if value not in (None, "", [], {}):
            return clean_text(value)
    return ""


def detect_platform(url: str) -> str:
    host = urllib.parse.urlsplit(url).netloc.lower()
    if "douyin.com" in host:
        return "douyin"
    if any(domain in host for domain in ("xiaohongshu.com", "xhslink.com", "xhslink.cn")):
        return "xiaohongshu"
    if any(domain in host for domain in ("weixin.qq.com", "channels.weixin.qq.com")):
        return "wechat_channels"
    raise ValueError(f"Unsupported video URL host: {host or url}")


def extract_links(text: str) -> list[str]:
    found = []
    for match in re.findall(r"https?://[^\s]+", text):
        url = match.rstrip("。；，、,.!！?？)]}〉》\"'")
        if url not in found:
            found.append(url)
    return found


def load_links(args: argparse.Namespace) -> list[str]:
    links = []
    for raw in args.url or []:
        extracted = extract_links(raw)
        links.extend(extracted or [raw.strip()])
    if args.links_file:
        links.extend(extract_links(Path(args.links_file).read_text(encoding="utf-8")))
    deduplicated = []
    for link in links:
        if link and link not in deduplicated:
            deduplicated.append(link)
    return deduplicated


def payload_has_data(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("code") not in (None, 0, 200):
        return False
    data = payload.get("data")
    return data not in (None, "", [], {})


def find_official_transcript(payload: Any) -> str:
    """Only accept fields that explicitly represent subtitles/transcripts."""
    direct_keys = {
        "subtitle_text",
        "transcript",
        "transcript_text",
        "recognition_text",
        "speech_text",
    }
    list_keys = {"subtitles", "subtitle_list", "captions", "caption_list"}
    candidates = []
    for obj in walk_dicts(payload):
        for key in direct_keys:
            value = obj.get(key)
            if isinstance(value, str) and len(value.strip()) >= 20:
                candidates.append(value.strip())
        for key in list_keys:
            value = obj.get(key)
            if not isinstance(value, list):
                continue
            sentences = []
            for item in value:
                if isinstance(item, str):
                    sentences.append(item.strip())
                elif isinstance(item, dict):
                    sentence = first_nonempty(item, ("text", "content", "sentence"))
                    if sentence:
                        sentences.append(sentence)
            joined = "".join(sentences).strip()
            if len(joined) >= 20:
                candidates.append(joined)
    return max(candidates, key=len) if candidates else ""


def _urls_from_address(value: Any) -> list[str]:
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return [value]
    if not isinstance(value, dict):
        return []
    output = []
    for key in ("url_list", "backup_urls"):
        items = value.get(key)
        if isinstance(items, list):
            output.extend(
                item
                for item in items
                if isinstance(item, str) and item.startswith(("http://", "https://"))
            )
    for key in ("url", "master_url", "play_url", "download_url"):
        item = value.get(key)
        if isinstance(item, str) and item.startswith(("http://", "https://")):
            output.append(item)
    return output


def _find_douyin_aweme(payload: Any) -> dict[str, Any]:
    candidates = []
    for obj in walk_dicts(payload):
        if obj.get("aweme_id") and isinstance(obj.get("video"), dict):
            candidates.append(obj)
        wrapped = obj.get("aweme_info")
        if isinstance(wrapped, dict) and wrapped.get("aweme_id"):
            candidates.append(wrapped)
    if not candidates:
        raise ValueError("TikHub response does not contain a Douyin video object")
    return max(candidates, key=lambda item: len(json.dumps(item, ensure_ascii=False)))


def extract_douyin(payload: dict[str, Any], source_url: str, endpoint: str) -> VideoRecord:
    aweme = _find_douyin_aweme(payload)
    video = aweme.get("video") or {}
    candidates: list[tuple[int, str, str]] = []
    for score, key in (
        (120, "download_addr"),
        (110, "play_addr_h264"),
        (100, "play_addr"),
        (90, "play_addr_265"),
    ):
        for url in _urls_from_address(video.get(key)):
            candidates.append((score, url, f"video.{key}"))
    for stream in video.get("bit_rate") or []:
        if not isinstance(stream, dict):
            continue
        bitrate = int(stream.get("bit_rate") or 0)
        for url in _urls_from_address(stream.get("play_addr")):
            candidates.append((80 + min(20, bitrate // 500_000), url, "video.bit_rate"))
    if not candidates:
        raise ValueError("TikHub response does not contain a Douyin media URL")
    _, video_url, source = max(candidates, key=lambda item: item[0])
    author = aweme.get("author") or {}
    content_id = str(aweme.get("aweme_id") or "")
    return VideoRecord(
        platform="douyin",
        source_url=source_url,
        content_id=content_id,
        title=first_nonempty(aweme, ("desc", "preview_title", "item_title")) or content_id,
        author_name=first_nonempty(author, ("nickname", "unique_id", "short_id")),
        published_at=clean_text(aweme.get("create_time")),
        endpoint=endpoint,
        video_url=video_url,
        video_url_source=source,
        asr_url=video_url,
        asr_format="mp4",
        official_transcript=find_official_transcript(aweme),
    )


def _find_xiaohongshu_note(payload: Any) -> dict[str, Any]:
    candidates = []
    for obj in walk_dicts(payload):
        if isinstance(obj.get("video_info_v2"), dict):
            candidates.append(obj)
        if obj.get("type") == "video" and any(
            key in obj for key in ("note_id", "id", "video_info")
        ):
            candidates.append(obj)
    if not candidates:
        raise ValueError("TikHub response does not contain a Xiaohongshu video note")
    return max(candidates, key=lambda item: len(json.dumps(item, ensure_ascii=False)))


def _best_xhs_stream(streams: Any) -> tuple[str, str]:
    if not isinstance(streams, list):
        return "", ""
    candidates = []
    for item in streams:
        if not isinstance(item, dict):
            continue
        urls = _urls_from_address(item)
        if not urls:
            continue
        score = (
            int(item.get("width") or 0) * int(item.get("height") or 0),
            int(item.get("video_bitrate") or item.get("audio_bitrate") or 0),
        )
        candidates.append((score, urls[0], clean_text(item.get("format"))))
    if not candidates:
        return "", ""
    _, url, fmt = max(candidates, key=lambda item: item[0])
    return url, fmt


def extract_xiaohongshu(payload: dict[str, Any], source_url: str, endpoint: str) -> VideoRecord:
    note = _find_xiaohongshu_note(payload)
    video_info = note.get("video_info_v2") or note.get("video_info") or {}
    media = video_info.get("media") or video_info
    streams = media.get("stream") or {}
    video_url, video_format = _best_xhs_stream(streams.get("h264"))
    source = "video_info_v2.media.stream.h264"
    if not video_url:
        video_url, video_format = _best_xhs_stream(streams.get("h265"))
        source = "video_info_v2.media.stream.h265"
    if not video_url:
        raise ValueError("TikHub response does not contain a Xiaohongshu video URL")
    audio_streams = (media.get("audio_stream") or {}).get("AAC")
    audio_url, audio_format = _best_xhs_stream(audio_streams)
    user = note.get("user") or note.get("author") or {}
    content_id = str(note.get("note_id") or note.get("id") or "")
    return VideoRecord(
        platform="xiaohongshu",
        source_url=source_url,
        content_id=content_id,
        title=first_nonempty(note, ("title", "display_title", "desc")) or content_id,
        author_name=first_nonempty(user, ("nickname", "nick_name", "name")),
        published_at=clean_text(note.get("timestamp") or note.get("time")),
        endpoint=endpoint,
        video_url=video_url,
        video_url_source=source,
        asr_url=audio_url or video_url,
        asr_format="m4a" if audio_url else (video_format.lower() or "mp4"),
        official_transcript=find_official_transcript(note),
        extra={"video_format": video_format, "audio_format": audio_format},
    )


def extract_wechat(payload: dict[str, Any], source_url: str, endpoint: str) -> VideoRecord:
    candidates = [obj for obj in walk_dicts(payload) if isinstance(obj.get("media"), dict)]
    if not candidates:
        raise ValueError("TikHub response does not contain a WeChat Channels video")
    item = max(candidates, key=lambda obj: len(json.dumps(obj, ensure_ascii=False)))
    media = item.get("media") or {}
    video_url = clean_text(media.get("full_url") or media.get("url"))
    if not video_url:
        raise ValueError("TikHub response does not contain a WeChat media URL")
    content_id = str(item.get("id") or item.get("object_id") or "")
    return VideoRecord(
        platform="wechat_channels",
        source_url=source_url,
        content_id=content_id,
        title=first_nonempty(item, ("title", "description")) or content_id,
        author_name=first_nonempty(item, ("nickname", "author_name", "username")),
        published_at=clean_text(item.get("create_time")),
        endpoint=endpoint,
        video_url=video_url,
        video_url_source="media.full_url",
        decode_key=clean_text(media.get("decode_key")),
        official_transcript=find_official_transcript(item),
    )


def extract_record(platform_name: str, payload: dict[str, Any], source_url: str) -> VideoRecord:
    endpoint = PLATFORM_ROUTES[platform_name]["path"]
    if platform_name == "douyin":
        return extract_douyin(payload, source_url, endpoint)
    if platform_name == "xiaohongshu":
        return extract_xiaohongshu(payload, source_url, endpoint)
    if platform_name == "wechat_channels":
        return extract_wechat(payload, source_url, endpoint)
    raise ValueError(f"Unsupported platform: {platform_name}")


def fetch_detail(
    platform_name: str,
    source_url: str,
    config: dict[str, Any],
    api_key: str,
    timeout: int,
) -> dict[str, Any]:
    route = PLATFORM_ROUTES[platform_name]
    method = "GET"
    params: dict[str, Any] | None = {route["param"]: source_url}
    body: dict[str, Any] | None = None
    if platform_name == "wechat_channels":
        method = "POST"
        params = None
        body = {"share_url": source_url, "raw": False}
    try:
        payload = tikhub_request.request_json(
            config=config,
            api_key=api_key,
            method=method,
            path=route["path"],
            params=params,
            body=body,
            timeout=timeout,
        )
    except SystemExit as exc:
        raise RuntimeError(f"TikHub request failed for {platform_name}") from exc
    if not payload_has_data(payload):
        raise RuntimeError(
            "TikHub returned no usable video data: "
            + json.dumps(sanitize_payload(payload), ensure_ascii=False)[:1000]
        )
    return payload


def is_mp4(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 16:
        return False
    with path.open("rb") as handle:
        header = handle.read(32)
    return b"ftyp" in header


def download_video(url: str, output: Path, *, timeout: int, replace: bool) -> int:
    if is_mp4(output) and not replace:
        return output.stat().st_size
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".part")
    partial.unlink(missing_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Accept": "*/*",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, partial.open(
            "wb"
        ) as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Video download failed: {exc}") from exc
    partial.replace(output)
    if not is_mp4(output):
        output.unlink(missing_ok=True)
        raise RuntimeError("Downloaded file is not a valid MP4")
    return output.stat().st_size


def download_wechat_with_helper(
    payload: dict[str, Any],
    output: Path,
    *,
    helper: str,
    replace: bool,
) -> int:
    if is_mp4(output) and not replace:
        return output.stat().st_size
    helper_path = Path(helper).expanduser().resolve()
    if not helper_path.is_file():
        raise RuntimeError(f"WeChat decrypting downloader not found: {helper_path}")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required by the WeChat decrypting downloader")
    with tempfile.TemporaryDirectory(prefix="shengjiang-wechat-video-") as temporary:
        root = Path(temporary)
        raw_path = root / "detail.json"
        helper_output = root / "download"
        raw_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        command = [
            node,
            str(helper_path),
            "--videos-json",
            str(raw_path),
            "--output-dir",
            str(helper_output),
            "--limit",
            "1",
        ]
        if replace:
            command.append("--replace")
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                "WeChat downloader failed: "
                + redact_error((completed.stderr or completed.stdout)[-1000:])
            )
        matches = sorted((helper_output / "decrypted").glob("*.mp4"))
        if not matches or not is_mp4(matches[0]):
            raise RuntimeError("WeChat downloader did not produce a valid MP4")
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(matches[0], output)
    return output.stat().st_size


def write_official_transcript(item_dir: Path, record: VideoRecord) -> dict[str, str]:
    text_path = item_dir / "transcript.txt"
    markdown_path = item_dir / "transcript.md"
    text_path.write_text(record.official_transcript.rstrip() + "\n", encoding="utf-8")
    markdown_path.write_text(
        f"# {record.title or '视频逐字稿'}\n\n"
        "来源：平台官方字幕或作者提供文本\n\n"
        f"## 全文\n\n{record.official_transcript.rstrip()}\n",
        encoding="utf-8",
    )
    return {"txt": str(text_path), "md": str(markdown_path)}


def public_url_for_file(public_base_url: str, root: Path, path: Path) -> str:
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return public_base_url.rstrip("/") + "/" + urllib.parse.quote(relative, safe="/")


def record_metadata(record: VideoRecord, status: dict[str, Any]) -> dict[str, Any]:
    return {
        "platform": record.platform,
        "content_id": record.content_id,
        "source_url": record.source_url,
        "author_name": record.author_name,
        "title": record.title,
        "published_at": record.published_at,
        "collected_at": status.get("collected_at"),
        "endpoint": record.endpoint,
        "video_url_source": record.video_url_source,
        "video_file": status.get("video_file"),
        "video_bytes": status.get("video_bytes"),
        "transcript_source": status.get("transcript_source"),
        "transcript_files": status.get("transcript_files"),
        "extra": record.extra,
    }


def plan_for_links(links: list[str], transcribe: str) -> dict[str, Any]:
    items = []
    counts: dict[str, int] = {}
    for url in links:
        platform_name = detect_platform(url)
        route = PLATFORM_ROUTES[platform_name]
        counts[route["path"]] = counts.get(route["path"], 0) + 1
        items.append(
            {
                "source_url": url,
                "platform": platform_name,
                "endpoint": route["path"],
                "tikhub_requests": 1,
            }
        )
    return {
        "dry_run": True,
        "items": items,
        "tikhub_request_count": sum(counts.values()),
        "endpoint_request_counts": counts,
        "transcription": transcribe,
        "asr_note": "Third-party ASR requests and charges are separate from TikHub.",
    }


def process_one(
    *,
    index: int,
    source_url: str,
    root: Path,
    config: dict[str, Any],
    api_key: str,
    args: argparse.Namespace,
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    platform_name = detect_platform(source_url)
    status: dict[str, Any] = {
        "index": index,
        "source_url": source_url,
        "platform": platform_name,
        "status": "running",
        "started_at": utc_now(),
        "collected_at": utc_now(),
    }
    if existing and existing.get("status") == "done" and not args.replace:
        return dict(existing, skipped=True)

    if args.metadata_json:
        payload = read_json(Path(args.metadata_json), {})
    else:
        payload = fetch_detail(
            platform_name,
            source_url,
            config,
            api_key,
            args.timeout,
        )
    record = extract_record(platform_name, payload, source_url)
    content_id = record.content_id or f"item-{index}"
    item_dir = root / f"{index:03d}-{platform_name}-{safe_component(content_id, str(index))}"
    item_dir.mkdir(parents=True, exist_ok=True)
    status_path = item_dir / "status.json"
    status.update(
        {
            "content_id": content_id,
            "title": record.title,
            "author_name": record.author_name,
            "item_dir": str(item_dir),
            "endpoint": record.endpoint,
        }
    )
    write_json(status_path, status)
    write_json(item_dir / "metadata.raw.sanitized.json", sanitize_payload(payload))

    video_path = item_dir / "video.mp4"
    try:
        if platform_name == "wechat_channels":
            helper = args.wechat_downloader or os.environ.get(
                "SHENGJIANG_WECHAT_DOWNLOADER", ""
            )
            if not helper:
                raise RuntimeError(
                    "WeChat video detail was fetched, but the decrypting downloader "
                    "is not configured. Set SHENGJIANG_WECHAT_DOWNLOADER or pass "
                    "--wechat-downloader."
                )
            size = download_wechat_with_helper(
                payload,
                video_path,
                helper=helper,
                replace=args.replace,
            )
        else:
            size = download_video(
                record.video_url,
                video_path,
                timeout=max(args.timeout, 600),
                replace=args.replace,
            )
        status.update({"video_file": str(video_path), "video_bytes": size})
    except Exception as exc:
        status.update(
            {
                "status": "failed",
                "stage": "download",
                "error": redact_error(str(exc)),
                "finished_at": utc_now(),
            }
        )
        write_json(status_path, status)
        write_json(item_dir / "metadata.json", record_metadata(record, status))
        return status

    try:
        if args.transcribe == "off":
            status.update({"transcript_source": "disabled"})
        elif record.official_transcript:
            transcript_files = write_official_transcript(item_dir, record)
            status.update(
                {
                    "transcript_source": "platform_official_or_author_text",
                    "transcript_files": transcript_files,
                }
            )
        else:
            asr_status = volc_auc.configuration_status()
            if not asr_status["configured"]:
                if args.transcribe == "volc":
                    raise RuntimeError("Volc ASR is required but not configured")
                status.update(
                    {
                        "transcript_source": "pending_third_party_api",
                        "transcript_status": "pending",
                        "transcript_blocker": "Volc ASR is not configured",
                    }
                )
            else:
                asr_url = record.asr_url
                asr_format = record.asr_format
                if not asr_url and args.public_base_url:
                    asr_url = public_url_for_file(args.public_base_url, root, video_path)
                    asr_format = "mp4"
                if not asr_url:
                    status.update(
                        {
                            "transcript_source": "pending_third_party_api",
                            "transcript_status": "pending",
                            "transcript_blocker": (
                                "Downloaded media needs a public URL before URL-mode ASR; "
                                "pass --public-base-url after serving the output root."
                            ),
                        }
                    )
                else:
                    result, cluster = volc_auc.transcribe_url(
                        asr_url,
                        audio_format=asr_format,
                        uid=f"shengjiang-{platform_name}-{content_id}",
                        timeout_seconds=args.asr_timeout,
                        poll_interval=args.poll_interval,
                    )
                    transcript_files = volc_auc.write_transcript_files(
                        result,
                        item_dir,
                        title=record.title,
                        source=f"火山引擎 AUC（{cluster}）",
                    )
                    status.update(
                        {
                            "transcript_source": "volcengine_auc",
                            "transcript_status": "done",
                            "asr_cluster": cluster,
                            "transcript_files": transcript_files,
                        }
                    )
    except Exception as exc:
        status.update(
            {
                "status": "partial",
                "stage": "transcribe",
                "error": redact_error(str(exc)),
                "finished_at": utc_now(),
            }
        )
        write_json(status_path, status)
        write_json(item_dir / "metadata.json", record_metadata(record, status))
        return status

    transcript_source = status.get("transcript_source")
    status["status"] = (
        "done"
        if transcript_source not in {"pending_third_party_api"}
        else "partial"
    )
    status["stage"] = "complete" if status["status"] == "done" else "transcribe"
    status["finished_at"] = utc_now()
    write_json(status_path, status)
    write_json(item_dir / "metadata.json", record_metadata(record, status))
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", help="Video URL or share text; repeat for batches")
    parser.add_argument("--links-file", help="UTF-8 text file containing one or more URLs")
    parser.add_argument("--out", help="Output root; defaults to a system temporary directory")
    parser.add_argument("--dry-run", action="store_true", help="Show routes and request count without paid calls")
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--config", help="JSON config; defaults to config.json in the Skill")
    parser.add_argument("--key-file", help="Read the TikHub key from any chosen file path")
    parser.add_argument("--metadata-json", help="Offline test: use one saved TikHub response instead of a paid call")
    parser.add_argument("--transcribe", choices=("auto", "volc", "off"), default="auto")
    parser.add_argument("--wechat-downloader", help="Path to the optional WeChat WASM decrypting downloader")
    parser.add_argument("--public-base-url", help="Public URL serving the output root for local-file URL ASR")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--asr-timeout", type=int, default=900)
    parser.add_argument("--poll-interval", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = tikhub_request.load_config(args.config, args.key_file)
    except (OSError, ValueError) as exc:
        print(f"Invalid config: {exc}", file=sys.stderr)
        return 2
    api_key, key_source = tikhub_request.resolve_api_key(config)

    if args.check_config:
        print(
            json.dumps(
                {
                    "tikhub": {
                        "configured": bool(api_key),
                        "source": key_source,
                        "api_base": config["api_base"],
                    },
                    "asr": volc_auc.configuration_status(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    links = load_links(args)
    if not links:
        print("Provide --url or --links-file", file=sys.stderr)
        return 2
    if args.metadata_json and len(links) != 1:
        print("--metadata-json supports exactly one --url", file=sys.stderr)
        return 2
    try:
        plan = plan_for_links(links, args.transcribe)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    root = (
        Path(args.out).expanduser().resolve()
        if args.out
        else Path(tempfile.gettempdir())
        / "shengjiang-video-pipeline"
        / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    manifest_path = root / "manifest.json"
    prior = read_json(manifest_path, {"items": []})
    prior_by_url = {
        item.get("source_url"): item
        for item in prior.get("items") or []
        if item.get("source_url")
    }
    unfinished_links = [
        link
        for link in links
        if args.replace or (prior_by_url.get(link) or {}).get("status") != "done"
    ]
    if not args.metadata_json and not api_key and unfinished_links:
        print(
            "TikHub API key not found. Save it once with "
            "tikhub_request.py --configure-local-key, choose --key-file, or use --dry-run.",
            file=sys.stderr,
        )
        return 2

    root.mkdir(parents=True, exist_ok=True)
    results = []
    for index, source_url in enumerate(links, start=1):
        try:
            result = process_one(
                index=index,
                source_url=source_url,
                root=root,
                config=config,
                api_key=api_key,
                args=args,
                existing=prior_by_url.get(source_url),
            )
        except Exception as exc:
            result = {
                "index": index,
                "source_url": source_url,
                "platform": detect_platform(source_url),
                "status": "failed",
                "stage": "metadata",
                "error": redact_error(str(exc)),
                "finished_at": utc_now(),
            }
        results.append(result)
        write_json(
            manifest_path,
            {
                "created_at": prior.get("created_at") or utc_now(),
                "updated_at": utc_now(),
                "output_root": str(root),
                "items": results,
                "summary": {
                    "total": len(results),
                    "done": sum(item.get("status") == "done" for item in results),
                    "partial": sum(item.get("status") == "partial" for item in results),
                    "failed": sum(item.get("status") == "failed" for item in results),
                },
            },
        )
        print(
            json.dumps(
                {
                    "index": index,
                    "platform": result.get("platform"),
                    "status": result.get("status"),
                    "content_id": result.get("content_id"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    summary = read_json(manifest_path, {}).get("summary") or {}
    print(
        json.dumps(
            {"output_root": str(root), "manifest": str(manifest_path), **summary},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if summary.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
