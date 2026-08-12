# test_dday.py
"""신청 종료일 디데이 표시 테스트.

오늘 날짜를 직접 넘겨 확인하므로 실행하는 날과 상관없이 결과가 같습니다.
"""

import unittest
from datetime import date

from core.dday import days_left, dday_label, dim_if_closed, is_closed


TODAY = date(2026, 8, 10)


class DaysLeftTest(unittest.TestCase):
    def test_남은_날수를_센다(self):
        self.assertEqual(days_left("2026-08-20", TODAY), 10)
        self.assertEqual(days_left("2026-08-11", TODAY), 1)

    def test_오늘_마감이면_0이다(self):
        self.assertEqual(days_left("2026-08-10", TODAY), 0)

    def test_이미_지났으면_음수다(self):
        self.assertEqual(days_left("2026-08-05", TODAY), -5)

    def test_date_객체도_받는다(self):
        self.assertEqual(days_left(date(2026, 8, 20), TODAY), 10)

    def test_날짜로_읽을_수_없으면_None이다(self):
        for bad in (None, "", "abc", "2026-13-99", 123):
            self.assertIsNone(days_left(bad, TODAY), f"입력값 {bad!r}")


class DdayLabelTest(unittest.TestCase):
    def test_남았으면_D_빼기로_보여_준다(self):
        self.assertEqual(dday_label("2026-08-20", TODAY), "D-10")
        self.assertEqual(dday_label("2026-08-11", TODAY), "D-1")

    def test_오늘_마감이면_D_DAY다(self):
        self.assertEqual(dday_label("2026-08-10", TODAY), "D-DAY")

    def test_지났으면_마감이다(self):
        self.assertEqual(dday_label("2026-08-09", TODAY), "마감")

    def test_날짜를_모르면_아무것도_보여_주지_않는다(self):
        self.assertIsNone(dday_label(None, TODAY))
        self.assertIsNone(dday_label("abc", TODAY))


class IsClosedTest(unittest.TestCase):
    def test_지났으면_마감이다(self):
        self.assertTrue(is_closed("2026-08-09", TODAY))

    def test_오늘이나_이후면_마감이_아니다(self):
        self.assertFalse(is_closed("2026-08-10", TODAY))
        self.assertFalse(is_closed("2026-08-20", TODAY))

    def test_날짜를_모르면_마감으로_보지_않는다(self):
        """잘못된 값 때문에 신청할 수 있는 공고가 마감으로 보이면 안 됩니다."""
        self.assertFalse(is_closed(None, TODAY))
        self.assertFalse(is_closed("abc", TODAY))


class SortOrderTest(unittest.TestCase):
    """백엔드가 돌려주는 순서를 화면이 그대로 쓰는지 확인합니다."""

    def test_마감이_가까운_순서를_그대로_보여_준다(self):
        listings = [
            {"id": 1, "application_end_date": "2026-08-12"},
            {"id": 2, "application_end_date": "2026-08-10"},
            {"id": 3, "application_end_date": "2026-08-20"},
        ]
        labels = [dday_label(x["application_end_date"], TODAY) for x in listings]
        self.assertEqual(labels, ["D-2", "D-DAY", "D-10"])


class DimIfClosedTest(unittest.TestCase):
    """신청이 끝난 공고만 흐린 회색으로 바꿉니다."""

    def test_마감된_공고는_회색_표기를_붙인다(self):
        self.assertEqual(dim_if_closed("방화동원룸", True), ":gray[방화동원룸]")

    def test_마감되지_않은_공고는_그대로_둔다(self):
        self.assertEqual(dim_if_closed("방화동원룸", False), "방화동원룸")

    def test_대괄호가_있어도_표기가_깨지지_않는다(self):
        """제목에 [더미데이터] 같은 값이 들어올 수 있습니다."""
        result = dim_if_closed("[더미데이터] 공고", True)

        self.assertTrue(result.startswith(":gray["))
        self.assertTrue(result.endswith("]"))
        # 안쪽 대괄호가 남아 있으면 색 표기가 중간에서 끊깁니다.
        self.assertNotIn("[", result[6:-1])
        self.assertNotIn("]", result[6:-1])

    def test_대괄호를_비슷한_글자로_바꾼다(self):
        result = dim_if_closed("[공고]", True)
        self.assertIn("［공고］", result)

    def test_마감되지_않으면_대괄호를_바꾸지_않는다(self):
        self.assertEqual(dim_if_closed("[공고]", False), "[공고]")

    def test_값이_없어도_오류가_나지_않는다(self):
        self.assertEqual(dim_if_closed(None, False), "")
        self.assertEqual(dim_if_closed(None, True), ":gray[]")

    def test_숫자도_글자로_바꿔_처리한다(self):
        self.assertEqual(dim_if_closed(123, False), "123")


if __name__ == "__main__":
    unittest.main()
