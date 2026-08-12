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
from app.routers.location_router import location_router
from app.routers.profile_router import profile_router

# 이 경로들은 로그 대시보드 자신이 5초마다 계속 호출하는 경로라, 그대로 로그를 남기면
# "대시보드를 보는 행위" 자체가 계속 로그로 찍히는 노이즈가 됩니다. 그래서 기록 대상에서 뺍니다.
EXCLUDED_LOG_PATHS = {"/logs", "/logs/history", "/docs", "/redoc", "/openapi.json"}

# 이 시간(ms)보다 오래 걸리면 2xx 응답이라도 warning으로 기록합니다.
# GET /listings/getall 벤치마크 기준 평상시 최대 응답시간이 약 1.7초였던 것을 감안해
# 여유를 두고 3초로 잡았습니다 (BE/scripts/benchmark_listings.py 참고).
SLOW_RESPONSE_THRESHOLD_MS = 3000


# Swagger 문서(/docs)에 표시할 API 그룹 설명입니다.
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
        "name": "Location",
        "description": "주소 좌표 변환 및 주변 생활권 시설 조회",
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
        "description": "AI 상담 챗봇 - 질의응답, 상담 이력, 상담 요약 저장/조회",
    },
    {
        "name": "AI Guide",
        "description": "AI 안내원 - 세션 내에서만 유지되는 1회성 질의응답",
    },
]

app = FastAPI(
    title="공공임대 청약 통합 안내 서비스",
    openapi_tags=tags_metadata,
)

# Streamlit Cloud(FE_Admin, FE_User)는 백엔드와 다른 도메인에서 API를 호출하므로
# CORS를 허용해야 합니다. ALLOWED_ORIGINS는 쉼표로 구분된 도메인 목록이며,
# 아직 배포 주소를 모르는 개발 단계에서는 기본값 "*"(전체 허용)를 씁니다.
# 쿠키/세션 인증을 쓰지 않는 API라 "*"를 써도 자격 증명이 새는 위험은 없습니다.
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
    """실제로 들어온 요청마다 처리 시간과 결과를 로그로 남깁니다.

    레벨 분류 기준:
      - 5xx 응답        -> error
      - 4xx 응답        -> warning
      - 느린 2xx 응답    -> warning (SLOW_RESPONSE_THRESHOLD_MS 이상)
      - 그 외 2xx 응답   -> info
    """

    if request.url.path in EXCLUDED_LOG_PATHS:
        return await call_next(request)

    screen = f"{request.method} {request.url.path}"
    start = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        # HTTPException/RequestValidationError는 이미 JSONResponse로 바뀌어 여기까지
        # 오지 않습니다. 여기 걸리는 건 정말 처리되지 않은 버그성 예외이므로 기록해 둡니다.
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
app.include_router(location_router)
app.include_router(chat_router)
app.include_router(guide_router)