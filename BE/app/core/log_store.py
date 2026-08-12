# log_store.py
"""실시간 로그를 메모리에 저장하는 buffer입니다.

collections.deque(maxlen=N)에 최근 로그만 들고 있다가 대시보드 폴링에 응답합니다.
서버가 재시작되면 buffer는 사라집니다. 다만 warning/error 로그는 나중에 다시 볼 수 있도록
Supabase logs 테이블에도 남깁니다 (info는 메모리에만 유지).

로그는 app/main.py의 요청 로깅 미들웨어가 실제 요청을 처리할 때마다 add_log()를
호출해서 쌓입니다 (가짜로 생성하는 시뮬레이터는 쓰지 않습니다).
"""

import threading
from collections import deque
from datetime import datetime, timezone

from app.core.supabase_config import get_supabase

MAX_LOGS = 200

# DB에 영구 저장할 레벨입니다. info는 양이 많고 다시 볼 필요가 적어 메모리에만 둡니다.
DB_PERSIST_LEVELS = {"warning", "error"}

# 여러 요청이 동시에 buffer를 건드릴 수 있으므로 lock으로 한 번에 하나씩만 접근합니다.
_log_buffer: deque[dict] = deque(maxlen=MAX_LOGS)
_lock = threading.Lock()


def add_log(level: str, screen: str, message: str, latency_ms: int) -> None:
    """로그 한 줄을 buffer에 추가합니다. warning/error는 DB에도 저장합니다."""

    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "screen": screen,
        "message": message,
        "latency_ms": latency_ms,
    }
    with _lock:
        _log_buffer.append(entry)

    if level in DB_PERSIST_LEVELS:
        _save_to_db(entry)


def _save_to_db(entry: dict) -> None:
    """warning/error 로그를 Supabase logs 테이블에 저장합니다.

    요청을 처리하는 도중에 호출되므로, DB 저장이 실패해도(Supabase 설정 누락,
    네트워크 오류 등) 예외를 밖으로 던지지 않고 무시합니다 — 로그 저장 실패 때문에
    정작 유저의 원래 요청 응답이 실패하면 안 됩니다.
    """

    try:
        get_supabase().table("logs").insert(entry).execute()
    except Exception as error:
        print(f"[log_store] Supabase 저장 실패: {error}")


def get_logs(level: str | None, limit: int) -> list[dict]:
    """buffer에서 최근 로그를 최신순으로 가져옵니다."""

    with _lock:
        logs = list(_log_buffer)

    if level and level != "all":
        logs = [log for log in logs if log["level"] == level]

    # deque는 오래된 순서로 쌓이므로, 최신 로그가 먼저 오도록 뒤집습니다.
    logs.reverse()
    return logs[:limit]
