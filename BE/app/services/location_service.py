import math
import os
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

from app.schemas.location_schema import (GeocodeResult, NearbyFacilities, NearbyFacility, NearbyStation)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

KAKAO_ADDRESS_SEARCH_URL = (
    "https://dapi.kakao.com/v2/local/search/address.json"
)
KAKAO_KEYWORD_SEARCH_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)
KAKAO_CATEGORY_SEARCH_URL = (
    "https://dapi.kakao.com/v2/local/search/category.json"
)
REQUEST_TIMEOUT = 10.0


FacilityCategory = Literal["subway", "mart", "hospital"]

FACILITY_CATEGORY_CODES: dict[FacilityCategory, str] = {
    "subway": "SW8",
    "mart": "MT1",
    "hospital": "HP8",
}

FACILITY_CATEGORY_LABELS: dict[FacilityCategory, str] = {
    "subway": "지하철역",
    "mart": "마트",
    "hospital": "병원",
}


def get_kakao_api_key() -> str:
    """환경변수에서 Kakao REST API 키를 읽습니다."""

    load_dotenv(ENV_PATH)

    api_key = os.getenv("KAKAO_REST_API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Kakao REST API 키가 설정되지 않았습니다.",
        )

    return api_key


def request_kakao(
    url: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Kakao 위치 API에 요청하고 JSON 응답을 반환합니다."""

    headers = {
        "Authorization": f"KakaoAK {get_kakao_api_key()}",
    }

    try:
        response = httpx.get(
            url,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.TimeoutException as error:
        raise HTTPException(
            status_code=504,
            detail="위치 검색 응답 시간이 초과되었습니다.",
        ) from error
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="위치 검색 서버에 연결할 수 없습니다.",
        ) from error

    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=500,
            detail="Kakao API 설정을 확인해 주세요.",
        )

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail="위치 검색 중 외부 API 오류가 발생했습니다.",
        )

    try:
        payload = response.json()
    except ValueError as error:
        raise HTTPException(
            status_code=502,
            detail="위치 검색 서버가 올바른 응답을 반환하지 않았습니다.",
        ) from error

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail="위치 검색 응답 형식이 올바르지 않습니다.",
        )

    return payload


def make_geocode_result(
    document: dict[str, Any],
    original_query: str,
    matched_by: Literal["address", "keyword"],
) -> GeocodeResult:
    """Kakao 검색 결과 한 건을 공통 좌표 모델로 변환합니다."""

    if matched_by == "address":
        road_address = document.get("road_address") or {}
        basic_address = document.get("address") or {}

        normalized_address = (
            road_address.get("address_name")
            or basic_address.get("address_name")
            or document.get("address_name")
            or original_query
        )
    else:
        normalized_address = (
            document.get("road_address_name")
            or document.get("address_name")
            or document.get("place_name")
            or original_query
        )

    try:
        return GeocodeResult(
            address=normalized_address,
            latitude=float(document["y"]),
            longitude=float(document["x"]),
            matched_by=matched_by,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="위치 검색 결과에서 좌표를 확인할 수 없습니다.",
        ) from error


def geocode_address(address: str) -> GeocodeResult:
    """Kakao에서 주소를 좌표로 변환하고, 실패하면 장소명으로 재검색합니다."""

    address = address.strip()

    if not address:
        raise HTTPException(
            status_code=400,
            detail="주소 또는 장소명을 입력해 주세요.",
        )

    address_payload = request_kakao(
        KAKAO_ADDRESS_SEARCH_URL,
        params={"query": address},
    )
    address_documents = address_payload.get("documents") or []

    if address_documents:
        return make_geocode_result(
            document=address_documents[0],
            original_query=address,
            matched_by="address",
        )

    keyword_payload = request_kakao(
        KAKAO_KEYWORD_SEARCH_URL,
        params={
            "query": address,
            "size": 1,
        },
    )
    keyword_documents = keyword_payload.get("documents") or []

    if keyword_documents:
        return make_geocode_result(
            document=keyword_documents[0],
            original_query=address,
            matched_by="keyword",
        )

    raise HTTPException(
        status_code=404,
        detail=(
            "입력한 주소 또는 장소를 찾을 수 없습니다. "
            "도로명 주소, 건물명 또는 아파트명을 확인해 주세요."
        ),
    )


def estimate_walking_minutes(distance_m: int) -> int:
    """직선거리에 경로 보정값과 평균 보행속도를 적용해 도보시간을 추정합니다."""

    route_factor = 1.25
    walking_speed_m_per_minute = 75

    estimated_route_distance = distance_m * route_factor
    estimated_minutes = math.ceil(
        estimated_route_distance / walking_speed_m_per_minute
    )

    return max(1, estimated_minutes)


def validate_search_options(
    latitude: float,
    longitude: float,
    radius_m: int,
    limit: int,
) -> None:
    """주변 시설 검색에 사용하는 좌표와 검색 조건을 확인합니다."""

    if not -90 <= latitude <= 90:
        raise HTTPException(
            status_code=400,
            detail="위도 값이 올바르지 않습니다.",
        )

    if not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=400,
            detail="경도 값이 올바르지 않습니다.",
        )

    if not 100 <= radius_m <= 20000:
        raise HTTPException(
            status_code=400,
            detail="검색 반경은 100m 이상 20km 이하여야 합니다.",
        )

    if not 1 <= limit <= 15:
        raise HTTPException(
            status_code=400,
            detail="조회 개수는 1개 이상 15개 이하여야 합니다.",
        )


def find_nearby_facilities(
    category: FacilityCategory,
    latitude: float,
    longitude: float,
    radius_m: int = 2000,
    limit: int = 3,
) -> list[NearbyFacility]:
    """Kakao 카테고리 코드로 좌표 주변 시설을 검색해 거리순으로 반환합니다."""

    validate_search_options(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        limit=limit,
    )

    category_code = FACILITY_CATEGORY_CODES[category]
    category_label = FACILITY_CATEGORY_LABELS[category]

    payload = request_kakao(
        KAKAO_CATEGORY_SEARCH_URL,
        params={
            "category_group_code": category_code,
            "x": longitude,
            "y": latitude,
            "radius": radius_m,
            "sort": "distance",
            "size": limit,
        },
    )

    documents = payload.get("documents") or []
    facilities: list[NearbyFacility] = []

    for document in documents:
        try:
            distance_m = int(document.get("distance") or 0)

            facility = NearbyFacility(
                category=category,
                name=document["place_name"],
                address=(
                    document.get("road_address_name")
                    or document.get("address_name")
                    or ""
                ),
                latitude=float(document["y"]),
                longitude=float(document["x"]),
                distance_m=distance_m,
                estimated_walking_minutes=estimate_walking_minutes(
                    distance_m
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=502,
                detail=f"{category_label} 검색 결과 형식이 올바르지 않습니다.",
            ) from error

        facilities.append(facility)

    return facilities


def find_nearby_subway_stations(
    latitude: float,
    longitude: float,
    radius_m: int = 2000,
    limit: int = 3,
) -> list[NearbyStation]:
    """기존 지하철역 API와 호환되는 결과를 반환합니다."""

    facilities = find_nearby_facilities(
        category="subway",
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        limit=limit,
    )

    return [
        NearbyStation.model_validate(
            facility.model_dump(exclude={"category"})
        )
        for facility in facilities
    ]


def find_nearby_living_facilities(
    latitude: float,
    longitude: float,
    radius_m: int = 2000,
    limit: int = 3,
) -> NearbyFacilities:
    """동일한 좌표와 반경으로 지하철역·마트·병원을 각각 조회합니다."""

    return NearbyFacilities(
        subways=find_nearby_facilities(
            category="subway",
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            limit=limit,
        ),
        marts=find_nearby_facilities(
            category="mart",
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            limit=limit,
        ),
        hospitals=find_nearby_facilities(
            category="hospital",
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            limit=limit,
        ),
    )
