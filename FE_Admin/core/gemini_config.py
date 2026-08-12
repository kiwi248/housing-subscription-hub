# gemini_config.py
"""Gemini 연동에 필요한 설정을 읽습니다.

키는 코드에 적지 않고 환경 변수나 FE_Admin/.env에서만 읽습니다.
키가 없으면 화면에서 안내만 하고 아무것도 호출하지 않습니다.

FE_Admin에는 원래 python-dotenv가 없어서, 필요한 만큼만 직접 읽습니다.
"""

import os
from pathlib import Path

import streamlit as st

# 이 파일은 FE_Admin/core/gemini_config.py에 있습니다.
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

# 공고 PDF를 읽을 때 쓰는 모델입니다. 필요하면 환경 변수로 바꿉니다.
DEFAULT_MODEL = "gemini-2.5-flash"


def read_env_file(path: Path = ENV_PATH) -> dict[str, str]:
    """.env 파일에서 이름과 값을 읽습니다.

    파일이 없으면 빈 사전입니다. 주석과 빈 줄은 건너뜁니다.
    값의 앞뒤 따옴표는 벗겨 냅니다.
    """

    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return values

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip().strip('"').strip("'")

    return values


def get_setting(name: str, default: str = "") -> str:
    """환경 변수 -> 로컬 .env -> Streamlit Cloud secrets 순으로 찾습니다.

    Streamlit Cloud에 배포하면 로컬 .env 파일이 없고 secrets는
    st.secrets로만 노출되므로, 이 순서로 확인해야 배포 환경에서도
    키를 찾을 수 있습니다.
    """

    value = (os.getenv(name) or "").strip()
    if value:
        return value

    value = read_env_file().get(name, "").strip()
    if value:
        return value

    try:
        return str(st.secrets[name]).strip()
    except Exception:
        return default


def get_api_key() -> str:
    """Gemini API 키를 읽습니다. 없으면 빈 문자열입니다.

    키 값 자체는 화면이나 로그에 절대 출력하지 않습니다.
    """

    return get_setting("GEMINI_API_KEY")


def get_model_name() -> str:
    return get_setting("GEMINI_MODEL", DEFAULT_MODEL)


def has_api_key() -> bool:
    """키가 준비됐는지만 알려 줍니다. 값은 돌려주지 않습니다."""

    return bool(get_api_key())
