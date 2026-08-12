# log_router.py
from fastapi import APIRouter, Query

from app.core.api_response import ApiResponse
from app.services.log_service import log_history, log_list

log_router = APIRouter(prefix="/logs", tags=["Log"])

# 200: 정상 - 정상 실행 되면 자동 전송

# 1. 최근 로그 조회 (메모리 buffer, level 필터)
@log_router.get("")
def get_recent_logs(
    level: str | None = Query(default=None, examples=["info", "warning", "error"]),
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse:
    logs = log_list(level=level, limit=limit)
    return ApiResponse(
        success=True,
        message="로그를 조회했습니다.",
        data=logs,
    )


# 2. warning/error 로그 이력 조회 (Supabase logs 테이블)
@log_router.get("/history")
def get_log_history(
    level: str | None = Query(default=None, examples=["all", "warning", "error"]),
    limit: int = Query(default=50, ge=1, le=200),
) -> ApiResponse:
    logs = log_history(level=level, limit=limit)
    return ApiResponse(
        success=True,
        message="저장된 로그 이력을 조회했습니다.",
        data=logs,
    )
