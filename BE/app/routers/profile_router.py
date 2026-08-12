# profile_router.py
from fastapi import APIRouter, HTTPException

from app.core.api_response import ApiResponse
from app.schemas.profile_schema import ProfileUpdate
from app.services.profile_service import profile_get, profile_update

profile_router = APIRouter(prefix="/profiles", tags=["Profile"])

# 200: 정상 - 정상 실행 되면 자동 전송
# 404: 데이터 없음

# 1. mypage 프로필 조회
@profile_router.get("/{user_id}")
def get(user_id: str) -> ApiResponse:
    profile = profile_get(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
    return ApiResponse(
        success=True,
        message="프로필을 조회했습니다.",
        data=profile,
    )


# 2. mypage 닉네임 수정
@profile_router.put("/{user_id}")
def update(user_id: str, profile: ProfileUpdate) -> ApiResponse:
    updated_profile = profile_update(user_id, profile)
    if updated_profile is None:
        raise HTTPException(status_code=404, detail="프로필을 찾을 수 없습니다.")
    return ApiResponse(
        success=True,
        message="프로필을 수정했습니다.",
        data=updated_profile,
    )
