# favorite_service.py
from app.core.supabase_config import get_supabase
from app.schemas.favorite_schema import (
    FavoriteCreate,
    FavoriteDetail,
    FavoritePublic,
    FavoriteRanking,
    FavoriteWithListing,
)


def favorite_create(favorite: FavoriteCreate) -> FavoritePublic | None:
    supabase = get_supabase()
    result = (
        supabase.table("favorites")
        .insert(
            {
                "user_id": favorite.user_id,
                "listing_id": favorite.listing_id,
            }
        )
        .execute()
    )
    if not result.data:
        return None
    return FavoritePublic.model_validate(result.data[0])


def favorite_get_by_user_and_listing(user_id: str, listing_id: int) -> FavoritePublic | None:
    supabase = get_supabase()
    result = (
        supabase.table("favorites")
        .select("*")
        .eq("user_id", user_id)
        .eq("listing_id", listing_id)
        .execute()
    )
    if not result.data:
        return None
    return FavoritePublic.model_validate(result.data[0])


def favorite_get_mypage(user_id: str) -> list[FavoriteWithListing]:
    """ mypage에서 내가 즐겨찾기한 청약정보 목록을 조회합니다. """
    supabase = get_supabase()
    result = (
        supabase.table("favorites")
        .select("*, listing:listings(*)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [FavoriteWithListing.model_validate(item) for item in result.data]


def favorite_delete(user_id: str, listing_id: int) -> FavoritePublic | None:
    supabase = get_supabase()
    result = (
        supabase.table("favorites")
        .delete()
        .eq("user_id", user_id)
        .eq("listing_id", listing_id)
        .execute()
    )
    if not result.data:
        return None
    return FavoritePublic.model_validate(result.data[0])


def favorite_ranking() -> list[FavoriteRanking]:
    """ 관리자용: 즐겨찾기가 많은 청약정보 순으로 조회합니다. """
    supabase = get_supabase()
    result = (
        supabase.table("favorites")
        .select("listing_id, listings(title)")
        .execute()
    )

    counts: dict[int, dict] = {}
    for row in result.data:
        listing_id = row["listing_id"]
        listing = row.get("listings") or {}
        if listing_id not in counts:
            counts[listing_id] = {
                "listing_id": listing_id,
                "title": listing.get("title", ""),
                "favorite_count": 0,
            }
        counts[listing_id]["favorite_count"] += 1

    ranking = sorted(counts.values(), key=lambda item: item["favorite_count"], reverse=True)
    return [FavoriteRanking.model_validate(item) for item in ranking]


def favorite_detail(listing_id: int | None) -> list[FavoriteDetail]:
    """ 관리자용: 어떤 유저가 어떤 청약정보를 즐겨찾기했는지 조회합니다.

    favorites.user_id는 auth.users를 참조하고 profiles를 참조하지 않아 PostgREST가
    favorites-profiles 관계를 자동으로 찾지 못합니다. 그래서 nickname은 user_id로
    profiles를 따로 조회해 채웁니다.
    """
    supabase = get_supabase()
    query = (
        supabase.table("favorites")
        .select("id, user_id, listing_id, created_at, listings(title)")
    )
    if listing_id is not None:
        query = query.eq("listing_id", listing_id)

    result = query.order("created_at", desc=True).execute()

    user_ids = list({row["user_id"] for row in result.data})
    nickname_by_user_id: dict[str, str | None] = {}
    if user_ids:
        profiles_result = (
            supabase.table("profiles")
            .select("id, nickname")
            .in_("id", user_ids)
            .execute()
        )
        nickname_by_user_id = {row["id"]: row.get("nickname") for row in profiles_result.data}

    details = []
    for row in result.data:
        listing = row.get("listings") or {}
        details.append(
            FavoriteDetail(
                favorite_id=row["id"],
                user_id=row["user_id"],
                nickname=nickname_by_user_id.get(row["user_id"]),
                listing_id=row["listing_id"],
                title=listing.get("title", ""),
                created_at=row["created_at"],
            )
        )
    return details
