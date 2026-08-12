# app/core/kakao_client.py
# 카카오 키 로딩, 카카오 API 호출

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

KAKAO_ADDRESS_SEARCH_URL = (
    "https://dapi.kakao.com/v2/local/search/address.json"
)
KAKAO_REQUEST_TIMEOUT = 5.0


class KakaoGeocodingError(Exception):
    pass


def get_kakao_rest_api_key() -> str:
    load_dotenv(ENV_PATH)

    value = os.getenv("KAKAO_REST_API_KEY", "").strip()

    if not value:
        raise KakaoGeocodingError(
            f"KAKAO_REST_API_KEY 값이 없습니다. {ENV_PATH} 파일을 확인하세요."
        )

    if value.startswith("your-"):
        raise KakaoGeocodingError(
            "KAKAO_REST_API_KEY 값이 예시 값입니다."
        )

    return value


def address_to_coordinates(
    address: str,
    rest_api_key: str,
) -> tuple[float, float] | None:
    # 현재 favorite_service.py의 함수 내용을 그대로 이동
    ...