"""기존 AI 상담과 분리된 AI 안내원 API입니다."""

from fastapi import APIRouter, Depends

from app.core.api_response import ApiResponse
from app.core.auth_dependency import AuthenticatedUser, get_current_user
from app.schemas.guide_schema import GuideRequest
from app.services.guide_service import create_guide_answer, get_guide_profile


guide_router = APIRouter(prefix="/ai-guide", tags=["AI Guide"])


@guide_router.get("/health")
def health() -> ApiResponse:
    return ApiResponse(
        success=True,
        message="AI 안내원 테스트 API가 실행 중입니다.",
        data={"storage": "session-only"},
    )


@guide_router.get("/me")
def me(user: AuthenticatedUser = Depends(get_current_user)) -> ApiResponse:
    return ApiResponse(
        success=True,
        message="AI 안내원 사용자 정보를 조회했습니다.",
        data=get_guide_profile(user.id, user.email),
    )


@guide_router.post("/message")
def message(
    request: GuideRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ApiResponse:
    answer = create_guide_answer(request.messages, request.question)
    return ApiResponse(success=True, message="AI 안내원 답변을 생성했습니다.", data=answer)
