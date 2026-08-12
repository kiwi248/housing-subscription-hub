from typing import Any

from core.api_client import request


def get_listings(sort: str | None = None):
    # 정렬은 백엔드가 합니다. 고른 기준 이름만 넘깁니다.
    params = {"sort": sort} if sort else None
    return request("GET", "/listings/getall", params=params)


def search_listings(params: dict[str, Any]):
    return request("GET", "/listings/search", params=params)


def get_listing(listing_id: int):
    return request("GET", f"/listings/get/{listing_id}")
