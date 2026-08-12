from typing import Literal

from pydantic import BaseModel, Field


class GeocodeResult(BaseModel):
    """주소 또는 장소명을 좌표로 변환한 결과입니다."""

    address: str = Field(
        min_length=1,
        examples=["서울 중구 세종대로 110"],
    )
    latitude: float = Field(
        ge=-90,
        le=90,
        examples=[37.566370776634],
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        examples=[126.977918351844],
    )
    matched_by: Literal["address", "keyword"] = Field(
        examples=["address"],
    )


class NearbyStation(BaseModel):
    """공고 위치 주변의 지하철역 정보입니다."""

    name: str = Field(
        min_length=1,
        examples=["시청역 1호선"],
    )
    address: str = Field(
        default="",
        examples=["서울 중구 정동 5-5"],
    )
    latitude: float = Field(
        ge=-90,
        le=90,
        examples=[37.5654],
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        examples=[126.9771],
    )
    distance_m: int = Field(
        ge=0,
        examples=[420],
    )
    estimated_walking_minutes: int = Field(
        ge=1,
        examples=[7],
    )


class NearbyFacility(NearbyStation):
    """공고 위치 주변의 생활권 시설 정보입니다."""

    category: Literal["subway", "mart", "hospital"] = Field(
        examples=["subway"],
    )


class NearbyFacilities(BaseModel):
    """시설 종류별 주변 생활권 검색 결과입니다."""

    subways: list[NearbyFacility] = Field(
        default_factory=list,
    )
    marts: list[NearbyFacility] = Field(
        default_factory=list,
    )
    hospitals: list[NearbyFacility] = Field(
        default_factory=list,
    )
