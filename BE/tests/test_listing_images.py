# test_listing_images.py
"""공고 사진 여러 장 처리 테스트.

실제 Supabase와 Storage에는 연결하지 않습니다.
가짜 객체로 어떤 값이 오가는지만 확인합니다.

BE 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest
from datetime import datetime
from unittest.mock import patch

from app.core.upload_config import MAX_IMAGE_COUNT, MAX_TOTAL_UPLOAD_SIZE
from app.schemas.listing_schema import ListingCreate, ListingPublic
from app.services.listing_service import split_image_urls, to_listing


BASE_TIME = datetime(2026, 8, 1, 9, 0, 0)

PHOTO_A = "https://example.com/a.jpg"
PHOTO_B = "https://example.com/b.jpg"
PHOTO_C = "https://example.com/c.jpg"


def make_row(**overrides) -> dict:
    """DB에서 읽어온 한 줄을 흉내 냅니다."""
    row = {
        "id": 1,
        "title": "[테스트] 공고",
        "housing_name": "테스트하우스",
        "area_sqm": "25.00",
        "recruitment_count": 3,
        "location": "중구",
        "detail_address": None,
        "deposit": 10000000,
        "monthly_rent": 200000,
        "application_start_date": "2026-08-01",
        "application_end_date": "2026-08-31",
        "description": "설명",
        "image_url": None,
        "source_url": "https://example.com/test",
        "created_at": BASE_TIME.isoformat(),
    }
    row.update(overrides)
    return row


class ToListingTest(unittest.TestCase):
    """함께 읽어 온 사진을 순서대로 늘어놓습니다."""

    def test_사진을_순서대로_담는다(self):
        row = make_row(
            image_url=PHOTO_A,
            listing_images=[
                {"image_url": PHOTO_B, "sort_order": 1},
                {"image_url": PHOTO_A, "sort_order": 0},
                {"image_url": PHOTO_C, "sort_order": 2},
            ],
        )

        listing = to_listing(row)

        self.assertEqual(listing.images, [PHOTO_A, PHOTO_B, PHOTO_C])

    def test_대표_이미지는_첫_장과_같다(self):
        row = make_row(
            image_url=PHOTO_A,
            listing_images=[
                {"image_url": PHOTO_A, "sort_order": 0},
                {"image_url": PHOTO_B, "sort_order": 1},
            ],
        )

        listing = to_listing(row)

        self.assertEqual(listing.image_url, listing.images[0])

    def test_사진_테이블이_비면_대표_이미지_한_장으로_본다(self):
        """새 테이블을 만들기 전에 등록된 공고입니다.

        빈 목록으로 두면 상세보기에서 사진이 없는 것처럼 보입니다.
        """
        row = make_row(image_url=PHOTO_A, listing_images=[])

        listing = to_listing(row)

        self.assertEqual(listing.images, [PHOTO_A])

    def test_사진도_대표_이미지도_없으면_빈_목록이다(self):
        listing = to_listing(make_row(listing_images=[]))

        self.assertEqual(listing.images, [])

    def test_사진_칸이_아예_없어도_안전하다(self):
        """즐겨찾기 마이페이지처럼 listings(*)만 읽어 오는 경우입니다."""
        listing = to_listing(make_row(image_url=PHOTO_A))

        self.assertEqual(listing.images, [PHOTO_A])

    def test_빈_URL은_걸러_낸다(self):
        row = make_row(
            listing_images=[
                {"image_url": PHOTO_A, "sort_order": 0},
                {"image_url": None, "sort_order": 1},
            ]
        )

        self.assertEqual(to_listing(row).images, [PHOTO_A])

    def test_원래_줄을_바꾸지_않는다(self):
        """같은 줄을 다시 쓰는 코드가 생겨도 안전해야 합니다."""
        row = make_row(listing_images=[{"image_url": PHOTO_A, "sort_order": 0}])

        to_listing(row)

        self.assertIn("listing_images", row)


class SplitImageUrlsTest(unittest.TestCase):
    """image_urls는 listings 테이블에 없는 칸이라 따로 떼어 냅니다."""

    def make_listing(self, **overrides) -> ListingCreate:
        values = {
            "title": "공고",
            "housing_name": "주택",
            "area_sqm": "25.00",
            "recruitment_count": 3,
            "location": "중구",
            "deposit": 1000,
            "monthly_rent": 100,
            "application_start_date": "2026-08-01",
            "application_end_date": "2026-08-31",
            "description": "설명",
            "source_url": "https://example.com",
        }
        values.update(overrides)
        return ListingCreate(**values)

    def test_저장할_값에서_사진_목록을_떼어_낸다(self):
        listing_data, image_urls = split_image_urls(
            self.make_listing(image_urls=[PHOTO_A, PHOTO_B])
        )

        self.assertNotIn("image_urls", listing_data)
        self.assertEqual(image_urls, [PHOTO_A, PHOTO_B])

    def test_사진이_없으면_빈_목록이다(self):
        _, image_urls = split_image_urls(self.make_listing())

        self.assertEqual(image_urls, [])

    def test_나머지_값은_그대로_남는다(self):
        listing_data, _ = split_image_urls(self.make_listing(image_urls=[PHOTO_A]))

        self.assertEqual(listing_data["title"], "공고")
        self.assertEqual(listing_data["location"], "중구")
        # Supabase가 그대로 받을 수 있게 날짜와 소수는 문자열이 됩니다.
        self.assertEqual(listing_data["application_start_date"], "2026-08-01")
        self.assertEqual(listing_data["area_sqm"], "25.00")


class UploadLimitTest(unittest.TestCase):
    """장수와 전체 크기를 미리 막습니다."""

    def test_스무_장까지_허용한다(self):
        self.assertEqual(MAX_IMAGE_COUNT, 20)

    def test_전체_크기_상한이_있다(self):
        """장수만 막으면 20장 × 5MB = 100MB가 한 요청에 실립니다."""
        self.assertEqual(MAX_TOTAL_UPLOAD_SIZE, 60 * 1024 * 1024)


class ListingImagesApiTest(unittest.TestCase):
    """사진 목록 저장 API가 무엇을 보내는지 확인합니다."""

    def make_listing(self, images: list[str], image_url: str | None) -> ListingPublic:
        return ListingPublic.model_validate(
            make_row(image_url=image_url, images=images, listing_images=[])
        )

    def test_남길_사진만_넘기면_나머지_파일을_지운다(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A, PHOTO_B, PHOTO_C], PHOTO_A)
        after = self.make_listing([PHOTO_A, PHOTO_C], PHOTO_A)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update", return_value=after
        ) as fake_update, patch(
            "app.routers.admin_router.delete_listing_image"
        ) as fake_delete:
            response = client.put(
                "/admin/listings/1/images",
                data={"kept_image_urls": [PHOTO_A, PHOTO_C], "keep_count": 2},
            )

        self.assertEqual(response.status_code, 200)
        # 빠진 사진의 파일만 지웁니다.
        fake_delete.assert_called_once_with(PHOTO_B)
        # 남은 사진 중 첫 장이 대표 이미지가 됩니다.
        saved = fake_update.call_args[0][1]
        self.assertEqual(saved.image_urls, [PHOTO_A, PHOTO_C])
        self.assertEqual(saved.image_url, PHOTO_A)

    def test_이_공고에_없는_URL은_무시한다(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A], PHOTO_A)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update", return_value=current
        ) as fake_update, patch("app.routers.admin_router.delete_listing_image"):
            client.put(
                "/admin/listings/1/images",
                data={"kept_image_urls": [PHOTO_A, "https://남의공고.com/x.jpg"], "keep_count": 2},
            )

        self.assertEqual(fake_update.call_args[0][1].image_urls, [PHOTO_A])

    def test_사진을_모두_지우면_대표_이미지도_없어진다(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A, PHOTO_B], PHOTO_A)
        after = self.make_listing([], None)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update", return_value=after
        ) as fake_update, patch(
            "app.routers.admin_router.delete_listing_image"
        ) as fake_delete:
            client.put("/admin/listings/1/images", data={"keep_count": 0})

        saved = fake_update.call_args[0][1]
        self.assertEqual(saved.image_urls, [])
        self.assertIsNone(saved.image_url)
        self.assertEqual(fake_delete.call_count, 2)

    def test_남길_사진이_중간에_사라지면_아무것도_지우지_않는다(self):
        """실제로 사진 열 장이 한 번에 사라진 적이 있습니다.

        화면이 보내는 형식이 틀려 kept_image_urls가 서버에 하나도
        도착하지 않았고, 서버는 "남길 사진 없음"으로 알아들었습니다.
        장수를 함께 받아 맞춰 보면 지우기 전에 걸러집니다.
        """
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A, PHOTO_B, PHOTO_C], PHOTO_A)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update"
        ) as fake_update, patch(
            "app.routers.admin_router.delete_listing_image"
        ) as fake_delete:
            # 3장을 남기겠다고 했는데 목록이 오지 않은 상황입니다.
            response = client.put(
                "/admin/listings/1/images", data={"keep_count": 3}
            )

        self.assertEqual(response.status_code, 400)
        fake_update.assert_not_called()
        fake_delete.assert_not_called()

    def test_장수를_아예_보내지_않으면_거절한다(self):
        """본문이 통째로 사라진 요청입니다. 조용히 지우면 안 됩니다."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A, PHOTO_B], PHOTO_A)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update"
        ) as fake_update, patch(
            "app.routers.admin_router.delete_listing_image"
        ) as fake_delete:
            response = client.put("/admin/listings/1/images")

        self.assertEqual(response.status_code, 422)
        fake_update.assert_not_called()
        fake_delete.assert_not_called()

    def test_없는_공고면_404다(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        with patch("app.routers.admin_router.listing_get", return_value=None):
            response = client.put("/admin/listings/999/images", data={"keep_count": 0})

        self.assertEqual(response.status_code, 404)


class UpdateKeepsImagesTest(unittest.TestCase):
    """공고를 수정해도 추가 사진이 사라지면 안 됩니다."""

    def make_listing(self, images: list[str], image_url: str | None) -> ListingPublic:
        return ListingPublic.model_validate(
            make_row(image_url=image_url, images=images, listing_images=[])
        )

    def base_form(self) -> dict:
        return {
            "title": "공고",
            "housing_name": "주택",
            "area_sqm": "25.00",
            "recruitment_count": "3",
            "location": "중구",
            "deposit": "1000",
            "monthly_rent": "100",
            "application_start_date": "2026-08-01",
            "application_end_date": "2026-08-31",
            "description": "설명",
            "source_url": "https://example.com",
        }

    def test_제목만_고쳐도_사진이_그대로_남는다(self):
        """이 확인이 없으면 저장할 때마다 추가 사진이 전부 사라집니다."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A, PHOTO_B, PHOTO_C], PHOTO_A)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update", return_value=current
        ) as fake_update, patch("app.routers.admin_router.delete_listing_image"):
            response = client.put(
                "/admin/listings/update/1", data=self.base_form()
            )

        self.assertEqual(response.status_code, 200)
        saved = fake_update.call_args[0][1]
        self.assertEqual(saved.image_urls, [PHOTO_A, PHOTO_B, PHOTO_C])

    def test_대표_이미지를_지우면_다음_사진이_대표가_된다(self):
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        current = self.make_listing([PHOTO_A, PHOTO_B], PHOTO_A)

        with patch("app.routers.admin_router.listing_get", return_value=current), patch(
            "app.routers.admin_router.listing_update", return_value=current
        ) as fake_update, patch("app.routers.admin_router.delete_listing_image"):
            client.put(
                "/admin/listings/update/1",
                data={**self.base_form(), "remove_image": "true"},
            )

        saved = fake_update.call_args[0][1]
        self.assertEqual(saved.image_urls, [PHOTO_B])
        self.assertEqual(saved.image_url, PHOTO_B)


if __name__ == "__main__":
    unittest.main()
