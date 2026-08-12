# test_bulk_delete.py
"""여러 공고를 한 번에 지울 때 쓰는 규칙 테스트.

지우는 일은 되돌릴 수 없어, 무엇을 지우는지 정확히 세는 부분을 확인합니다.

FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.bulk_delete import (
    MAX_DELETE_COUNT,
    can_delete,
    checkbox_key,
    names_of,
    picked_ids,
    set_all,
    summarize_deletes,
)


def listing(listing_id: int, housing_name: str = "테스트하우스") -> dict:
    return {"id": listing_id, "housing_name": housing_name, "title": "모집공고"}


class CheckboxKeyTest(unittest.TestCase):
    def test_공고마다_다른_이름이_나온다(self):
        self.assertNotEqual(checkbox_key(1), checkbox_key(2))

    def test_같은_공고면_같은_이름이다(self):
        self.assertEqual(checkbox_key(7), checkbox_key(7))


class PickedIdsTest(unittest.TestCase):
    """고른 상태는 선택칸에서만 읽습니다."""

    def test_켜진_것만_센다(self):
        state = {checkbox_key(1): True, checkbox_key(2): False, checkbox_key(3): True}

        self.assertEqual(picked_ids(state, [1, 2, 3]), [1, 3])

    def test_목록_순서를_따른다(self):
        state = {checkbox_key(1): True, checkbox_key(2): True}

        self.assertEqual(picked_ids(state, [2, 1]), [2, 1])

    def test_아무것도_안_골랐으면_빈_목록이다(self):
        self.assertEqual(picked_ids({}, [1, 2]), [])

    def test_이_페이지에_없는_공고는_세지_않는다(self):
        """페이지를 넘기면 선택이 풀립니다. 안 보이는 공고를 지우면 사고입니다."""
        state = {checkbox_key(99): True}

        self.assertEqual(picked_ids(state, [1, 2]), [])

    def test_페이지가_비어_있어도_안전하다(self):
        self.assertEqual(picked_ids({checkbox_key(1): True}, []), [])
        self.assertEqual(picked_ids({}, None), [])

    def test_숫자가_아닌_번호는_건너뛴다(self):
        state = {checkbox_key(1): True}

        self.assertEqual(picked_ids(state, [1, "번호아님"]), [1])


class SetAllTest(unittest.TestCase):
    def test_한꺼번에_켠다(self):
        state = {}

        changed = set_all(state, [1, 2, 3], True)

        self.assertEqual(changed, 3)
        self.assertEqual(picked_ids(state, [1, 2, 3]), [1, 2, 3])

    def test_한꺼번에_끈다(self):
        state = {}
        set_all(state, [1, 2, 3], True)

        set_all(state, [1, 2, 3], False)

        self.assertEqual(picked_ids(state, [1, 2, 3]), [])

    def test_값을_직접_넣는다(self):
        """지우기만 해서는 켜지지 않습니다. Streamlit이 저장된 값을 먼저 봅니다."""
        state = {}

        set_all(state, [1], True)

        self.assertIs(state[checkbox_key(1)], True)

    def test_다른_페이지_선택칸은_건드리지_않는다(self):
        state = {checkbox_key(99): True}

        set_all(state, [1, 2], False)

        self.assertTrue(state[checkbox_key(99)])

    def test_빈_페이지도_안전하다(self):
        self.assertEqual(set_all({}, [], True), 0)
        self.assertEqual(set_all({}, None, True), 0)


class NamesOfTest(unittest.TestCase):
    def setUp(self):
        self.listings = [listing(1, "방화동원룸 13㎡형"), listing(2, "문정동원룸 14㎡형")]

    def test_번호와_이름을_함께_보여_준다(self):
        self.assertEqual(
            names_of([1, 2], self.listings),
            ["#1  방화동원룸 13㎡형", "#2  문정동원룸 14㎡형"],
        )

    def test_목록에_없는_공고는_번호만_보여_준다(self):
        self.assertEqual(names_of([9], self.listings), ["#9"])

    def test_이름이_없으면_번호만_보여_준다(self):
        self.assertEqual(names_of([1], [{"id": 1, "housing_name": "", "title": ""}]), ["#1"])

    def test_고른_순서를_지킨다(self):
        self.assertEqual([x[:2] for x in names_of([2, 1], self.listings)], ["#2", "#1"])

    def test_빈_값도_안전하다(self):
        self.assertEqual(names_of([], self.listings), [])
        self.assertEqual(names_of([1], None), ["#1"])


class CanDeleteTest(unittest.TestCase):
    def test_고른_것이_있으면_지울_수_있다(self):
        allowed, reason = can_delete([1, 2])

        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_아무것도_안_골랐으면_막는다(self):
        allowed, reason = can_delete([])

        self.assertFalse(allowed)
        self.assertIn("골라", reason)

    def test_너무_많이_고르면_막는다(self):
        """실수로 많은 공고를 한꺼번에 지우는 일을 막습니다."""
        allowed, reason = can_delete(list(range(MAX_DELETE_COUNT + 1)))

        self.assertFalse(allowed)
        self.assertIn(str(MAX_DELETE_COUNT), reason)

    def test_상한만큼은_지울_수_있다(self):
        allowed, _ = can_delete(list(range(MAX_DELETE_COUNT)))

        self.assertTrue(allowed)


class SummarizeDeletesTest(unittest.TestCase):
    def test_모두_지웠으면_건수만_알려_준다(self):
        self.assertEqual(summarize_deletes([1, 2, 3], []), "3건을 삭제했습니다.")

    def test_일부만_실패하면_둘_다_알려_준다(self):
        message = summarize_deletes([1, 2], [3])

        self.assertIn("2건", message)
        self.assertIn("1건", message)

    def test_모두_실패하면_실패만_알려_준다(self):
        self.assertEqual(summarize_deletes([], [1, 2]), "2건을 삭제하지 못했습니다.")

    def test_아무것도_없으면_안내한다(self):
        self.assertEqual(summarize_deletes([], []), "삭제한 공고가 없습니다.")


class SelectionFlowTest(unittest.TestCase):
    """전체 선택 뒤 하나만 풀었을 때 나머지가 유지되는지 봅니다."""

    def test_하나만_풀어도_나머지는_남는다(self):
        """실제로 9건 → 8건 → 7건으로 줄줄이 풀리는 문제가 있었습니다."""
        state = {}
        page = [1, 2, 3, 4, 5]
        set_all(state, page, True)

        state[checkbox_key(3)] = False

        self.assertEqual(picked_ids(state, page), [1, 2, 4, 5])

    def test_다시_전체_선택하면_모두_켜진다(self):
        state = {}
        page = [1, 2, 3]
        set_all(state, page, True)
        state[checkbox_key(2)] = False

        set_all(state, page, True)

        self.assertEqual(picked_ids(state, page), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
