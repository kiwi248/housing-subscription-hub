# test_listing_detail_address.py
"""상세주소 칸 테스트.

실제 Supabase에는 연결하지 않고, 스키마와 수정 API가 값을 제대로 넘기는지만 확인합니다.
"""

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.listing_schema import ListingCreate, ListingPublic


client = TestClient(app)
UPDATE_PATH = "/admin/listings/update/1"


def make_listing(detail_address: str | None = "서울 강남구 도곡로 464") -> ListingPublic:
    return ListingPublic(
        id=1,
        title="공고",
        housing_name="주택",
        area_sqm=Decimal("25.00"),
        recruitment_count=3,
        location="강남구",
        detail_address=detail_address,
        deposit=10000000,
        monthly_rent=200000,
        application_start_date=date(2026, 8, 1),
        application_end_date=date(2026, 8, 31),
        description="설명",
        image_url=None,
        source_url="https://example.com",
        created_at=datetime(2026, 8, 1, 9, 0, 0),
    )


def form_data(detail_address: str | None = None) -> dict:
    data = {
        "title": "공고",
        "housing_name": "주택",
        "area_sqm": "25.00",
        "recruitment_count": "3",
        "location": "강남구",
        "deposit": "10000000",
        "monthly_rent": "200000",
        "application_start_date": "2026-08-01",
        "application_end_date": "2026-08-31",
        "description": "설명",
        "source_url": "https://example.com",
    }
    if detail_address is not None:
        data["detail_address"] = detail_address
    return data


class SchemaTest(unittest.TestCase):
    def test_상세주소_없이도_등록값을_만들_수_있다(self):
        """이미 등록된 공고에는 상세주소가 없습니다."""
        listing = ListingCreate(
            title="공고",
            housing_name="주택",
            area_sqm=Decimal("25.00"),
            recruitment_count=3,
            location="강남구",
            deposit=0,
            monthly_rent=0,
            application_start_date=date(2026, 8, 1),
            application_end_date=date(2026, 8, 2),
            description="설명",
            source_url="https://example.com",
        )

        self.assertIsNone(listing.detail_address)

    def test_상세주소를_담을_수_있다(self):
        listing = ListingCreate(
            title="공고",
            housing_name="주택",
            area_sqm=Decimal("25.00"),
            recruitment_count=3,
            location="강남구",
            detail_address="서울 강남구 도곡로 464",
            deposit=0,
            monthly_rent=0,
            application_start_date=date(2026, 8, 1),
            application_end_date=date(2026, 8, 2),
            description="설명",
            source_url="https://example.com",
        )

        self.assertEqual(listing.detail_address, "서울 강남구 도곡로 464")

    def test_저장에_보낼_때도_상세주소가_함께_간다(self):
        listing = ListingCreate(
            title="공고",
            housing_name="주택",
            area_sqm=Decimal("25.00"),
            recruitment_count=3,
            location="강남구",
            detail_address="서울 강남구 도곡로 464",
            deposit=0,
            monthly_rent=0,
            application_start_date=date(2026, 8, 1),
            application_end_date=date(2026, 8, 2),
            description="설명",
            source_url="https://example.com",
        )

        self.assertEqual(
            listing.model_dump(mode="json")["detail_address"], "서울 강남구 도곡로 464"
        )

    def test_조회_응답에_상세주소가_들어간다(self):
        self.assertEqual(make_listing().detail_address, "서울 강남구 도곡로 464")

    def test_상세주소가_없는_공고도_응답을_만들_수_있다(self):
        self.assertIsNone(make_listing(None).detail_address)


class UpdateApiTest(unittest.TestCase):
    def test_앞뒤_공백은_없애고_저장한다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["detail_address"] = listing.detail_address
            return make_listing()

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()),              patch("app.routers.admin_router.listing_update", side_effect=fake_update),              patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(
                UPDATE_PATH, data=form_data("  서울 강남구 도곡로 464  ")
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(saved["detail_address"], "서울 강남구 도곡로 464")

    def test_공백만_보내면_값_없음으로_저장된다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["detail_address"] = listing.detail_address
            return make_listing(None)

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()),              patch("app.routers.admin_router.listing_update", side_effect=fake_update),              patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(UPDATE_PATH, data=form_data("   "))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(saved["detail_address"])

    def test_보낸_상세주소가_그대로_저장된다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["detail_address"] = listing.detail_address
            return make_listing()

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(
                UPDATE_PATH, data=form_data("서울 송파구 올림픽로 240")
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(saved["detail_address"], "서울 송파구 올림픽로 240")

    def test_상세주소를_비우면_값_없음으로_저장된다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["detail_address"] = listing.detail_address
            return make_listing(None)

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(UPDATE_PATH, data=form_data(""))

        self.assertEqual(response.status_code, 200)
        # 빈 문자열이 아니라 값 없음으로 저장해야 컬럼이 NULL이 됩니다.
        self.assertIsNone(saved["detail_address"])

    def test_상세주소를_보내지_않아도_수정이_된다(self):
        """예전 화면에서 온 요청도 그대로 동작해야 합니다."""
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", return_value=make_listing()) as fake_update, \
             patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(UPDATE_PATH, data=form_data())

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(fake_update.call_args.args[1].detail_address)


if __name__ == "__main__":
    unittest.main()
