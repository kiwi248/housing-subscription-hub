"""백엔드(FastAPI) API에서 공통으로 사용하는 HTTP 요청 기능입니다."""
import os
from pathlib import Path
from typing import Any

import httpx
import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

def _get_backend_url() -> str:
    """로컬 .env를 먼저 확인하고, 없으면 배포 secrets를 읽습니다."""

    load_dotenv(ENV_PATH)

    backend_url = os.getenv("BACKEND_URL", "").strip()

    if backend_url:
        return backend_url.rstrip("/")

    # 로컬 .env 파일이 존재하면 로컬 백엔드 기본 주소를 사용합니다.
    # 이때 st.secrets에 접근하지 않아 불필요한 경고를 막습니다.
    if ENV_PATH.exists():
        return "http://127.0.0.1:8000"

    try:
        backend_url = str(
            st.secrets["BACKEND_URL"]
        ).strip()
    except Exception:
        backend_url = ""

    return (
        backend_url.rstrip("/")
        or "http://127.0.0.1:8000"
    )


BACKEND_URL = _get_backend_url()
REQUEST_TIMEOUT = 15.0


class BackendAPIError(Exception):
    """백엔드 연결 또는 API 응답 처리 중 발생한 오류입니다."""


def request(
    method: str,
    path: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
):
    if params is not None:
        # httpx가 None 값을 빈 문자열로 보내면 백엔드 쿼리 파라미터 검증이 실패하므로 제거합니다.
        params = {key: value for key, value in params.items() if value is not None}

    try:
        response = httpx.request(
            method,
            f"{BACKEND_URL}{path}",
            json=json,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.TimeoutException as error:
        raise BackendAPIError("백엔드 응답 시간이 초과되었습니다.") from error
    except httpx.RequestError as error:
        raise BackendAPIError(
            "백엔드 서버에 연결할 수 없습니다. 서버 실행 상태를 확인해 주세요."
        ) from error

    try:
        payload = response.json()
    except ValueError as error:
        raise BackendAPIError("백엔드가 올바른 JSON을 반환하지 않았습니다.") from error

    if response.is_error:
        # 백엔드는 {"success": false, "message": "..."} 형태로 오류를 내려줍니다.
        message = payload.get("message") or "요청에 실패했습니다."
        raise BackendAPIError(f"{message} ({response.status_code})")

    return payload
