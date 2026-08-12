"""TCP/TLS Redis 연결과 AI 상담 기록 설정을 제공합니다."""

from __future__ import annotations

from functools import lru_cache

from app.core.gemini_config import get_chat_setting


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = get_chat_setting(name, str(default))
    try:
        return max(minimum, min(int(raw_value), maximum))
    except ValueError as error:
        raise RuntimeError(f"{name}는 정수여야 합니다.") from error


def get_chat_history_ttl() -> int:
    """마지막 저장 시점부터 기록을 유지할 시간(초)을 반환합니다."""

    return _bounded_int("CHAT_HISTORY_TTL_SECONDS", 3600, 60, 86400)


def get_chat_history_max_messages() -> int:
    return _bounded_int("CHAT_HISTORY_MAX_MESSAGES", 30, 2, 100)


@lru_cache(maxsize=1)
def get_redis():
    """REDIS_URL이 준비된 뒤에만 TCP/TLS 클라이언트를 생성합니다."""

    url = get_chat_setting("REDIS_URL")
    if not url or "your-" in url:
        raise RuntimeError("Redis TCP 연결 URL이 설정되어 있지 않습니다.")
    if not url.startswith(("redis://", "rediss://")):
        raise RuntimeError("REDIS_URL은 redis:// 또는 rediss:// 형식이어야 합니다.")

    import redis

    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
