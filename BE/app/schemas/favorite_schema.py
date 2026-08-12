# favorite_schema.py
from datetime import datetime

from pydantic import BaseModel

from app.schemas.listing_schema import ListingPublic


class FavoriteCreate(BaseModel):
    user_id: str
    listing_id: int


class FavoritePublic(BaseModel):
    id: int
    user_id: str
    listing_id: int
    created_at: datetime


class FavoriteWithListing(BaseModel):
    id: int
    user_id: str
    listing_id: int
    created_at: datetime
    listing: ListingPublic


class FavoriteCoordinate(BaseModel):
    """즐겨찾기 공고의 주소를 지도 좌표로 변환한 결과입니다."""

    listing_id: int
    title: str
    location: str
    longitude: float | None = None
    latitude: float | None = None


class FavoriteRanking(BaseModel):
    listing_id: int
    title: str
    favorite_count: int


class FavoriteDetail(BaseModel):
    favorite_id: int
    user_id: str
    nickname: str | None = None
    listing_id: int
    title: str
    created_at: datetime
