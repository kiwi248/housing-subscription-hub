# test_listing_order.py
"""청약정보 조회 정렬 기준 테스트.

실제 Supabase에는 연결하지 않고, 어떤 정렬을 요청했는지만 확인합니다.
"""

import unittest
from unittest.mock import patch


class FakeQuery:
    """supabase 쿼리 빌더를 흉내 내며 order 호출을 기록합니다."""

    def __init__(self, log):
        self.log = log

    def select(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def order(self, column, desc=False, **kwargs):
        self.log.append((column, desc))
        return self

    def execute(self):
        class Result:
            data = []

        return Result()


class FakeSupabase:
    def __init__(self, log):
        self.log = log

    def table(self, name):
        return FakeQuery(self.log)


class ListingOrderTest(unittest.TestCase):
    def _orders_for(self, call):
        from app.services import listing_service

        log = []
        with patch.object(listing_service, "get_supabase", return_value=FakeSupabase(log)):
            call(listing_service)
        return log

    def test_전체_조회는_마감이_가까운_순이다(self):
        orders = self._orders_for(lambda svc: svc.listing_get_all())

        self.assertEqual(orders[0], ("application_end_date", False))

    def test_전체_조회는_동률이면_등록_최신순이다(self):
        orders = self._orders_for(lambda svc: svc.listing_get_all())

        self.assertEqual(orders[1], ("created_at", True))
        self.assertEqual(orders[2], ("id", True))

    def test_검색도_같은_기준을_쓴다(self):
        orders = self._orders_for(
            lambda svc: svc.listing_search(
                location="강남구", max_deposit=None, max_monthly_rent=None
            )
        )

        self.assertEqual(
            orders, [("application_end_date", False), ("created_at", True), ("id", True)]
        )

    def test_시작일_기준_정렬은_더_이상_쓰지_않는다(self):
        orders = self._orders_for(lambda svc: svc.listing_get_all())

        self.assertNotIn("application_start_date", [column for column, _ in orders])

    def test_마감일은_오름차순이다(self):
        """가장 임박한 공고가 앞에 와야 하므로 내림차순이면 안 됩니다."""
        orders = self._orders_for(lambda svc: svc.listing_get_all())

        column, desc = orders[0]
        self.assertEqual(column, "application_end_date")
        self.assertFalse(desc)


class MoveClosedToEndTest(unittest.TestCase):
    """신청이 끝난 공고를 목록 맨 뒤로 보냅니다."""

    @staticmethod
    def _listing(listing_id: int, end: str):
        from datetime import date, datetime
        from decimal import Decimal

        from app.schemas.listing_schema import ListingPublic

        return ListingPublic(
            id=listing_id,
            title="공고",
            housing_name="주택",
            area_sqm=Decimal("20.00"),
            recruitment_count=1,
            location="중구",
            deposit=0,
            monthly_rent=0,
            application_start_date=date(2026, 1, 1),
            application_end_date=date.fromisoformat(end),
            description="설명",
            image_url=None,
            source_url="https://example.com",
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )

    def test_마감된_공고가_뒤로_간다(self):
        from datetime import date

        from app.services.listing_service import move_closed_to_end

        today = date(2026, 8, 10)
        # 들어오는 순서는 마감일 오름차순입니다.
        listings = [
            self._listing(1, "2026-08-01"),  # 마감
            self._listing(2, "2026-08-05"),  # 마감
            self._listing(3, "2026-08-10"),  # 오늘 마감 - 아직 신청 가능
            self._listing(4, "2026-08-20"),
        ]

        result = move_closed_to_end(listings, today)

        self.assertEqual([x.id for x in result], [3, 4, 2, 1])

    def test_오늘_마감은_아직_신청할_수_있는_것으로_본다(self):
        from datetime import date

        from app.services.listing_service import move_closed_to_end

        result = move_closed_to_end([self._listing(1, "2026-08-10")], date(2026, 8, 10))

        self.assertEqual([x.id for x in result], [1])

    def test_마감된_것끼리는_최근에_끝난_순이다(self):
        from datetime import date

        from app.services.listing_service import move_closed_to_end

        listings = [
            self._listing(1, "2026-07-01"),
            self._listing(2, "2026-08-01"),
        ]

        result = move_closed_to_end(listings, date(2026, 8, 10))

        self.assertEqual([x.id for x in result], [2, 1])

    def test_건수가_줄지_않는다(self):
        from datetime import date

        from app.services.listing_service import move_closed_to_end

        listings = [self._listing(i, "2026-08-01") for i in range(5)]

        self.assertEqual(len(move_closed_to_end(listings, date(2026, 8, 10))), 5)

    def test_모두_신청_가능하면_순서가_그대로다(self):
        from datetime import date

        from app.services.listing_service import move_closed_to_end

        listings = [self._listing(1, "2026-08-20"), self._listing(2, "2026-08-25")]

        result = move_closed_to_end(listings, date(2026, 8, 10))

        self.assertEqual([x.id for x in result], [1, 2])

    def test_빈_목록도_안전하다(self):
        from datetime import date

        from app.services.listing_service import move_closed_to_end

        self.assertEqual(move_closed_to_end([], date(2026, 8, 10)), [])


if __name__ == "__main__":
    unittest.main()
