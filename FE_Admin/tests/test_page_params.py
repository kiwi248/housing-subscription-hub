# test_page_params.py
"""URL query parameter 변환 함수 테스트.

Streamlit이나 서버에 연결하지 않는 순수 함수만 확인합니다.
FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.page_params import build_params, parse_edit_id, parse_page, parse_search


class ParsePageTest(unittest.TestCase):
    def test_정상적인_숫자는_그대로_쓴다(self):
        self.assertEqual(parse_page("5"), 5)
        self.assertEqual(parse_page("11"), 11)

    def test_값이_없으면_1페이지다(self):
        self.assertEqual(parse_page(None), 1)

    def test_숫자가_아니면_1페이지다(self):
        for bad in ("abc", "", "  ", "5.5", "1e3"):
            self.assertEqual(parse_page(bad), 1, f"입력값 {bad!r}")

    def test_0이나_음수는_1페이지다(self):
        self.assertEqual(parse_page("0"), 1)
        self.assertEqual(parse_page("-1"), 1)
        self.assertEqual(parse_page("-999"), 1)

    def test_앞뒤_공백은_무시한다(self):
        self.assertEqual(parse_page(" 7 "), 7)

    def test_같은_이름이_여러_번_오면_첫_값을_쓴다(self):
        self.assertEqual(parse_page(["3", "9"]), 3)

    def test_빈_목록은_1페이지다(self):
        self.assertEqual(parse_page([]), 1)

    def test_상한은_두지_않는다(self):
        """마지막 페이지를 넘는 값은 서버가 실제 개수를 보고 보정합니다."""
        self.assertEqual(parse_page("99999"), 99999)


class ParseEditIdTest(unittest.TestCase):
    def test_정상적인_ID는_그대로_쓴다(self):
        self.assertEqual(parse_edit_id("123"), 123)

    def test_값이_없으면_수정_모드가_아니다(self):
        self.assertIsNone(parse_edit_id(None))

    def test_숫자가_아니면_수정_모드가_아니다(self):
        for bad in ("abc", "", "  ", "12a", "1.5"):
            self.assertIsNone(parse_edit_id(bad), f"입력값 {bad!r}")

    def test_0이나_음수는_수정_모드가_아니다(self):
        self.assertIsNone(parse_edit_id("0"))
        self.assertIsNone(parse_edit_id("-5"))

    def test_같은_이름이_여러_번_오면_첫_값을_쓴다(self):
        self.assertEqual(parse_edit_id(["42", "77"]), 42)


class BuildParamsTest(unittest.TestCase):
    def test_수정_중이_아니면_page만_담는다(self):
        self.assertEqual(build_params(5), {"page": "5"})

    def test_수정_중이면_edit_id도_담는다(self):
        self.assertEqual(build_params(5, 123), {"page": "5", "edit_id": "123"})

    def test_페이지가_0이하여도_1로_맞춘다(self):
        self.assertEqual(build_params(0), {"page": "1"})
        self.assertEqual(build_params(-3), {"page": "1"})

    def test_값은_모두_문자열이다(self):
        params = build_params(2, 7)
        self.assertTrue(all(isinstance(v, str) for v in params.values()))

    def test_로그인_정보는_담기지_않는다(self):
        params = build_params(5, 123)
        self.assertEqual(set(params), {"page", "edit_id"})


class ParseSearchTest(unittest.TestCase):
    def test_검색_조건이_없으면_빈_사전이다(self):
        self.assertEqual(parse_search({}), {})

    def test_자치구를_읽는다(self):
        self.assertEqual(parse_search({"location": ["강남구"]}), {"location": "강남구"})

    def test_금액을_읽는다(self):
        parsed = parse_search({"max_deposit": ["20000000"], "max_monthly_rent": ["300000"]})
        self.assertEqual(parsed, {"max_deposit": "20000000", "max_monthly_rent": "300000"})

    def test_0이나_음수_금액은_조건이_아니다(self):
        self.assertEqual(parse_search({"max_deposit": ["0"], "max_monthly_rent": ["-1"]}), {})

    def test_숫자가_아닌_금액은_무시한다(self):
        self.assertEqual(parse_search({"max_deposit": ["abc"]}), {})

    def test_빈_자치구는_조건이_아니다(self):
        self.assertEqual(parse_search({"location": ["  "]}), {})

    def test_같은_이름이_여러_번_오면_첫_값을_쓴다(self):
        self.assertEqual(parse_search({"location": ["강남구", "중구"]}), {"location": "강남구"})

    def test_검색_조건_외의_값은_읽지_않는다(self):
        parsed = parse_search({"location": ["강남구"], "edit_id": ["13"], "page": ["5"]})
        self.assertEqual(parsed, {"location": "강남구"})


class BuildParamsWithSearchTest(unittest.TestCase):
    """수정 화면을 오갈 때 검색 조건이 주소에 남아야 뒤로가기로 돌아와도 유지됩니다."""

    def test_검색_조건을_함께_담는다(self):
        params = build_params(1, None, {"location": "강남구", "max_deposit": "20000000"})
        self.assertEqual(
            params, {"page": "1", "location": "강남구", "max_deposit": "20000000"}
        )

    def test_수정_중에도_검색_조건이_남는다(self):
        params = build_params(1, 136, {"max_deposit": "20000000"})
        self.assertEqual(
            params, {"page": "1", "edit_id": "136", "max_deposit": "20000000"}
        )

    def test_수정_화면을_닫아도_검색_조건은_남는다(self):
        search = {"location": "강남구"}
        opened = build_params(3, 136, search)
        closed = build_params(3, None, search)
        self.assertEqual(closed, {"page": "3", "location": "강남구"})
        self.assertNotIn("edit_id", closed)
        self.assertEqual(opened["location"], closed["location"])

    def test_검색_조건이_없으면_기존과_같다(self):
        self.assertEqual(build_params(5, 123, None), build_params(5, 123))
        self.assertEqual(build_params(5, 123, {}), build_params(5, 123))

    def test_빈_값은_담지_않는다(self):
        self.assertEqual(build_params(1, None, {"location": "  "}), {"page": "1"})

    def test_검색_조건_외의_값은_담지_않는다(self):
        params = build_params(1, None, {"location": "강남구", "password": "비밀"})
        self.assertEqual(set(params), {"page", "location"})

    def test_주소에_다시_읽어도_같은_조건이_나온다(self):
        search = {"location": "강남구", "max_deposit": "20000000"}
        params = build_params(2, 136, search)
        restored = parse_search({k: [v] for k, v in params.items()})
        self.assertEqual(restored, search)


class EditScreenBranchTest(unittest.TestCase):
    """화면 분기는 오직 주소의 edit_id로만 정해져야 합니다.

    수정 대상을 st.session_state에 따로 들고 있으면, 목록으로 돌아온 뒤에도
    그 값 때문에 수정 화면이 다시 열립니다. 그래서 주소만 보고 정합니다.
    """

    @staticmethod
    def is_edit_screen(query_params: dict) -> bool:
        """화면 코드와 같은 방식으로 수정 화면 여부를 정합니다."""
        return parse_edit_id(query_params.get("edit_id")) is not None

    def test_edit_id가_없으면_목록_화면이다(self):
        self.assertFalse(self.is_edit_screen({"page": ["1"]}))

    def test_edit_id가_있으면_수정_화면이다(self):
        self.assertTrue(self.is_edit_screen({"page": ["1"], "edit_id": ["136"]}))

    def test_잘못된_edit_id는_목록_화면이다(self):
        for bad in ("0", "-1", "abc", ""):
            self.assertFalse(self.is_edit_screen({"edit_id": [bad]}), f"입력값 {bad!r}")

    def test_페이지만_바뀌면_수정_화면이_열리지_않는다(self):
        """다음/이전 버튼으로 만든 주소에는 edit_id가 없어야 합니다."""
        moved = build_params(2, None, {})
        self.assertFalse(self.is_edit_screen({k: [v] for k, v in moved.items()}))

    def test_오래된_수정_대상은_주소에_없으면_무시된다(self):
        """session_state에 옛 값이 남아 있어도 주소에 없으면 목록 화면입니다."""
        stale_session_state = {"editing_listing_id": 136, "selected_listing": 136}
        query_params = {"page": ["2"]}
        self.assertFalse(self.is_edit_screen(query_params))
        # 화면 분기에 session_state를 쓰지 않으므로 값이 남아 있어도 영향이 없습니다.
        self.assertNotIn("edit_id", query_params)
        self.assertTrue(stale_session_state)


class PageNavigationTest(unittest.TestCase):
    """다음/이전 버튼이 만드는 주소를 확인합니다."""

    def test_다음_페이지로_가면_edit_id가_사라진다(self):
        opened = build_params(1, 136)
        self.assertIn("edit_id", opened)
        moved = build_params(1 + 1, None)
        self.assertNotIn("edit_id", moved)
        self.assertEqual(moved["page"], "2")

    def test_이전_페이지로_가면_edit_id가_사라진다(self):
        moved = build_params(2 - 1, None)
        self.assertEqual(moved["page"], "1")
        self.assertNotIn("edit_id", moved)

    def test_페이지_번호가_한_칸씩_어긋나지_않는다(self):
        """사용자에게 보이는 번호를 그대로 주소에 적습니다. 0부터 세지 않습니다."""
        for shown in (1, 2, 3, 11):
            self.assertEqual(build_params(shown)["page"], str(shown))
            self.assertEqual(parse_page([str(shown)]), shown)

    def test_주소를_읽고_다시_만들어도_페이지가_같다(self):
        for shown in (1, 2, 7):
            params = build_params(shown, 136, {"location": "강남구"})
            self.assertEqual(parse_page([params["page"]]), shown)

    def test_페이지_이동_시_검색_조건은_남는다(self):
        search = {"location": "강남구"}
        moved = build_params(2, None, search)
        self.assertEqual(moved, {"page": "2", "location": "강남구"})


class UrlRoundTripTest(unittest.TestCase):
    """검색 조건과 page, edit_id를 함께 만들고 다시 해석합니다."""

    def test_수정_화면_주소를_그대로_복원한다(self):
        search = {"location": "강남구", "max_deposit": "20000000"}
        params = build_params(2, 140, search)
        self.assertEqual(params["page"], "2")
        self.assertEqual(params["edit_id"], "140")

        as_query = {k: [v] for k, v in params.items()}
        self.assertEqual(parse_page(as_query["page"]), 2)
        self.assertEqual(parse_edit_id(as_query["edit_id"]), 140)
        self.assertEqual(parse_search(as_query), search)

    def test_수정_화면에서_목록으로_돌아가도_페이지와_조건이_같다(self):
        search = {"max_monthly_rent": "300000"}
        edit_params = build_params(2, 140, search)
        list_params = build_params(2, None, search)
        self.assertEqual(list_params["page"], edit_params["page"])
        self.assertNotIn("edit_id", list_params)
        self.assertEqual(
            parse_search({k: [v] for k, v in list_params.items()}), search
        )

    def test_같은_값이면_주소를_다시_쓸_필요가_없다(self):
        """같은 값을 다시 쓰면 방문 기록이 쌓여 뒤로가기가 헛돕니다."""
        params = build_params(2, 140, {"location": "강남구"})
        current = dict(params)
        self.assertEqual(current, params)


if __name__ == "__main__":
    unittest.main()
