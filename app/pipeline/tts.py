"""Async TTS generation via DashScope CosyVoice WebSocket API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid

import websockets

from ..config import settings

log = logging.getLogger("pipeline.tts")


async def generate_one(text: str, key: str) -> bytes:
    """Generate TTS audio for a single text segment. Returns MP3 bytes."""
    if not text.strip():
        return b""

    chunks: list[bytes] = []
    async with websockets.connect(
        settings.tts_ws_url,
        additional_headers={"Authorization": f"Bearer {key}"},
    ) as ws:
        task_id = str(uuid.uuid4())
        await ws.send(json.dumps({
            "header": {"action": "run-task", "task_id": task_id, "streaming": "out"},
            "payload": {
                "model": settings.tts_model,
                "task_group": "audio",
                "task": "tts",
                "function": "SpeechSynthesizer",
                "input": {"text": text},
                "parameters": {
                    "voice": settings.tts_voice,
                    "format": "mp3",
                    "text_type": "PlainText",
                },
            },
        }))

        async for msg in ws:
            if isinstance(msg, bytes):
                chunks.append(msg)
            else:
                data = json.loads(msg)
                event = data.get("header", {}).get("event", "")
                if event == "task-finished":
                    break
                elif event == "task-failed":
                    raise RuntimeError(f"TTS 失败: {data}")

    return b"".join(chunks)


async def generate_all(scene_data: dict, audio_dir: str) -> int:
    """Generate TTS for every solution_script step. Returns count of files written."""
    os.makedirs(audio_dir, exist_ok=True)
    steps = scene_data.get("solution_script", [])
    keys = settings.tts_keys
    count = 0

    for i, step in enumerate(steps):
        text = step.get("speech", "")
        out_path = os.path.join(audio_dir, f"step_{i}.mp3")
        key = keys[i % len(keys)]

        for attempt in range(3):
            try:
                buf = await generate_one(text, key)
                if buf:
                    with open(out_path, "wb") as f:
                        f.write(buf)
                    count += 1
                    log.info("TTS %d/%d OK (%d bytes)", i + 1, len(steps), len(buf))
                break
            except Exception as e:
                log.warning("TTS %d/%d 失败 (attempt %d): %s", i + 1, len(steps), attempt + 1, e)
                if attempt < 2:
                    await asyncio.sleep(1)

    return count
