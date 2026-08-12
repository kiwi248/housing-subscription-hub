# test_listing_sort.py
"""청약정보 목록 정렬 기준 테스트.

실제 Supabase에 연결하지 않습니다. 어떤 순서로 정렬을 요청했는지만
가짜 질의 객체로 받아 확인합니다.

BE 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.listing_service import (
    SORT_COLUMNS,
    apply_sort,
    is_known_sort,
    move_closed_to_end,
)


client = TestClient(app)


class FakeQuery:
    """supabase 질의를 흉내 냅니다. 붙은 order를 순서대로 기억합니다."""

    def __init__(self):
        self.orders = []

    def order(self, column, desc=False, nullsfirst=None, foreign_table=None):
        self.orders.append((column, desc, nullsfirst))
        return self


class FakeListing:
    """ListingPublic 중 정렬에 쓰는 값만 흉내 냅니다."""

    def __init__(self, listing_id, end_date):
        self.id = listing_id
        self.application_end_date = end_date

    def __repr__(self):
        return f"공고{self.id}"


class SortColumnsTest(unittest.TestCase):
    def test_화면이_요청한_기준을_모두_안다(self):
        """사용자가 고를 수 있는 기준이 빠짐없이 있어야 합니다."""
        expected = {
            "created_desc",
            "end_date_asc",
            "area_desc",
            "area_asc",
            "recruitment_desc",
            "recruitment_asc",
            "deposit_desc",
            "deposit_asc",
            "rent_desc",
            "rent_asc",
        }
        self.assertEqual(set(SORT_COLUMNS), expected)

    def test_넓은_순과_좁은_순은_같은_항목을_반대로_본다(self):
        for desc_key, asc_key, column in (
            ("area_desc", "area_asc", "area_sqm"),
            ("recruitment_desc", "recruitment_asc", "recruitment_count"),
            ("deposit_desc", "deposit_asc", "deposit"),
            ("rent_desc", "rent_asc", "monthly_rent"),
        ):
            with self.subTest(column=column):
                self.assertEqual(SORT_COLUMNS[desc_key], (column, True))
                self.assertEqual(SORT_COLUMNS[asc_key], (column, False))

    def test_아는_기준인지_확인한다(self):
        self.assertTrue(is_known_sort("area_desc"))
        self.assertFalse(is_known_sort("엉뚱한값"))
        self.assertFalse(is_known_sort(None))
        self.assertFalse(is_known_sort(""))


class ApplySortTest(unittest.TestCase):
    def test_고른_항목으로_정렬을_붙인다(self):
        query = apply_sort(FakeQuery(), "area_desc")

        self.assertEqual(query.orders[0][0], "area_sqm")
        self.assertTrue(query.orders[0][1])

    def test_오름차순도_붙인다(self):
        query = apply_sort(FakeQuery(), "deposit_asc")

        self.assertEqual(query.orders[0][0], "deposit")
        self.assertFalse(query.orders[0][1])

    def test_값이_없는_공고는_뒤로_보낸다(self):
        """빈 값이 맨 위에 오면 목록이 이상해 보입니다."""
        query = apply_sort(FakeQuery(), "recruitment_desc")

        self.assertFalse(query.orders[0][2])

    def test_같은_값이면_나중에_등록한_공고가_앞이다(self):
        """이 기준이 없으면 페이지를 넘길 때마다 순서가 흔들릴 수 있습니다."""
        query = apply_sort(FakeQuery(), "rent_asc")

        self.assertEqual(query.orders[1], ("id", True, None))

    def test_모든_기준에_id_보조_정렬이_붙는다(self):
        for key in SORT_COLUMNS:
            with self.subTest(sort=key):
                query = apply_sort(FakeQuery(), key)
                self.assertEqual(len(query.orders), 2)
                self.assertEqual(query.orders[1][0], "id")


class MoveClosedToEndTest(unittest.TestCase):
    """정렬 기준이 바뀌어도 끝난 공고는 뒤에 있어야 합니다."""

    def setUp(self):
        self.today = date(2026, 8, 10)

    def test_끝난_공고를_뒤로_보낸다(self):
        listings = [
            FakeListing(1, date(2026, 8, 1)),
            FakeListing(2, date(2026, 8, 20)),
            FakeListing(3, date(2026, 8, 5)),
        ]

        result = move_closed_to_end(listings, self.today)

        self.assertEqual([x.id for x in result], [2, 3, 1])

    def test_마감일_순일_때는_최근에_끝난_것부터_놓는다(self):
        listings = [FakeListing(1, date(2026, 7, 1)), FakeListing(2, date(2026, 8, 1))]

        result = move_closed_to_end(listings, self.today, recent_closed_first=True)

        self.assertEqual([x.id for x in result], [2, 1])

    def test_다른_기준일_때는_받은_순서를_그대로_둔다(self):
        """면적이나 보증금 순으로 받았으면 그 순서를 흐트러뜨리면 안 됩니다."""
        listings = [FakeListing(1, date(2026, 7, 1)), FakeListing(2, date(2026, 8, 1))]

        result = move_closed_to_end(listings, self.today, recent_closed_first=False)

        self.assertEqual([x.id for x in result], [1, 2])

    def test_아직_열린_공고끼리는_순서를_바꾸지_않는다(self):
        listings = [
            FakeListing(1, date(2026, 9, 1)),
            FakeListing(2, date(2026, 8, 30)),
            FakeListing(3, date(2026, 12, 1)),
        ]

        result = move_closed_to_end(listings, self.today, recent_closed_first=False)

        self.assertEqual([x.id for x in result], [1, 2, 3])

    def test_오늘_마감은_아직_열린_것으로_본다(self):
        listings = [FakeListing(1, date(2026, 8, 10))]

        result = move_closed_to_end(listings, self.today)

        self.assertEqual([x.id for x in result], [1])

    def test_마감일이_없으면_열린_것으로_본다(self):
        listings = [FakeListing(1, None), FakeListing(2, date(2026, 8, 1))]

        result = move_closed_to_end(listings, self.today)

        self.assertEqual([x.id for x in result], [1, 2])

    def test_빈_목록도_안전하다(self):
        self.assertEqual(move_closed_to_end([], self.today), [])


class SortApiTest(unittest.TestCase):
    """화면이 보낸 정렬 기준이 서비스까지 그대로 가는지 확인합니다."""

    def test_전체_조회에_정렬_기준을_넘긴다(self):
        with patch("app.routers.listing_router.listing_get_all", return_value=[]) as fake:
            response = client.get("/listings/getall", params={"sort": "area_desc"})

        self.assertEqual(response.status_code, 200)
        fake.assert_called_once_with(sort="area_desc")

    def test_정렬_기준을_보내지_않으면_기본이다(self):
        with patch("app.routers.listing_router.listing_get_all", return_value=[]) as fake:
            response = client.get("/listings/getall")

        self.assertEqual(response.status_code, 200)
        fake.assert_called_once_with(sort=None)

    def test_페이지_조회에도_정렬_기준을_넘긴다(self):
        with patch("app.routers.listing_router.listing_get_page") as fake:
            client.get("/listings/page", params={"page": 2, "sort": "deposit_asc"})

        fake.assert_called_once_with(page=2, page_size=10, sort="deposit_asc")

    def test_조건검색에도_정렬_기준을_넘긴다(self):
        with patch("app.routers.listing_router.listing_search", return_value=[]) as fake:
            response = client.get(
                "/listings/search", params={"location": "강서구", "sort": "rent_desc"}
            )

        self.assertEqual(response.status_code, 200)
        fake.assert_called_once_with(
            location="강서구",
            max_deposit=None,
            max_monthly_rent=None,
            sort="rent_desc",
        )

    def test_모르는_정렬_기준은_400으로_막는다(self):
        """조용히 무시하면 왜 순서가 안 바뀌는지 알기 어렵습니다."""
        response = client.get("/listings/getall", params={"sort": "엉뚱한값"})

        self.assertEqual(response.status_code, 400)
        # 이 프로젝트는 오류도 {success, message} 형태로 내보냅니다.
        body = response.json()
        self.assertFalse(body["success"])
        self.assertIn("엉뚱한값", body["message"])

    def test_모든_경로에서_모르는_기준을_막는다(self):
        for path in ("/listings/getall", "/listings/page", "/listings/search"):
            with self.subTest(path=path):
                response = client.get(path, params={"sort": "없는기준"})
                self.assertEqual(response.status_code, 400)

    def test_화면이_고를_수_있는_기준은_모두_통과한다(self):
        for key in SORT_COLUMNS:
            with self.subTest(sort=key):
                with patch(
                    "app.routers.listing_router.listing_get_all", return_value=[]
                ):
                    response = client.get("/listings/getall", params={"sort": key})
                self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
