from fastapi import APIRouter, Query

from app.core.api_response import ApiResponse
from app.services.location_service import (
    find_nearby_living_facilities,
    find_nearby_subway_stations,
    geocode_address,
)


location_router = APIRouter(
    prefix="/locations",
    tags=["Location"],
)


@location_router.get("/geocode")
def geocode(
    address: str = Query(
        min_length=2,
        max_length=255,
        examples=["서울특별시 중구 세종대로 110"],
    ),
) -> ApiResponse:
    """입력한 주소를 위도와 경도로 변환합니다."""

    result = geocode_address(address)

    return ApiResponse(
        success=True,
        message="주소를 좌표로 변환했습니다.",
        data=result,
    )


@location_router.get("/nearby-subways")
def nearby_subways(
    latitude: float = Query(
        ge=-90,
        le=90,
        examples=[37.566370776634],
    ),
    longitude: float = Query(
        ge=-180,
        le=180,
        examples=[126.977918351844],
    ),
    radius_m: int = Query(
        default=2000,
        ge=100,
        le=20000,
        examples=[2000],
    ),
    limit: int = Query(
        default=3,
        ge=1,
        le=15,
        examples=[3],
    ),
) -> ApiResponse:
    """입력한 좌표 주변의 가까운 지하철역을 조회합니다."""

    stations = find_nearby_subway_stations(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        limit=limit,
    )

    return ApiResponse(
        success=True,
        message="주변 지하철역을 조회했습니다.",
        data=stations,
    )


@location_router.get("/nearby-facilities")
def nearby_facilities(
    latitude: float = Query(
        ge=-90,
        le=90,
        examples=[37.566370776634],
    ),
    longitude: float = Query(
        ge=-180,
        le=180,
        examples=[126.977918351844],
    ),
    radius_m: int = Query(
        default=2000,
        ge=100,
        le=20000,
        examples=[2000],
    ),
    limit: int = Query(
        default=3,
        ge=1,
        le=15,
        examples=[3],
    ),
) -> ApiResponse:
    """입력한 좌표 주변의 지하철역·마트·병원을 조회합니다."""

    facilities = find_nearby_living_facilities(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        limit=limit,
    )

    return ApiResponse(
        success=True,
        message="주변 생활권 시설을 조회했습니다.",
        data=facilities,
    )