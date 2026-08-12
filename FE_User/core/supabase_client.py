"""Supabase Auth(회원가입/로그인) 연결을 만드는 공통 helper입니다.

회원가입, 로그인, 로그아웃은 백엔드를 거치지 않고 Supabase Auth에 바로 요청합니다.
프런트엔드 코드이므로 반드시 anon(publishable) key만 사용합니다.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"


def get_required_env(name: str) -> str:
    """로컬 .env를 먼저 확인하고, 없으면 배포 secrets를 읽습니다."""

    load_dotenv(ENV_PATH)

    value = os.getenv(name, "")

    if not value:
        try:
            value = st.secrets[name]
        except Exception:
            value = ""

    value = (value or "").strip()

    if not value:
        raise RuntimeError(
            f"{name} 값이 없습니다. "
            f"로컬은 {ENV_PATH}, "
            "배포 환경은 Streamlit Cloud secrets를 확인하세요."
        )

    if value.startswith(("your-", "https://your-")):
        raise RuntimeError(
            f"{name} 값이 예시 값입니다. "
            "Supabase Dashboard에서 실제 값을 복사해 넣어 주세요."
        )

    return value


def get_supabase() -> Client:
    """검증된 URL과 anon key로 프런트엔드용 Supabase 클라이언트를 만듭니다."""

    url = get_required_env("SUPABASE_URL")
    anon_key = get_required_env("SUPABASE_ANON_KEY")
    return create_client(url, anon_key)
