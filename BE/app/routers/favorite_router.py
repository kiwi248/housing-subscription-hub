# favorite_router.py
from fastapi import APIRouter, HTTPException

from app.core.api_response import ApiResponse
from app.schemas.favorite_schema import FavoriteCreate
from app.services.favorite_service import (
    favorite_create,
    favorite_delete,
    favorite_get_by_user_and_listing,
    favorite_get_mypage,
)

favorite_router = APIRouter(prefix="/favorites", tags=["Favorite"])

# 200: 정상 - 정상 실행 되면 자동 전송
# 404: 데이터 없음
# 409: 중복 즐겨찾기
# 500: 서버 또는 DB 처리 실패

@favorite_router.post("/create")
def create(favorite: FavoriteCreate) -> ApiResponse:
    if favorite_get_by_user_and_listing(favorite.user_id, favorite.listing_id):
        raise HTTPException(status_code=409, detail="이미 즐겨찾기한 청약정보입니다.")

    created_favorite = favorite_create(favorite)
    if created_favorite is None:
        raise HTTPException(status_code=500, detail="즐겨찾기 등록에 실패했습니다.")
    return ApiResponse(
        success=True,
        message="즐겨찾기에 등록되었습니다.",
        data=created_favorite,
    )


# 2. mypage 즐겨찾기 조회
@favorite_router.get("/mypage/{user_id}")
def mypage(user_id: str) -> ApiResponse:
    favorites = favorite_get_mypage(user_id)
    return ApiResponse(
        success=True,
        message="즐겨찾기 목록을 조회했습니다.",
        data=favorites,
    )


# 3. mypage 즐겨찾기 삭제
@favorite_router.delete("/delete/{user_id}/{listing_id}")
def delete(user_id: str, listing_id: int) -> ApiResponse:
    current_favorite = favorite_get_by_user_and_listing(user_id, listing_id)
    if current_favorite is None:
        raise HTTPException(status_code=404, detail="즐겨찾기를 찾을 수 없습니다.")

    deleted_favorite = favorite_delete(user_id, listing_id)
    if deleted_favorite is None:
        raise HTTPException(status_code=500, detail="즐겨찾기 삭제에 실패했습니다.")
    return ApiResponse(
        success=True,
        message="즐겨찾기가 삭제되었습니다.",
        data=deleted_favorite,
    )
