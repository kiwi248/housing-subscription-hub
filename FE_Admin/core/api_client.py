"""모든 메뉴 API에서 공통으로 사용하는 HTTP 요청 기능."""

from typing import Any

import httpx
import streamlit as st


def _get_backend_url() -> str:
    """배포 환경(Streamlit Cloud)에서는 secrets의 BACKEND_URL을 쓰고,
    로컬 개발 환경(secrets 미설정)에서는 로컬 백엔드 주소를 씁니다.
    """

    try:
        return st.secrets["BACKEND_URL"]
    except Exception:
        return "http://127.0.0.1:8000"


BACKEND_URL = _get_backend_url()
REQUEST_TIMEOUT = 15.0

# 사진을 올릴 때만 쓰는 시간 제한입니다.
# 사진 20장이면 수십 MB라 15초 안에 다 보내지 못합니다.
UPLOAD_TIMEOUT = 180.0


class BackendAPIError(Exception):
    """백엔드 연결 또는 API 응답 처리 중 발생한 오류입니다."""


def request(
    method: str,
    path: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    # 같은 이름으로 여러 개를 보낼 때는 (이름, 값) 목록으로 넘깁니다.
    # 사진 여러 장을 올릴 때 files가 그런 모양이 됩니다.
    files: Any = None,
    data: Any = None,
    timeout: float | None = None,
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
            files=files,
            data=data,
            timeout=timeout or REQUEST_TIMEOUT,
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
