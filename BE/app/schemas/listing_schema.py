# listing_schema.py
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255, examples=["행복주택 입주자 모집공고"])
    housing_name: str = Field(min_length=1, max_length=255, examples=["강남 행복주택"])
    area_sqm: Decimal = Field(gt=0, examples=["39.72"])
    recruitment_count: int = Field(gt=0, examples=[12])
    location: str = Field(min_length=1, max_length=50, examples=["강남구"])
    # 자치구만으로는 어느 동네인지 알기 어려워 도로명 주소를 따로 받습니다. 선택 입력입니다.
    detail_address: str | None = Field(
        default=None, max_length=255, examples=["서울 강남구 도곡로 464"]
    )
    deposit: int = Field(ge=0, examples=[50000000])
    monthly_rent: int = Field(ge=0, examples=[350000])
    application_start_date: date
    application_end_date: date
    description: str = Field(min_length=1, examples=["전용면적 39.72㎡ 입주자를 모집합니다."])
    # 목록 카드에 보여 줄 대표 이미지입니다.
    image_url: str | None = None
    # 공고에 붙일 사진 전부입니다. 첫 장이 대표 이미지가 됩니다.
    #
    # 이 값은 listings 테이블의 칸이 아니라 listing_images 테이블로 갑니다.
    # listing_create/listing_update가 저장 전에 따로 떼어 냅니다.
    image_urls: list[str] = Field(default_factory=list)
    source_url: str = Field(min_length=1, examples=["https://apply.lh.or.kr/"])


class ListingPublic(BaseModel):
    id: int
    title: str
    housing_name: str
    area_sqm: Decimal
    recruitment_count: int
    location: str
    detail_address: str | None = None
    deposit: int
    monthly_rent: int
    application_start_date: date
    application_end_date: date
    description: str
    # 목록 카드에 보여 줄 대표 이미지입니다. images의 첫 장과 같은 값입니다.
    image_url: str | None = None
    # 공고에 붙은 사진 전부입니다. 보여 줄 순서대로 담깁니다.
    #
    # 기본값을 빈 목록으로 둔 이유가 있습니다.
    # 즐겨찾기 마이페이지는 listings(*)만 읽어 사진 목록을 받지 않습니다.
    # 필수로 만들면 그 응답이 검증에 걸려 깨집니다.
    images: list[str] = Field(default_factory=list)
    source_url: str
    created_at: datetime


class ListingPage(BaseModel):
    """목록을 페이지로 나눠 보낼 때 쓰는 응답입니다.

    화면이 전체 페이지 수를 계산할 수 있도록 개수 정보를 함께 담습니다.
    """

    items: list[ListingPublic]
    page: int
    page_size: int
    total_count: int
    total_pages: int
