from core.api_client import request


def create_favorite(user_id: str, listing_id: int):
    return request("POST", "/favorites/create", json={"user_id": user_id, "listing_id": listing_id})


def get_mypage_favorites(user_id: str):
    return request("GET", f"/favorites/mypage/{user_id}")


def delete_favorite(user_id: str, listing_id: int):
    return request("DELETE", f"/favorites/delete/{user_id}/{listing_id}")
