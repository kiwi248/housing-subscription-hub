# log_service.py
from app.core.log_store import get_logs
from app.core.supabase_config import get_supabase
from app.schemas.log_schema import LogEntry, LogHistoryEntry

# DB에는 warning/error만 저장되므로, 이 두 값만 조회 대상으로 허용합니다.
HISTORY_LEVELS = ("warning", "error")


def log_list(level: str | None, limit: int) -> list[LogEntry]:
    """메모리 buffer에서 최근 로그를 조회해 응답 모델로 바꿉니다."""

    logs = get_logs(level=level, limit=limit)
    return [LogEntry.model_validate(log) for log in logs]


def log_history(level: str | None, limit: int) -> list[LogHistoryEntry]:
    """Supabase logs 테이블에서 warning/error 이력을 조회합니다."""

    query = (
        get_supabase()
        .table("logs")
        .select("*")
        .order("time", desc=True)
        .limit(limit)
    )

    if level and level != "all":
        query = query.eq("level", level)
    else:
        query = query.in_("level", HISTORY_LEVELS)

    result = query.execute()
    return [LogHistoryEntry.model_validate(row) for row in result.data]
