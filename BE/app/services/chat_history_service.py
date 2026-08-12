"""로그인 사용자별 진행 중인 AI 상담을 Upstash Redis에 보관합니다."""

from __future__ import annotations

import json

from fastapi import HTTPException, status

from app.core.redis_config import (
    get_chat_history_max_messages,
    get_chat_history_ttl,
    get_redis,
)
from app.schemas.chat_schema import ChatMessage


def _history_key(user_id: str) -> str:
    return f"ai-chat:active:{user_id}"


def _storage_error(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="현재 대화 기록 저장소에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    )


def get_chat_history(user_id: str, redis_client=None) -> list[ChatMessage]:
    try:
        client = redis_client or get_redis()
        raw_history = client.get(_history_key(user_id))
        if not raw_history:
            return []
        rows = json.loads(raw_history) if isinstance(raw_history, str) else raw_history
        return [ChatMessage.model_validate(row) for row in rows]
    except HTTPException:
        raise
    except Exception as error:
        raise _storage_error(error) from error


def save_chat_history(
    user_id: str,
    messages: list[ChatMessage],
    redis_client=None,
) -> list[ChatMessage]:
    selected = messages[-get_chat_history_max_messages() :]
    payload = json.dumps(
        [message.model_dump() for message in selected],
        ensure_ascii=False,
    )
    try:
        client = redis_client or get_redis()
        client.set(
            _history_key(user_id),
            payload,
            ex=get_chat_history_ttl(),
        )
    except Exception as error:
        raise _storage_error(error) from error
    return selected


def append_chat_exchange(
    user_id: str,
    question: str,
    answer: str,
    redis_client=None,
) -> list[ChatMessage]:
    try:
        client = redis_client or get_redis()
        history = get_chat_history(user_id, client)
        history.extend(
            [
                ChatMessage(role="user", content=question),
                ChatMessage(role="assistant", content=answer),
            ]
        )
        return save_chat_history(user_id, history, client)
    except HTTPException:
        raise
    except Exception as error:
        raise _storage_error(error) from error


def delete_chat_history(user_id: str, redis_client=None) -> None:
    try:
        client = redis_client or get_redis()
        client.delete(_history_key(user_id))
    except Exception as error:
        raise _storage_error(error) from error
