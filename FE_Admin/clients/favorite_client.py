from core.api_client import request


def get_favorite_ranking():
    return request("GET", "/admin/favorites/ranking")


def get_favorite_detail(listing_id: int | None = None):
    params = {"listing_id": listing_id} if listing_id is not None else None
    return request("GET", "/admin/favorites/detail", params=params)
