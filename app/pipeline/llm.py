"""Async LLM client using aiohttp — supports OpenAI and Anthropic compatible APIs."""

from __future__ import annotations

import asyncio
import json
import logging
from enum import Enum
from typing import Optional

import aiohttp

from ..config import settings

log = logging.getLogger("pipeline.llm")


class ModelPurpose(Enum):
    """Model selection by purpose."""
    GENERAL = "general"  # 通用任务（题型检测等）
    PROBLEM_SOLVING = "problem_solving"  # 解题/作图（使用 Claude Opus）


def _get_config_for_purpose(purpose: ModelPurpose) -> tuple[str, str, str]:
    """Get (model, api_key, api_url) for the given purpose."""
    if purpose == ModelPurpose.PROBLEM_SOLVING:
        return (
            settings.problem_solving_model,
            settings.problem_solving_key,
            settings.problem_solving_api_url,
        )
    else:
        return (
            settings.llm_model,
            settings.dashscope_api_key,
            settings.dashscope_api_url,
        )


def _is_anthropic_api(url: str) -> bool:
    """Detect Anthropic-compatible API by URL pattern."""
    return "/anthropic" in url or "anthropic.com" in url


async def call_llm(
    messages: list[dict],
    temperature: float = 0.1,
    max_tokens: int = 16000,
    purpose: ModelPurpose = ModelPurpose.GENERAL,
) -> str:
    """Call chat API with model selected by purpose.

    Args:
        messages: Chat message history
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        purpose: Model purpose (GENERAL or PROBLEM_SOLVING)

    Returns:
        Assistant response content as string.
    """
    model, api_key, api_url = _get_config_for_purpose(purpose)
    use_anthropic = _is_anthropic_api(api_url)

    if use_anthropic:
        return await _call_anthropic(messages, temperature, max_tokens, model, api_key, api_url)
    else:
        return await _call_openai(messages, temperature, max_tokens, model, api_key, api_url)


async def _parse_sse_stream(
    resp: aiohttp.ClientResponse,
    parse_event: callable,
) -> str:
    """Common SSE stream parser for both OpenAI and Anthropic APIs."""
    text_parts: list[str] = []
    buffer = ""
    async for chunk in resp.content.iter_any():
        buffer += chunk.decode("utf-8", errors="replace")
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                event = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            text_chunk, should_stop = parse_event(event)
            if text_chunk:
                text_parts.append(text_chunk)
            if should_stop:
                break
    return "".join(text_parts).strip()


async def _make_request(
    url: str,
    payload: dict,
    headers: dict,
    parse_event: callable,
    api_name: str,
    model: str,
) -> str:
    """Common HTTP request handler with retry logic."""
    timeout = aiohttp.ClientTimeout(total=settings.request_timeout, sock_read=None)

    for attempt in range(1, settings.max_retries + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        raise RuntimeError(f"HTTP {resp.status}: {body[:500]}")

                    result = await _parse_sse_stream(resp, parse_event)

                    if result:
                        log.info("%s (%s) streaming 完成：%d chars", api_name, model, len(result))
                        return result
                    else:
                        raise RuntimeError(f"{api_name} streaming 未返回内容")
        except Exception as exc:
            log.warning("LLM 请求失败 (%d/%d): %s", attempt, settings.max_retries, exc)
            if attempt < settings.max_retries:
                wait = 2 ** attempt
                log.info("等待 %ds 后重试...", wait)
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(f"LLM 请求连续失败 {settings.max_retries} 次") from exc

    return ""


async def _call_openai(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    model: str,
    api_key: str,
    api_url: str,
) -> str:
    """OpenAI-compatible API (DashScope, etc.) — uses streaming."""
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }

    if "qwen3" in model:
        payload["extra_body"] = {"enable_thinking": True}
        log.info("qwen3 模型：启用思考模式")
    else:
        payload["temperature"] = temperature

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    def parse_openai_event(event: dict) -> tuple[Optional[str], bool]:
        choices = event.get("choices", [])
        if not choices:
            return None, False
        delta = choices[0].get("delta", {})
        content = delta.get("content", "")
        return content if content else None, False

    return await _make_request(
        api_url,
        payload,
        headers,
        parse_openai_event,
        "OpenAI",
        model,
    )


async def _call_anthropic(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    model: str,
    api_key: str,
    api_url: str,
) -> str:
    """Anthropic-compatible API — uses streaming."""
    # Extract system message
    system_text = ""
    user_messages = []
    for msg in messages:
        if msg["role"] == "system":
            system_text += msg["content"] + "\n"
        else:
            user_messages.append(msg)

    # Build Anthropic URL — append /v1/messages if needed
    url = api_url.rstrip("/")
    if not url.endswith("/messages"):
        url = url.rstrip("/") + "/v1/messages"

    payload: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": user_messages,
        "stream": True,
    }
    if system_text.strip():
        payload["system"] = system_text.strip()

    headers = {
        "x-api-key": api_key,
        "Authorization": f"Bearer {api_key}",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }

    log.info("Anthropic API (streaming): model=%s, url=%s", model, url)

    def parse_anthropic_event(event: dict) -> tuple[Optional[str], bool]:
        etype = event.get("type", "")
        if etype == "content_block_delta":
            delta = event.get("delta", {})
            if delta.get("type") == "text_delta":
                return delta.get("text", ""), False
        elif etype == "message_stop":
            return None, True
        return None, False

    return await _make_request(
        url,
        payload,
        headers,
        parse_anthropic_event,
        "Anthropic",
        model,
    )
