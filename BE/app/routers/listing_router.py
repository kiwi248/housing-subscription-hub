# listing_router.py
from fastapi import APIRouter, HTTPException, Query

from app.core.api_response import ApiResponse
from app.services.listing_service import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    SORT_COLUMNS,
    is_known_sort,
    listing_get,
    listing_get_all,
    listing_get_page,
    listing_search,
)

listing_router = APIRouter(prefix="/listings", tags=["Listing"])

# 200: 정상 - 정상 실행 되면 자동 전송
# 400: 모르는 정렬 기준
# 404: 데이터 없음


def check_sort(sort: str | None) -> str | None:
    """모르는 정렬 기준이 들어오면 조용히 넘기지 않고 알려 줍니다.

    잘못 적은 이름을 그냥 무시하면 왜 순서가 안 바뀌는지 알기 어렵습니다.
    """

    if sort is None or is_known_sort(sort):
        return sort
    raise HTTPException(
        status_code=400,
        detail=f"정렬 기준 '{sort}'을(를) 알 수 없습니다. 가능한 값: {', '.join(SORT_COLUMNS)}",
    )


# 1. 전체 조회
@listing_router.get("/getall")
def get_all(sort: str | None = Query(default=None)) -> ApiResponse:
    listings = listing_get_all(sort=check_sort(sort))
    return ApiResponse(
        success=True,
        message="청약정보 목록을 조회했습니다.",
        data=listings,
    )


# 2. 페이지 조회 (등록이 최신인 순서)
#    기존 /getall은 사용자 화면과 벤치마크 스크립트가 쓰고 있어 그대로 두고,
#    페이지가 필요한 화면만 이 경로를 씁니다.
@listing_router.get("/page")
def get_page(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    sort: str | None = Query(default=None),
) -> ApiResponse:
    listing_page = listing_get_page(
        page=page, page_size=page_size, sort=check_sort(sort)
    )
    return ApiResponse(
        success=True,
        message="청약정보 목록을 조회했습니다.",
        data=listing_page,
    )


# 3. 조건검색 (최신순, 위치, 최대 보증금, 최대 월세)
@listing_router.get("/search")
def search(
    location: str | None = Query(default=None),
    max_deposit: int | None = Query(default=None, ge=0),
    max_monthly_rent: int | None = Query(default=None, ge=0),
    sort: str | None = Query(default=None),
) -> ApiResponse:
    listings = listing_search(
        location=location,
        max_deposit=max_deposit,
        max_monthly_rent=max_monthly_rent,
        sort=check_sort(sort),
    )
    return ApiResponse(
        success=True,
        message="청약정보 검색에 성공했습니다.",
        data=listings,
    )


# 4. 한개 조회
@listing_router.get("/get/{listing_id}")
def get(listing_id: int) -> ApiResponse:
    listing = listing_get(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail=f"청약정보 ID {listing_id}를 찾을 수 없습니다.")
    return ApiResponse(
        success=True,
        message="청약정보를 조회했습니다.",
        data=listing,
    )
