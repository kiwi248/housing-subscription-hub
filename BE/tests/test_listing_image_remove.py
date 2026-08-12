# test_listing_image_remove.py
"""청약정보 수정 시 기존 이미지 삭제 테스트.

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


def form_data(remove_image: str | None = None) -> dict:
    """수정 요청에 보낼 폼 값입니다."""
    data = {
        "title": "[테스트] 수정된 공고",
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
    if remove_image is not None:
        data["remove_image"] = remove_image
    return data


class RemoveImageTest(unittest.TestCase):
    def test_삭제를_고르면_이미지_참조가_없어진다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            return make_listing(image_url=None)

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data(remove_image="true"))

        self.assertEqual(response.status_code, 200)
        # 빈 문자열이나 가짜 URL이 아니라 None으로 저장해야 합니다.
        self.assertIsNone(saved["image_url"])
        fake_delete.assert_called_once_with(OUR_IMAGE_URL)

    def test_삭제를_고르지_않으면_기존_이미지를_유지한다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            return make_listing()

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data(remove_image="false"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(saved["image_url"], OUR_IMAGE_URL)
        fake_delete.assert_not_called()

    def test_remove_image를_보내지_않아도_기존처럼_유지한다(self):
        """이전 화면에서 온 요청도 그대로 동작해야 합니다."""
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            return make_listing()

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(saved["image_url"], OUR_IMAGE_URL)
        fake_delete.assert_not_called()

    def test_새_이미지와_삭제를_함께_보내면_거절한다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update") as fake_update, \
             patch("app.routers.admin_router.upload_listing_image") as fake_upload, \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(
                UPDATE_PATH,
                data=form_data(remove_image="true"),
                files={"image": ("new.png", TEST_PNG, "image/png")},
            )

        self.assertEqual(response.status_code, 400)
        # 거절했으므로 업로드도 수정도 삭제도 일어나면 안 됩니다.
        fake_upload.assert_not_called()
        fake_update.assert_not_called()
        fake_delete.assert_not_called()

    def test_DB_수정에_실패하면_기존_파일을_지우지_않는다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_update", return_value=None), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data(remove_image="true"))

        self.assertEqual(response.status_code, 500)
        # DB가 아직 기존 이미지를 가리키고 있으므로 파일을 지우면 공고가 깨집니다.
        fake_delete.assert_not_called()

    def test_이미_이미지가_없는_공고에_삭제를_요청해도_안전하다(self):
        saved = {}

        def fake_update(listing_id, listing):
            saved["image_url"] = listing.image_url
            return make_listing(image_url=None)

        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=None)), \
             patch("app.routers.admin_router.listing_update", side_effect=fake_update), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.put(UPDATE_PATH, data=form_data(remove_image="true"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(saved["image_url"])
        fake_delete.assert_not_called()

    def test_저장을_두_번_눌러도_중복_삭제가_일어나지_않는다(self):
        """두 번째 요청에서는 이미 이미지가 없으므로 삭제를 다시 부르지 않습니다."""
        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=None)), \
             patch("app.routers.admin_router.listing_update", return_value=make_listing(image_url=None)), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            first = client.put(UPDATE_PATH, data=form_data(remove_image="true"))
            second = client.put(UPDATE_PATH, data=form_data(remove_image="true"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        fake_delete.assert_not_called()

    def test_외부_URL을_지우라고_해도_Storage를_건드리지_않는다(self):
        from app.services import image_service

        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=EXTERNAL_IMAGE_URL)), \
             patch("app.routers.admin_router.listing_update", return_value=make_listing(image_url=None)), \
             patch.object(image_service, "get_supabase") as fake_supabase:
            response = client.put(UPDATE_PATH, data=form_data(remove_image="true"))

        self.assertEqual(response.status_code, 200)
        # 우리 버킷 경로가 아니므로 Storage에 접근조차 하지 않아야 합니다.
        fake_supabase.assert_not_called()


class DeleteImageSafetyTest(unittest.TestCase):
    """image_service.delete_listing_image의 안전장치를 직접 확인합니다."""

    def test_다른_공고가_쓰고_있으면_지우지_않는다(self):
        from app.services import image_service

        with patch.object(image_service, "is_image_still_used", return_value=True), \
             patch.object(image_service, "get_supabase") as fake_supabase:
            image_service.delete_listing_image(OUR_IMAGE_URL)

        fake_supabase.assert_not_called()

    def test_아무도_쓰지_않으면_지운다(self):
        from app.services import image_service

        with patch.object(image_service, "is_image_still_used", return_value=False), \
             patch.object(image_service, "get_supabase") as fake_supabase:
            image_service.delete_listing_image(OUR_IMAGE_URL)

        remove = fake_supabase.return_value.storage.from_.return_value.remove
        remove.assert_called_once_with(["old.png"])

    def test_참조_확인에_실패하면_지우지_않는다(self):
        """잘못 지워 되돌릴 수 없는 것보다 남겨 두는 편이 안전합니다."""
        from app.services import image_service

        class Boom:
            def table(self, *args, **kwargs):
                raise RuntimeError("연결 실패")

        with patch.object(image_service, "get_supabase", return_value=Boom()), \
             patch.object(image_service, "add_log") as fake_log:
            still_used = image_service.is_image_still_used(OUR_IMAGE_URL)

        self.assertTrue(still_used)
        fake_log.assert_called_once()

    def test_Storage_삭제_실패를_조용히_넘기지_않는다(self):
        from app.services import image_service

        with patch.object(image_service, "is_image_still_used", return_value=False), \
             patch.object(image_service, "get_supabase") as fake_supabase, \
             patch.object(image_service, "add_log") as fake_log:
            fake_supabase.return_value.storage.from_.return_value.remove.side_effect = (
                RuntimeError("storage down")
            )
            # 요청 자체를 실패시키지는 않습니다.
            image_service.delete_listing_image(OUR_IMAGE_URL)

        fake_log.assert_called_once()
        self.assertEqual(fake_log.call_args.args[0], "error")

    def test_값이_없으면_아무것도_하지_않는다(self):
        from app.services import image_service

        with patch.object(image_service, "get_supabase") as fake_supabase:
            image_service.delete_listing_image(None)
            image_service.delete_listing_image("")

        fake_supabase.assert_not_called()


if __name__ == "__main__":
    unittest.main()
