#!/usr/bin/env python3
"""Minimal Volcengine AUC URL transcription client.

Credentials are read from environment variables or the user's macOS Keychain.
The module never prints credential values and only supports third-party API
transcription; it does not contain a local-model fallback.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_SERVICE_URL = "https://openspeech.bytedance.com/api/v1/auc"
DEFAULT_CLUSTER = "volc_auc_meeting"
DEFAULT_KEYCHAIN_SERVICE = "volc-asr"


def _keychain_get(service: str, account: str) -> str:
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
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def resolve_credentials() -> tuple[dict[str, str], dict[str, str]]:
    """Return credentials and non-secret source labels."""
    service = os.environ.get(
        "VOLC_ASR_KEYCHAIN_SERVICE", DEFAULT_KEYCHAIN_SERVICE
    ).strip()
    env_appid = os.environ.get("VOLC_ASR_APPID", "").strip()
    env_token = os.environ.get("VOLC_ASR_ACCESS_TOKEN", "").strip()
    appid = env_appid or _keychain_get(service, "appid")
    token = env_token or _keychain_get(service, "access_token")
    return (
        {"appid": appid, "token": token},
        {
            "appid": "environment:VOLC_ASR_APPID" if env_appid else "macOS Keychain",
            "token": (
                "environment:VOLC_ASR_ACCESS_TOKEN"
                if env_token
                else "macOS Keychain"
            ),
        },
    )


def configuration_status() -> dict[str, Any]:
    credentials, sources = resolve_credentials()
    return {
        "configured": bool(credentials["appid"] and credentials["token"]),
        "provider": "volcengine-auc-url",
        "cluster": os.environ.get("VOLC_ASR_CLUSTER", DEFAULT_CLUSTER),
        "credential_sources": sources,
    }


def _post_json(
    url: str,
    payload: dict[str, Any],
    token: str,
    *,
    timeout: int = 60,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer; {token}",
            "Content-Type": "application/json",
            "User-Agent": "Shengjiang-Research/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").replace(
            token, "<redacted>"
        )
        raise RuntimeError(f"Volc ASR HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Volc ASR request failed: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Volc ASR returned a non-JSON response: "
            + raw.decode("utf-8", errors="replace")[:500]
        ) from exc


def _submit(
    *,
    audio_url: str,
    audio_format: str,
    credentials: dict[str, str],
    cluster: str,
    uid: str,
    timeout: int,
) -> dict[str, Any]:
    service_url = os.environ.get("VOLC_ASR_SERVICE_URL", DEFAULT_SERVICE_URL).rstrip(
        "/"
    )
    payload = {
        "app": {
            "appid": credentials["appid"],
            "token": credentials["token"],
            "cluster": cluster,
        },
        "user": {"uid": uid},
        "audio": {"format": audio_format, "url": audio_url},
        "additions": {"use_itn": "True", "with_speaker_info": "False"},
    }
    return _post_json(
        f"{service_url}/submit",
        payload,
        credentials["token"],
        timeout=timeout,
    )


def _submit_with_quota_fallback(
    *,
    audio_url: str,
    audio_format: str,
    credentials: dict[str, str],
    cluster: str,
    uid: str,
    timeout: int,
) -> tuple[dict[str, Any], str]:
    def submit(target_cluster: str) -> dict[str, Any]:
        return _submit(
            audio_url=audio_url,
            audio_format=audio_format,
            credentials=credentials,
            cluster=target_cluster,
            uid=uid,
            timeout=timeout,
        )

    try:
        submitted = submit(cluster)
    except RuntimeError as exc:
        if "audio_duration_lifetime" not in str(exc) or not cluster.endswith(
            "_flash"
        ):
            raise
        fallback_cluster = cluster[: -len("_flash")]
        return submit(fallback_cluster), fallback_cluster

    response = submitted.get("resp") or {}
    response_text = json.dumps(response, ensure_ascii=False)
    if (
        str(response.get("code") or "") != "1000"
        and "audio_duration_lifetime" in response_text
        and cluster.endswith("_flash")
    ):
        fallback_cluster = cluster[: -len("_flash")]
        return submit(fallback_cluster), fallback_cluster
    return submitted, cluster


def _wait(
    *,
    task_id: str,
    credentials: dict[str, str],
    cluster: str,
    timeout_seconds: int,
    poll_interval: int,
) -> dict[str, Any]:
    service_url = os.environ.get("VOLC_ASR_SERVICE_URL", DEFAULT_SERVICE_URL).rstrip(
        "/"
    )
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last = _post_json(
            f"{service_url}/query",
            {
                "appid": credentials["appid"],
                "token": credentials["token"],
                "cluster": cluster,
                "id": task_id,
            },
            credentials["token"],
            timeout=60,
        )
        response = last.get("resp") or {}
        code = str(response.get("code") or "")
        if code == "1000" and response.get("text"):
            return last
        if code not in {"1000", "2000", "2001"}:
            raise RuntimeError(
                "Volc ASR task failed: "
                + json.dumps(last, ensure_ascii=False)[:1000]
            )
        time.sleep(poll_interval)
    raise TimeoutError(
        f"Volc ASR task timed out: {task_id}; last="
        + json.dumps(last, ensure_ascii=False)[:500]
    )


def transcribe_url(
    audio_url: str,
    *,
    audio_format: str,
    uid: str,
    timeout_seconds: int = 900,
    poll_interval: int = 5,
) -> tuple[dict[str, Any], str]:
    credentials, _ = resolve_credentials()
    if not credentials["appid"] or not credentials["token"]:
        raise RuntimeError(
            "Volc ASR credentials are not configured in environment variables "
            "or the user's macOS Keychain."
        )
    primary_cluster = os.environ.get("VOLC_ASR_CLUSTER", DEFAULT_CLUSTER)
    submitted, selected_cluster = _submit_with_quota_fallback(
        audio_url=audio_url,
        audio_format=audio_format,
        credentials=credentials,
        cluster=primary_cluster,
        uid=uid,
        timeout=60,
    )
    response = submitted.get("resp") or {}
    if str(response.get("code") or "") != "1000" or not response.get("id"):
        raise RuntimeError(
            "Volc ASR submission failed: "
            + json.dumps(submitted, ensure_ascii=False)[:1000]
        )
    result = _wait(
        task_id=str(response["id"]),
        credentials=credentials,
        cluster=selected_cluster,
        timeout_seconds=timeout_seconds,
        poll_interval=poll_interval,
    )
    return result, selected_cluster


def write_transcript_files(
    result: dict[str, Any],
    output_dir: Path,
    *,
    title: str,
    source: str,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    response = result.get("resp") or {}
    text = str(response.get("text") or "").strip()
    raw_path = output_dir / "transcript.raw.json"
    text_path = output_dir / "transcript.txt"
    markdown_path = output_dir / "transcript.md"
    raw_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    lines = [f"# {title or '视频逐字稿'}", "", f"来源：{source}", "", "## 全文", "", text]
    utterances = response.get("utterances") or []
    if utterances:
        lines.extend(["", "## 分句", ""])
        for item in utterances:
            start = int(item.get("start_time") or 0) / 1000
            end = int(item.get("end_time") or 0) / 1000
            sentence = str(item.get("text") or "").strip()
            lines.append(f"- [{start:.2f}-{end:.2f}] {sentence}")
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "raw": str(raw_path),
        "txt": str(text_path),
        "md": str(markdown_path),
    }
