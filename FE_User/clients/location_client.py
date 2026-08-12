"""사용자 화면에서 백엔드 위치 API를 호출하는 클라이언트입니다."""

from core.api_client import request


def geocode_location(query: str):
    """주소 또는 장소명을 위도와 경도로 변환합니다."""

    return request(
        "GET",
        "/locations/geocode",
        params={
            "address": query,
        },
    )


def get_nearby_subways(
    latitude: float,
    longitude: float,
    radius_m: int = 2000,
    limit: int = 3,
):
    """주어진 좌표 주변의 가까운 지하철역을 조회합니다."""

    return request(
        "GET",
        "/locations/nearby-subways",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_m,
            "limit": limit,
        },
    )


def get_nearby_facilities(
    latitude: float,
    longitude: float,
    radius_m: int = 2000,
    limit: int = 3,
):
    """주변 지하철역·마트·병원을 함께 조회합니다."""

    return request(
        "GET",
        "/locations/nearby-facilities",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_m,
            "limit": limit,
        },
    )