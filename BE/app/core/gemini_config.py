"""Gemini 설정과 클라이언트를 챗봇 호출 시점에 준비합니다.

기존 FastAPI 기능은 Gemini 설정이 없어도 계속 실행될 수 있도록 import 시점에는
API key를 검사하지 않습니다. 로컬 화면 검증은 CHAT_GEMINI_MODE=mock으로 동작합니다.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BE_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = BE_ROOT / ".env"


def get_chat_setting(name: str, default: str = "") -> str:
    load_dotenv(ENV_PATH)
    return os.getenv(name, default).strip()


def get_gemini_mode() -> str:
    """mock 또는 gemini 중 현재 실행 모드를 반환합니다."""

    mode = get_chat_setting("CHAT_GEMINI_MODE", "mock").lower()
    if mode not in {"mock", "gemini"}:
        raise RuntimeError("CHAT_GEMINI_MODE는 mock 또는 gemini여야 합니다.")
    return mode


def get_gemini_model() -> str:
    return get_chat_setting("GEMINI_MODEL", "gemini-2.5-flash-lite")


def get_history_limit() -> int:
    raw_value = get_chat_setting("CHAT_HISTORY_LIMIT", "10")
    try:
        return max(0, min(int(raw_value), 30))
    except ValueError as error:
        raise RuntimeError("CHAT_HISTORY_LIMIT는 정수여야 합니다.") from error


def get_gemini_client():
    """실제 Gemini 모드에서만 API key를 검사하고 클라이언트를 만듭니다."""

    api_key = get_chat_setting("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your-"):
        raise RuntimeError("GEMINI_API_KEY가 설정되어 있지 않습니다.")

    from google import genai

    return genai.Client(api_key=api_key)
