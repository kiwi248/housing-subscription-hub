# test_listing_image_delete_api.py
"""이미지 삭제 전용 API 테스트.

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

DELETE_IMAGE_PATH = "/admin/listings/1/image"
OUR_IMAGE_URL = "https://example.supabase.co/storage/v1/object/public/listing-images/old.png"
EXTERNAL_IMAGE_URL = "https://www.i-sh.co.kr/outside.png"


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


class DeleteImageApiTest(unittest.TestCase):
    def test_이미지를_지우면_참조가_없어지고_파일도_지운다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_clear_image", return_value=make_listing(image_url=None)) as fake_clear, \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIsNone(response.json()["data"]["image_url"])
        fake_clear.assert_called_once_with(1)
        fake_delete.assert_called_once_with(OUR_IMAGE_URL)

    def test_공고_id_말고는_아무_값도_받지_않는다(self):
        """제목·금액 같은 값을 함께 보내도 저장에 쓰이지 않아야 합니다."""
        cleared = {}

        def fake_clear(listing_id):
            cleared["args"] = listing_id
            return make_listing(image_url=None)

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_clear_image", side_effect=fake_clear), \
             patch("app.routers.admin_router.listing_update") as fake_update, \
             patch("app.routers.admin_router.delete_listing_image"):
            response = client.request(
                "DELETE",
                DELETE_IMAGE_PATH,
                json={"title": "몰래 바뀐 제목", "deposit": 999},
            )

        self.assertEqual(response.status_code, 200)
        # 공고 수정 서비스는 아예 호출되지 않습니다.
        fake_update.assert_not_called()
        self.assertEqual(cleared["args"], 1)

    def test_없는_공고면_404를_준다(self):
        with patch("app.routers.admin_router.listing_get", return_value=None), \
             patch("app.routers.admin_router.listing_clear_image") as fake_clear, \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(response.status_code, 404)
        fake_clear.assert_not_called()
        fake_delete.assert_not_called()

    def test_이미_이미지가_없으면_안전하게_끝낸다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=None)), \
             patch("app.routers.admin_router.listing_clear_image") as fake_clear, \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        fake_clear.assert_not_called()
        fake_delete.assert_not_called()

    def test_여러_번_불러도_파일_삭제는_한_번만_일어난다(self):
        """두 번째 요청에서는 이미 이미지가 없으므로 삭제를 다시 부르지 않습니다."""
        listings = [make_listing(), make_listing(image_url=None)]

        with patch("app.routers.admin_router.listing_get", side_effect=lambda _id: listings.pop(0)), \
             patch("app.routers.admin_router.listing_clear_image", return_value=make_listing(image_url=None)), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            first = client.delete(DELETE_IMAGE_PATH)
            second = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        fake_delete.assert_called_once_with(OUR_IMAGE_URL)

    def test_DB_수정에_실패하면_파일을_지우지_않는다(self):
        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_clear_image", return_value=None), \
             patch("app.routers.admin_router.delete_listing_image") as fake_delete:
            response = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(response.status_code, 500)
        # DB가 아직 이미지를 가리키고 있으므로 파일을 지우면 공고가 깨집니다.
        fake_delete.assert_not_called()

    def test_외부_URL은_Storage를_건드리지_않는다(self):
        from app.services import image_service

        with patch("app.routers.admin_router.listing_get", return_value=make_listing(image_url=EXTERNAL_IMAGE_URL)), \
             patch("app.routers.admin_router.listing_clear_image", return_value=make_listing(image_url=None)), \
             patch.object(image_service, "get_supabase") as fake_supabase:
            response = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(response.status_code, 200)
        fake_supabase.assert_not_called()

    def test_다른_공고가_쓰는_이미지는_지우지_않는다(self):
        from app.services import image_service

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_clear_image", return_value=make_listing(image_url=None)), \
             patch.object(image_service, "is_image_still_used", return_value=True), \
             patch.object(image_service, "get_supabase") as fake_supabase:
            response = client.delete(DELETE_IMAGE_PATH)

        self.assertEqual(response.status_code, 200)
        fake_supabase.assert_not_called()

    def test_Storage_삭제가_실패해도_요청은_성공하고_기록된다(self):
        from app.services import image_service

        with patch("app.routers.admin_router.listing_get", return_value=make_listing()), \
             patch("app.routers.admin_router.listing_clear_image", return_value=make_listing(image_url=None)), \
             patch.object(image_service, "is_image_still_used", return_value=False), \
             patch.object(image_service, "get_supabase") as fake_supabase, \
             patch.object(image_service, "add_log") as fake_log:
            fake_supabase.return_value.storage.from_.return_value.remove.side_effect = (
                RuntimeError("storage down")
            )
            response = client.delete(DELETE_IMAGE_PATH)

        # DB에서는 이미 지워졌으므로 요청 자체는 성공입니다.
        self.assertEqual(response.status_code, 200)
        # 다만 조용히 넘기지 않고 남깁니다.
        fake_log.assert_called_once()
        self.assertEqual(fake_log.call_args.args[0], "error")


class ClearImageServiceTest(unittest.TestCase):
    """listing_clear_image가 image_url 한 칸만 건드리는지 확인합니다."""

    def test_image_url만_None으로_바꾼다(self):
        from app.services import listing_service

        sent = {}

        class FakeQuery:
            def update(self, data):
                sent["data"] = data
                return self

            def eq(self, column, value):
                sent["eq"] = (column, value)
                return self

            def execute(self):
                class Result:
                    data = [make_listing(image_url=None).model_dump(mode="json")]

                return Result()

        class FakeSupabase:
            def table(self, name):
                sent["table"] = name
                return FakeQuery()

        with patch.object(listing_service, "get_supabase", return_value=FakeSupabase()):
            result = listing_service.listing_clear_image(1)

        self.assertEqual(sent["table"], "listings")
        self.assertEqual(sent["eq"], ("id", 1))
        # 제목·금액 같은 다른 칸은 아예 보내지 않습니다.
        self.assertEqual(sent["data"], {"image_url": None})
        self.assertIsNone(result.image_url)


if __name__ == "__main__":
    unittest.main()
