"""Centralised settings loaded from environment variables."""

from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM - 通用/解题模型
    dashscope_api_key: str
    dashscope_api_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    llm_model: str = "qwen3.5-plus"  # 通用模型（用于题型检测等）

    # LLM - 解题/作图专用模型 (Claude Opus)
    problem_solving_model: str = "claude-opus-4-6"
    problem_solving_api_key: str = ""  # 留空时使用 dashscope_api_key
    problem_solving_api_url: str = "https://api.anthropic.com/v1/messages"

    # TTS
    tts_enabled: bool = True
    tts_api_keys: str = ""  # comma-separated, falls back to dashscope_api_key
    tts_voice: str = "cosyvoice-v3.5-plus-teacher-685fe7cc7c524e40a95be555c3dd2bdb"
    tts_model: str = "cosyvoice-v3.5-plus"
    tts_ws_url: str = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

    # Paths
    lectures_dir: str = "./lectures"
    template_path: str = "./data/template.html"
    teaching_data_dir: str = "./data/teaching_data"

    # Limits
    max_concurrent: int = 3
    request_timeout: int = 300
    max_retries: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def tts_keys(self) -> list[str]:
        if self.tts_api_keys:
            return [k.strip() for k in self.tts_api_keys.split(",") if k.strip()]
        return [self.dashscope_api_key]

    @property
    def problem_solving_key(self) -> str:
        """Get API key for problem solving model."""
        return self.problem_solving_api_key or self.dashscope_api_key


settings = Settings()
