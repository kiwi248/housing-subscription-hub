"""AI 상담 전용 클라이언트입니다."""

from __future__ import annotations

from typing import Any

import httpx

from core.api_client import BACKEND_URL


CHAT_REQUEST_TIMEOUT = 45.0


class ChatAPIError(Exception):
    """AI 상담 API 호출 중 사용자에게 안내할 수 있는 오류입니다."""


def get_chat_backend_url() -> str:
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
            f"{get_chat_backend_url()}{path}",
            headers=headers,
            json=json,
            timeout=CHAT_REQUEST_TIMEOUT,
        )
    except httpx.TimeoutException as error:
        raise ChatAPIError("AI 상담 응답 시간이 초과되었습니다.") from error
    except httpx.RequestError as error:
        raise ChatAPIError("AI 상담 테스트 백엔드에 연결할 수 없습니다.") from error

    try:
        payload = response.json()
    except ValueError as error:
        raise ChatAPIError("AI 상담 백엔드가 올바른 응답을 반환하지 않았습니다.") from error

    if response.is_error:
        message = payload.get("message") or "AI 상담 요청에 실패했습니다."
        raise ChatAPIError(f"{message} ({response.status_code})")
    return payload


def get_chat_profile(access_token: str) -> dict:
    return _request("GET", "/chat/me", access_token)


def get_chat_history(access_token: str) -> dict:
    return _request("GET", "/chat/history", access_token)


def delete_chat_history(access_token: str) -> dict:
    return _request("DELETE", "/chat/history", access_token)


def send_chat_message(question: str, access_token: str) -> dict:
    return _request(
        "POST",
        "/chat/message",
        access_token,
        json={"question": question},
    )


def save_chat_summary(access_token: str) -> dict:
    return _request(
        "POST",
        "/chat/save",
        access_token,
        json={},
    )


def get_chat_summaries(access_token: str) -> dict:
    return _request("GET", "/chat/summaries", access_token)


def delete_chat_summary(summary_id: str, access_token: str) -> dict:
    return _request("DELETE", f"/chat/summaries/{summary_id}", access_token)
