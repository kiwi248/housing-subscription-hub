# test_listing_page.py
"""청약정보 페이지 조회 테스트.

실제 Supabase에는 연결하지 않습니다.
supabase 클라이언트를 흉내 내는 가짜 객체로 정렬과 범위 조회를 확인합니다.
"""

import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.listing_schema import ListingPage, ListingPublic
from app.services import listing_service


client = TestClient(app)

BASE_TIME = datetime(2026, 8, 1, 9, 0, 0)


def make_row(listing_id: int, created_at: datetime) -> dict:
    """DB에서 읽어온 한 줄을 흉내 냅니다."""
    return {
        "id": listing_id,
        "title": f"[테스트] 공고 {listing_id}",
        "housing_name": "테스트하우스",
        "area_sqm": "25.00",
        "recruitment_count": 3,
        "location": "중구",
        "deposit": 10000000,
        "monthly_rent": 200000,
        "application_start_date": "2026-08-01",
        "application_end_date": "2026-08-31",
        "description": "설명",
        "image_url": None,
        "source_url": "https://example.com/test",
        "created_at": created_at.isoformat(),
    }


class FakeResult:
    def __init__(self, data, count):
        self.data = data
        self.count = count


class FakeQuery:
    """supabase.table("listings")가 돌려주는 객체를 흉내 냅니다.

    실제 Supabase처럼 범위를 넘는 요청에는 오류를 냅니다.
    """

    def __init__(self, rows, log):
        self.rows = rows
        self.log = log
        self.start = None
        self.end = None
        self.count_mode = None

    def select(self, columns, count=None):
        self.count_mode = count
        self.log.setdefault("select", []).append((columns, count))
        return self

    def order(self, column, desc=False, nullsfirst=None):
        # nullsfirst는 값이 비어 있는 공고를 어디에 둘지 정합니다.
        self.log.setdefault("order", []).append((column, desc))
        return self

    def limit(self, size):
        self.log.setdefault("limit", []).append(size)
        return self

    def range(self, start, end):
        self.start, self.end = start, end
        self.log.setdefault("range", []).append((start, end))
        return self

    def execute(self):
        # 개수만 세는 조회입니다.
        if self.start is None:
            return FakeResult(self.rows[:1], len(self.rows))

        # 실제 Supabase는 데이터가 없는 범위를 요청하면 오류를 냅니다.
        if self.rows and self.start >= len(self.rows):
            raise RuntimeError("Requested range not satisfiable")

        # 서버가 정렬해서 준 것처럼 created_at 내림차순, id 내림차순으로 맞춥니다.
        ordered = sorted(self.rows, key=lambda r: (r["created_at"], r["id"]), reverse=True)
        return FakeResult(ordered[self.start : self.end + 1], len(self.rows))


class FakeSupabase:
    def __init__(self, rows, log):
        self.rows = rows
        self.log = log

    def table(self, name):
        self.log["table"] = name
        return FakeQuery(self.rows, self.log)


def run_page(rows, page=1, page_size=10):
    log = {}
    with patch.object(listing_service, "get_supabase", return_value=FakeSupabase(rows, log)):
        result = listing_service.listing_get_page(page=page, page_size=page_size)
    return result, log


class ListingPageServiceTest(unittest.TestCase):
    def setUp(self):
        # 109건. id가 클수록 최근에 등록된 것으로 만듭니다.
        self.rows_109 = [
            make_row(i, BASE_TIME + timedelta(minutes=i)) for i in range(1, 110)
        ]

    def test_기본값은_1페이지_10건이다(self):
        result, _ = run_page(self.rows_109)
        self.assertIsInstance(result, ListingPage)
        self.assertEqual(result.page, 1)
        self.assertEqual(result.page_size, 10)
        self.assertEqual(len(result.items), 10)

    def test_등록시각_내림차순으로_정렬한다(self):
        result, log = run_page(self.rows_109)
        self.assertEqual(log["order"], [("created_at", True), ("id", True)])
        # 가장 최근(id 109)이 맨 위에 옵니다.
        self.assertEqual(result.items[0].id, 109)
        self.assertEqual(result.items[-1].id, 100)

    def test_등록시각이_같으면_id_내림차순이다(self):
        same_time = [make_row(i, BASE_TIME) for i in (1, 2, 3)]
        result, log = run_page(same_time, page_size=10)
        self.assertEqual(log["order"], [("created_at", True), ("id", True)])
        self.assertEqual([x.id for x in result.items], [3, 2, 1])

    def test_109건이면_전체_11페이지다(self):
        result, _ = run_page(self.rows_109)
        self.assertEqual(result.total_count, 109)
        self.assertEqual(result.total_pages, 11)

    def test_마지막_페이지는_9건이다(self):
        result, _ = run_page(self.rows_109, page=11)
        self.assertEqual(result.page, 11)
        self.assertEqual(len(result.items), 9)

    def test_전체를_가져오지_않고_범위만_요청한다(self):
        _, log = run_page(self.rows_109, page=3, page_size=10)
        # 3페이지는 21번째부터 30번째까지 (0부터 세면 20~29)
        self.assertEqual(log["range"], [(20, 29)])
        # 개수 조회 -> 목록 조회 순서로 두 번 호출합니다.
        # 사진은 listing_images 테이블에 따로 있어 함께 읽어 옵니다.
        self.assertEqual(
            log["select"],
            [("id", "exact"), ("*, listing_images(image_url, sort_order)", None)],
        )

    def test_0건이어도_정상_응답한다(self):
        result, _ = run_page([])
        self.assertEqual(result.items, [])
        self.assertEqual(result.total_count, 0)
        self.assertEqual(result.total_pages, 1)
        self.assertEqual(result.page, 1)

    def test_범위를_넘는_페이지는_마지막_페이지로_맞춘다(self):
        result, _ = run_page(self.rows_109, page=99)
        self.assertEqual(result.page, 11)
        self.assertEqual(len(result.items), 9)

    def test_0이나_음수_페이지는_1페이지로_맞춘다(self):
        for bad_page in (0, -5):
            result, _ = run_page(self.rows_109, page=bad_page)
            self.assertEqual(result.page, 1)
            self.assertEqual(len(result.items), 10)

    def test_너무_큰_page_size는_제한된다(self):
        result, log = run_page(self.rows_109, page_size=99999)
        self.assertEqual(result.page_size, listing_service.MAX_PAGE_SIZE)
        self.assertEqual(log["range"], [(0, listing_service.MAX_PAGE_SIZE - 1)])

    def test_0이하_page_size는_1로_맞춘다(self):
        result, _ = run_page(self.rows_109, page_size=0)
        self.assertEqual(result.page_size, 1)
        self.assertEqual(result.total_pages, 109)

    def test_정확히_10건이면_1페이지다(self):
        rows = [make_row(i, BASE_TIME + timedelta(minutes=i)) for i in range(1, 11)]
        result, _ = run_page(rows)
        self.assertEqual(result.total_pages, 1)
        self.assertEqual(len(result.items), 10)


class ListingPageApiTest(unittest.TestCase):
    """/listings/page 엔드포인트를 확인합니다."""

    def fake_page(self, page=1, page_size=10, total_count=109):
        return ListingPage(
            items=[
                ListingPublic(
                    id=1,
                    title="[테스트] 공고",
                    housing_name="테스트하우스",
                    area_sqm=Decimal("25.00"),
                    recruitment_count=3,
                    location="중구",
                    deposit=10000000,
                    monthly_rent=200000,
                    application_start_date=date(2026, 8, 1),
                    application_end_date=date(2026, 8, 31),
                    description="설명",
                    image_url=None,
                    source_url="https://example.com/test",
                    created_at=BASE_TIME,
                )
            ],
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=11,
        )

    def test_기본_호출은_1페이지_10건을_요청한다(self):
        with patch("app.routers.listing_router.listing_get_page", return_value=self.fake_page()) as fake:
            response = client.get("/listings/page")

        self.assertEqual(response.status_code, 200)
        fake.assert_called_once_with(page=1, page_size=10, sort=None)
        body = response.json()["data"]
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], 10)
        self.assertEqual(body["total_count"], 109)
        self.assertEqual(body["total_pages"], 11)
        self.assertIn("items", body)

    def test_page와_page_size를_전달한다(self):
        with patch("app.routers.listing_router.listing_get_page", return_value=self.fake_page(page=3)) as fake:
            response = client.get("/listings/page", params={"page": 3, "page_size": 20})

        self.assertEqual(response.status_code, 200)
        fake.assert_called_once_with(page=3, page_size=20, sort=None)

    def test_잘못된_페이지_번호는_422로_막는다(self):
        response = client.get("/listings/page", params={"page": 0})
        self.assertEqual(response.status_code, 422)

    def test_너무_큰_page_size는_422로_막는다(self):
        response = client.get("/listings/page", params={"page_size": 99999})
        self.assertEqual(response.status_code, 422)

    def test_기존_전체조회는_그대로_리스트를_돌려준다(self):
        """페이지 조회를 추가해도 사용자 화면이 쓰는 /getall은 바뀌지 않아야 합니다."""
        from app.schemas.listing_schema import ListingPublic as LP

        item = LP(
            id=1, title="t", housing_name="h", area_sqm=Decimal("25.00"),
            recruitment_count=3, location="중구", deposit=1, monthly_rent=1,
            application_start_date=date(2026, 8, 1), application_end_date=date(2026, 8, 31),
            description="d", image_url=None, source_url="https://example.com/x",
            created_at=BASE_TIME,
        )
        with patch("app.routers.listing_router.listing_get_all", return_value=[item]):
            response = client.get("/listings/getall")

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()["data"], list)


if __name__ == "__main__":
    unittest.main()
