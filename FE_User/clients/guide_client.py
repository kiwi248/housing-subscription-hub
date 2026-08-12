"""기존 AI 상담과 분리된 AI 안내원 전용 클라이언트입니다."""

from __future__ import annotations

from typing import Any

import httpx

from core.api_client import BACKEND_URL


GUIDE_REQUEST_TIMEOUT = 45.0


class GuideAPIError(Exception):
    """AI 안내원 API 호출 오류입니다."""


def get_guide_backend_url() -> str:
    return BACKEND_URL


def _request(
    method: str,
    path: str,
    access_token: str,
    json: dict[str, Any] | None = None,
) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = httpx.request(
            method,
            f"{get_guide_backend_url()}{path}",
            headers=headers,
            json=json,
            timeout=GUIDE_REQUEST_TIMEOUT,
        )
    except httpx.TimeoutException as error:
        raise GuideAPIError("AI 안내원 응답 시간이 초과되었습니다.") from error
    except httpx.RequestError as error:
        raise GuideAPIError("AI 안내원 테스트 백엔드에 연결할 수 없습니다.") from error

    try:
        payload = response.json()
    except ValueError as error:
        raise GuideAPIError("AI 안내원 백엔드가 올바른 응답을 반환하지 않았습니다.") from error

    if response.is_error:
        message = payload.get("message") or "AI 안내원 요청에 실패했습니다."
        raise GuideAPIError(f"{message} ({response.status_code})")
    return payload


def get_guide_profile(access_token: str) -> dict:
    return _request("GET", "/ai-guide/me", access_token)


def send_guide_message(question: str, messages: list[dict], access_token: str) -> dict:
    return _request(
        "POST",
        "/ai-guide/message",
        access_token,
        json={"question": question, "messages": messages},
    )
