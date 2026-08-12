# test_listing_update.py
"""청약정보 수정 API 테스트.

실제 Supabase DB와 Storage에는 연결하지 않습니다.
service와 image_service 함수를 가짜 함수로 바꿔치기해서 확인합니다.
"""

import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.listing_schema import ListingPublic


client = TestClient(app)

UPDATE_PATH = "/admin/listings/update/1"
OUR_IMAGE_URL = "https://example.supabase.co/storage/v1/object/public/listing-images/old.png"
NEW_IMAGE_URL = "https://example.supabase.co/storage/v1/object/public/listing-images/new.png"
EXTERNAL_IMAGE_URL = "https://www.i-sh.co.kr/outside.png"

# 매직 넘버가 맞는 아주 작은 PNG입니다. 실제 업로드는 하지 않습니다.
TEST_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def make_listing(listing_id: int = 1, image_url: str | None = OUR_IMAGE_URL) -> ListingPublic:
    return ListingPublic(
        id=listing_id,
        title="[테스트] 공고",
        housing_name="테스트하우스",
        area_sqm=Decimal("25.00"),
        recruitment_count=3,
        location="중구",
        deposit=10000000,
        monthly_rent=200000,
        application_start_date=date(2026, 8, 1),
        application_end_date=date(2026, 8, 31),
        description="테스트 설명",
        image_url=image_url,
        source_url="https://example.com/test",
        created_at=datetime(2026, 8, 1, 9, 0, 0),
    )


def form_data(title: str = "[테스트] 수정된 공고") -> dict:
    """수정 요청에 보낼 폼 값입니다."""
    return {
        "title": title,
        "housing_name": "테스트하우스",
        "area_sqm": "25.00",
        "recruitment_count": "3",
        "location": "중구",
        "deposit": "10000000",
        "monthly_rent": "200000",
        "application_start_date": "2026-08-01",
        "application_end_date": "2026-08-31",
        "description": "테스트 설명",
        "source_url": "https://example.com/test",
    }


class ListingUpdateTest(unittest.TestCase):
    def test_텍스트만_수정하면_기존_이미지를_유지한다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            saved["title"] = listing.title
            return make_listing()

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data())

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(saved["image_url"], OUR_IMAGE_URL)
        self.assertEqual(saved["title"], "[테스트] 수정된 공고")
        fake_delete.assert_not_called()

    def test_새_이미지로_수정하면_DB_URL이_바뀐다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            return make_listing(image_url=NEW_IMAGE_URL)

        async def fake_upload(image):
            return NEW_IMAGE_URL

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.upload_listing_image", side_effect=fake_upload), \
             patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(
                UPDATE_PATH,
                data=form_data(),
                files={"image": ("new.png", TEST_PNG, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(saved["image_url"], NEW_IMAGE_URL)
        self.assertEqual(response.json()["data"]["image_url"], NEW_IMAGE_URL)

    def test_DB_수정_성공_후_기존_이미지_삭제를_호출한다(self):
        async def fake_upload(image):
            return NEW_IMAGE_URL

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", return_value=make_listing(image_url=NEW_IMAGE_URL)), \
             patch("app.routers.admin_router.upload_listing_image", side_effect=fake_upload), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(
                UPDATE_PATH,
                data=form_data(),
                files={"image": ("new.png", TEST_PNG, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        # 지워야 할 대상은 새 이미지가 아니라 예전 이미지입니다.
        fake_delete.assert_called_once_with(OUR_IMAGE_URL)

    def test_기존_이미지가_외부_URL이면_삭제_함수가_외부_URL을_받는다(self):
        """라우터는 예전 URL을 그대로 넘기고, 외부 URL 판별은 image_service가 담당합니다."""
        async def fake_upload(image):
            return NEW_IMAGE_URL

        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=EXTERNAL_IMAGE_URL)), \
             patch("app.routers.admin_router.listing_update", return_value=make_listing(image_url=NEW_IMAGE_URL)), \
             patch("app.routers.admin_router.upload_listing_image", side_effect=fake_upload), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(
                UPDATE_PATH,
                data=form_data(),
                files={"image": ("new.png", TEST_PNG, "image/png")},
            )

        self.assertEqual(response.status_code, 200)
        fake_delete.assert_called_once_with(EXTERNAL_IMAGE_URL)

    def test_외부_URL은_실제로_지워지지_않는다(self):
        """image_service.delete_listing_image가 외부 URL을 걸러내는지 직접 확인합니다."""
        from app.services import image_service

        with patch.object(image_service, "get_supabase") as fake_supabase:
            image_service.delete_listing_image(EXTERNAL_IMAGE_URL)

        fake_supabase.assert_not_called()

    def test_기존_이미지가_없어도_정상_수정된다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            return make_listing(image_url=None)

        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=None)), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data())

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(saved["image_url"])
        fake_delete.assert_not_called()

    def test_새_이미지_업로드_실패하면_DB를_수정하지_않는다(self):
        from fastapi import HTTPException

        async def fake_upload(image):
            raise HTTPException(status_code=400, detail="이미지 파일이 아닙니다.")

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update") as fake_update, \
             patch("app.routers.admin_router.upload_listing_image", side_effect=fake_upload), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(
                UPDATE_PATH,
                data=form_data(),
                files={"image": ("bad.png", b"not an image", "image/png")},
            )

        self.assertEqual(response.status_code, 400)
        fake_update.assert_not_called()
        fake_delete.assert_not_called()

    def test_DB_수정_실패하면_새로_올린_이미지를_지운다(self):
        async def fake_upload(image):
            return NEW_IMAGE_URL

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", return_value=None), \
             patch("app.routers.admin_router.upload_listing_image", side_effect=fake_upload), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(
                UPDATE_PATH,
                data=form_data(),
                files={"image": ("new.png", TEST_PNG, "image/png")},
            )

        self.assertEqual(response.status_code, 500)
        # 예전 이미지가 아니라 새로 올린 이미지를 지워야 합니다.
        fake_delete.assert_called_once_with(NEW_IMAGE_URL)

    def test_DB_수정_실패하고_새_이미지도_없으면_아무것도_지우지_않는다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", return_value=None), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data())

        self.assertEqual(response.status_code, 500)
        fake_delete.assert_not_called()

    def test_기존_이미지_삭제가_실패해도_수정_결과는_유지된다(self):
        async def fake_upload(image):
            return NEW_IMAGE_URL

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", return_value=make_listing(image_url=NEW_IMAGE_URL)), \
             patch("app.routers.admin_router.upload_listing_image", side_effect=fake_upload), \
             patch("app.routers.admin_router.delete_listing_image", side_effect=RuntimeError("storage down")):
            with self.assertRaises(RuntimeError):
                client.put(
                    UPDATE_PATH,
                    data=form_data(),
                    files={"image": ("new.png", TEST_PNG, "image/png")},
                )

    def test_존재하지_않는_공고를_수정하면_404를_반환한다(self):
        with patch("app.routers.admin_router.listing_get", return_value=None), \
             patch("app.routers.admin_router.listing_update") as fake_update:
            response = client.put("/admin/listings/update/999999", data=form_data())

        self.assertEqual(response.status_code, 404)
        fake_update.assert_not_called()


class ExistingApiTest(unittest.TestCase):
    """수정 기능을 넣은 뒤에도 기존 등록·조회·삭제가 그대로인지 확인합니다."""

    def test_등록_API는_그대로_동작한다(self):
        with patch("app.routers.admin_router.listing_create", return_value=make_listing()):
            response = client.post(
                "/admin/listings/create",
                json={
                    "title": "[테스트] 공고",
                    "housing_name": "테스트하우스",
                    "area_sqm": 25,
                    "recruitment_count": 3,
                    "location": "중구",
                    "deposit": 10000000,
                    "monthly_rent": 200000,
                    "application_start_date": "2026-08-01",
                    "application_end_date": "2026-08-31",
                    "description": "테스트 설명",
                    "image_url": None,
                    "source_url": "https://example.com/test",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_전체조회_API는_그대로_동작한다(self):
        with patch("app.routers.listing_router.listing_get_all", return_value=[make_listing()]):
            response = client.get("/listings/getall")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_삭제_API는_그대로_동작하고_이미지도_지운다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_delete", return_value=make_listing()), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.delete("/admin/listings/delete/1")

        self.assertEqual(response.status_code, 200)
        fake_delete.assert_called_once_with(OUR_IMAGE_URL)

    def test_없는_공고_삭제는_404를_반환한다(self):
        with patch("app.routers.admin_router.listing_get", return_value=None):
            response = client.delete("/admin/listings/delete/999999")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
