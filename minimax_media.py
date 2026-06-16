"""MiniMax audio + video generation helpers.

These call MiniMax's *platform* API (https://api.minimax.io) which is separate
from the OpenRouter text endpoint used by the chat agent. They power the
audio (Text-to-Speech) and video (Text-to-Video) demo features.

Required environment variables:
    MINIMAX_API_KEY    - Bearer token from platform.minimax.io > API Keys
    MINIMAX_API_HOST   - optional, defaults to https://api.minimax.io
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

API_HOST = os.getenv("MINIMAX_API_HOST", "https://api.minimax.io").rstrip("/")

# Default models / voices — overridable per request.
DEFAULT_TTS_MODEL = "speech-2.6-hd"
DEFAULT_VOICE_ID = "English_expressive_narrator"
DEFAULT_VIDEO_MODEL = "MiniMax-Hailuo-02"


class MiniMaxConfigError(RuntimeError):
    """Raised when MiniMax credentials are missing."""


class MiniMaxAPIError(RuntimeError):
    """Raised when the MiniMax API returns an error payload."""


def _api_key() -> str:
    key = os.getenv("MINIMAX_API_KEY")
    if not key or key.strip() in {"", "PASTE_YOUR_MINIMAX_KEY_HERE"}:
        raise MiniMaxConfigError(
            "MINIMAX_API_KEY is not set. Add it to .env "
            "(get one at https://platform.minimax.io/user-center/basic-information/interface-key)."
        )
    return key


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }


def _check_base_resp(payload: dict, context: str) -> None:
    base = payload.get("base_resp", {})
    status_code = base.get("status_code", 0)
    if status_code not in (0, None):
        raise MiniMaxAPIError(
            f"{context} failed (status_code={status_code}): "
            f"{base.get('status_msg', 'unknown error')}"
        )


# ── Text-to-Speech (synchronous) ─────────────────────────────────────────────
async def text_to_speech(
    text: str,
    *,
    voice_id: str = DEFAULT_VOICE_ID,
    model: str = DEFAULT_TTS_MODEL,
    audio_format: str = "mp3",
    speed: float = 1.0,
) -> bytes:
    """Convert text to speech and return raw audio bytes (mp3 by default)."""

    if not text or not text.strip():
        raise ValueError("text must be a non-empty string")

    url = f"{API_HOST}/v1/t2a_v2"
    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": "auto",
        "output_format": "hex",
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": 1,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": audio_format,
            "channel": 1,
        },
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=_auth_headers(), json=payload)
        response.raise_for_status()
        data = response.json()

    _check_base_resp(data, "Text-to-speech")

    hex_audio = data.get("data", {}).get("audio")
    if not hex_audio:
        raise MiniMaxAPIError("Text-to-speech returned no audio data")

    return bytes.fromhex(hex_audio)


# ── Text-to-Video (asynchronous task + polling) ──────────────────────────────
async def _create_video_task(
    client: httpx.AsyncClient,
    prompt: str,
    model: str,
    duration: int,
    resolution: str,
) -> str:
    url = f"{API_HOST}/v1/video_generation"
    payload = {
        "prompt": prompt,
        "model": model,
        "duration": duration,
        "resolution": resolution,
    }
    response = await client.post(url, headers=_auth_headers(), json=payload)
    response.raise_for_status()
    data = response.json()
    _check_base_resp(data, "Video task creation")

    task_id = data.get("task_id")
    if not task_id:
        raise MiniMaxAPIError("Video task creation returned no task_id")
    return task_id


async def _poll_video_task(
    client: httpx.AsyncClient,
    task_id: str,
    poll_interval: int,
    max_attempts: int,
) -> str:
    url = f"{API_HOST}/v1/query/video_generation"
    for _ in range(max_attempts):
        await asyncio.sleep(poll_interval)
        response = await client.get(
            url, headers=_auth_headers(), params={"task_id": task_id}
        )
        response.raise_for_status()
        data = response.json()
        status = data.get("status")

        if status == "Success":
            file_id = data.get("file_id")
            if not file_id:
                raise MiniMaxAPIError("Video task succeeded but returned no file_id")
            return file_id
        if status == "Fail":
            raise MiniMaxAPIError(
                f"Video generation failed: {data.get('error_message', 'unknown error')}"
            )
        # Preparing / Queueing / Processing -> keep polling

    raise MiniMaxAPIError(
        f"Video generation timed out after {poll_interval * max_attempts}s"
    )


async def _fetch_video_url(client: httpx.AsyncClient, file_id: str) -> str:
    url = f"{API_HOST}/v1/files/retrieve"
    response = await client.get(url, headers=_auth_headers(), params={"file_id": file_id})
    response.raise_for_status()
    data = response.json()
    download_url = data.get("file", {}).get("download_url")
    if not download_url:
        raise MiniMaxAPIError("Could not retrieve video download URL")
    return download_url


async def generate_video(
    prompt: str,
    *,
    model: str = DEFAULT_VIDEO_MODEL,
    duration: int = 6,
    resolution: str = "768P",
    poll_interval: int = 10,
    max_attempts: int = 60,
) -> str:
    """Create a text-to-video task, poll until done, return a download URL."""

    if not prompt or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    async with httpx.AsyncClient(timeout=120) as client:
        task_id = await _create_video_task(client, prompt, model, duration, resolution)
        file_id = await _poll_video_task(client, task_id, poll_interval, max_attempts)
        return await _fetch_video_url(client, file_id)
