# test_pagination.py
"""청약정보 목록 페이지 나누기 테스트.

Streamlit이나 서버에 연결하지 않는 순수 함수만 확인합니다.
"""

import unittest

from core.pagination import (
    PAGE_SIZE,
    build_params,
    clamp_page,
    parse_page,
    slice_page,
    total_pages,
)


def sample(count: int) -> list:
    """마감이 가까운 순으로 정렬된 목록을 흉내 냅니다."""
    return [{"id": i, "housing_name": f"공고 {i}"} for i in range(1, count + 1)]


def names(items) -> list:
    return [x["housing_name"] for x in items]


class PageSizeTest(unittest.TestCase):
    def test_한_페이지에_10건씩_보여_준다(self):
        """관리자 화면과 같은 값을 씁니다."""
        self.assertEqual(PAGE_SIZE, 10)


class ParsePageTest(unittest.TestCase):
    def test_정상적인_숫자는_그대로_쓴다(self):
        self.assertEqual(parse_page("5"), 5)
        self.assertEqual(parse_page(["3"]), 3)

    def test_값이_없으면_1페이지다(self):
        self.assertEqual(parse_page(None), 1)
        self.assertEqual(parse_page([]), 1)

    def test_숫자가_아니면_1페이지다(self):
        for bad in ("abc", "", "  ", "2.5"):
            self.assertEqual(parse_page(bad), 1, f"입력값 {bad!r}")

    def test_0이나_음수는_1페이지다(self):
        self.assertEqual(parse_page("0"), 1)
        self.assertEqual(parse_page("-3"), 1)


class TotalPagesTest(unittest.TestCase):
    def test_딱_나누어떨어지면_그만큼이다(self):
        self.assertEqual(total_pages(20), 2)
        self.assertEqual(total_pages(100), 10)

    def test_남으면_한_페이지_더_만든다(self):
        self.assertEqual(total_pages(21), 3)
        self.assertEqual(total_pages(112), 12)

    def test_공고가_없어도_1페이지다(self):
        self.assertEqual(total_pages(0), 1)

    def test_한_건이면_1페이지다(self):
        self.assertEqual(total_pages(1), 1)


class ClampPageTest(unittest.TestCase):
    def test_마지막_페이지를_넘으면_마지막으로_맞춘다(self):
        """공고가 지워져 페이지가 줄면 빈 화면이 나오지 않게 합니다."""
        self.assertEqual(clamp_page(99, 25), 3)

    def test_1보다_작으면_1페이지다(self):
        self.assertEqual(clamp_page(0, 25), 1)
        self.assertEqual(clamp_page(-5, 25), 1)

    def test_범위_안이면_그대로_둔다(self):
        self.assertEqual(clamp_page(2, 25), 2)

    def test_공고가_없으면_1페이지다(self):
        self.assertEqual(clamp_page(3, 0), 1)


class SlicePageTest(unittest.TestCase):
    def test_첫_페이지는_앞에서_10건이다(self):
        self.assertEqual(names(slice_page(sample(25), 1)), [f"공고 {i}" for i in range(1, 11)])

    def test_두_번째_페이지는_그다음_10건이다(self):
        self.assertEqual(names(slice_page(sample(25), 2)), [f"공고 {i}" for i in range(11, 21)])

    def test_마지막_페이지는_남은_만큼만이다(self):
        self.assertEqual(names(slice_page(sample(25), 3)), ["공고 21", "공고 22", "공고 23", "공고 24", "공고 25"])

    def test_서버가_준_순서를_그대로_지킨다(self):
        """마감이 가까운 순을 흐트러뜨리면 안 됩니다."""
        items = sample(25)
        self.assertEqual(names(slice_page(items, 1)), names(items[:10]))

    def test_원래_목록을_바꾸지_않는다(self):
        items = sample(25)
        before = names(items)

        slice_page(items, 2)

        self.assertEqual(names(items), before)

    def test_마지막_페이지를_넘는_번호도_안전하다(self):
        self.assertEqual(len(slice_page(sample(25), 99)), 5)

    def test_빈_목록도_안전하다(self):
        self.assertEqual(slice_page([], 1), [])

    def test_목록이_아니면_빈_결과다(self):
        self.assertEqual(slice_page(None, 1), [])
        self.assertEqual(slice_page({"a": 1}, 1), [])

    def test_모든_페이지를_모으면_원래_목록과_같다(self):
        items = sample(112)
        gathered = []
        for page in range(1, total_pages(len(items)) + 1):
            gathered.extend(slice_page(items, page))

        self.assertEqual(names(gathered), names(items))


class BuildParamsTest(unittest.TestCase):
    def test_페이지_번호만_담는다(self):
        self.assertEqual(build_params(3), {"page": "3"})

    def test_0이하면_1로_맞춘다(self):
        self.assertEqual(build_params(0), {"page": "1"})
        self.assertEqual(build_params(-2), {"page": "1"})

    def test_값은_문자열이다(self):
        self.assertTrue(all(isinstance(v, str) for v in build_params(2).values()))

    def test_개인정보는_담기지_않는다(self):
        self.assertEqual(set(build_params(2)), {"page"})


if __name__ == "__main__":
    unittest.main()
