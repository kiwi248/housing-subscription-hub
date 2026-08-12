"""최신 app/main.py 구조에 AI 상담 라우터만 추가한 통합 테스트 서버입니다.

실제 app/main.py는 수정하지 않습니다. 이 파일은 8010 포트에서 기존 API와
AI 상담 API가 함께 동작하는지 확인할 때 사용합니다.
"""

import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.log_store import add_log
from app.exceptions.handlers import register_exception_handlers
from app.routers.admin_router import admin_router
from app.routers.chat_router import chat_router
from app.routers.favorite_router import favorite_router
from app.routers.guide_router import guide_router
from app.routers.listing_router import listing_router
from app.routers.log_router import log_router
from app.routers.profile_router import profile_router


EXCLUDED_LOG_PATHS = {"/logs", "/logs/history", "/docs", "/redoc", "/openapi.json"}
SLOW_RESPONSE_THRESHOLD_MS = 3000


tags_metadata = [
    {
        "name": "Admin",
        "description": "관리자 로그인, 청약정보 등록/삭제, 즐겨찾기 현황 조회",
    },
    {
        "name": "Profile",
        "description": "mypage 프로필(닉네임) 조회/수정. 회원가입·로그인은 Supabase Auth가 처리합니다.",
    },
    {
        "name": "Listing",
        "description": "청약정보 조회 및 조건검색",
    },
    {
        "name": "Favorite",
        "description": "mypage 즐겨찾기 등록/조회/삭제",
    },
    {
        "name": "Log",
        "description": "실시간 요청 로그 조회 API (메모리 buffer + warning/error는 Supabase에도 저장)",
    },
    {
        "name": "Chat",
        "description": "로그인 사용자의 Gemini 상담, 요약 저장 및 조회",
    },
    {
        "name": "AI Guide",
        "description": "프로젝트 사용법과 간단한 청약 용어를 안내하는 독립 AI 안내원",
    },
]

app = FastAPI(
    title="공공임대 청약 통합 안내 서비스 - AI 통합 테스트",
    openapi_tags=tags_metadata,
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """최신 실제 앱과 같은 기준으로 테스트 요청 로그를 기록합니다."""

    if request.url.path in EXCLUDED_LOG_PATHS:
        return await call_next(request)

    screen = f"{request.method} {request.url.path}"
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        latency_ms = int((time.perf_counter() - start) * 1000)
        add_log("error", screen, "처리되지 않은 예외 발생", latency_ms)
        raise

    latency_ms = int((time.perf_counter() - start) * 1000)
    status_code = response.status_code

    if status_code >= 500:
        level = "error"
        message = f"서버 오류 ({status_code})"
    elif status_code >= 400:
        level = "warning"
        message = f"클라이언트 오류 ({status_code})"
    elif latency_ms >= SLOW_RESPONSE_THRESHOLD_MS:
        level = "warning"
        message = "느린 응답 감지"
    else:
        level = "info"
        message = "정상 처리"

    add_log(level, screen, message, latency_ms)
    return response


register_exception_handlers(app)

app.include_router(admin_router)
app.include_router(profile_router)
app.include_router(listing_router)
app.include_router(favorite_router)
app.include_router(log_router)
app.include_router(chat_router)
app.include_router(guide_router)
