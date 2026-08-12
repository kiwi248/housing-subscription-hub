# test_create_form.py
"""청약정보 등록 폼 입력값 초기화 테스트.

Streamlit이나 서버에 연결하지 않는 순수 함수만 확인합니다.
FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.create_form import (
    CREATE_FORM_FIELDS,
    NONCE_KEY,
    current_nonce,
    field_key,
    form_key,
    reset_form_state,
)


def filled_state(nonce: int = 0) -> dict:
    """등록 폼에 값이 들어 있는 상태를 흉내 냅니다."""
    state = {field_key(field, nonce): f"{field} 값" for field in CREATE_FORM_FIELDS}
    if nonce:
        state[NONCE_KEY] = nonce
    return state


class FormFieldsTest(unittest.TestCase):
    def test_등록_폼_입력칸이_모두_들어_있다(self):
        expected = {
            "title", "housing-name", "area-sqm", "recruitment-count", "location",
            "detail-address", "deposit", "monthly-rent", "start-date", "end-date",
            "description", "image", "source-url",
        }
        self.assertEqual(set(CREATE_FORM_FIELDS), expected)

    def test_상세주소_입력칸도_초기화_대상이다(self):
        """상세주소가 남아 있으면 다른 공고를 넣을 때 헷갈립니다."""
        self.assertIn("detail-address", CREATE_FORM_FIELDS)

    def test_이름이_겹치지_않는다(self):
        self.assertEqual(len(CREATE_FORM_FIELDS), len(set(CREATE_FORM_FIELDS)))


class KeyTest(unittest.TestCase):
    def test_입력칸_이름에_폼_번호가_들어간다(self):
        self.assertEqual(field_key("title", 0), "create-title-0")
        self.assertEqual(field_key("title", 3), "create-title-3")

    def test_폼_번호가_다르면_이름도_다르다(self):
        """이름이 달라져야 브라우저가 새 입력칸으로 보고 값을 비웁니다."""
        self.assertNotEqual(field_key("title", 0), field_key("title", 1))
        self.assertNotEqual(form_key(0), form_key(1))

    def test_모두_create_로_시작한다(self):
        for field in CREATE_FORM_FIELDS:
            self.assertTrue(field_key(field, 0).startswith("create-"))


class CurrentNonceTest(unittest.TestCase):
    def test_처음에는_0이다(self):
        self.assertEqual(current_nonce({}), 0)

    def test_저장된_번호를_읽는다(self):
        self.assertEqual(current_nonce({NONCE_KEY: 5}), 5)

    def test_이상한_값이면_0으로_본다(self):
        self.assertEqual(current_nonce({NONCE_KEY: "abc"}), 0)
        self.assertEqual(current_nonce({NONCE_KEY: None}), 0)


class ResetFormStateTest(unittest.TestCase):
    def test_입력값을_모두_지운다(self):
        state = filled_state()

        reset_form_state(state)

        remaining = [k for k in state if k.startswith("create-") and k != NONCE_KEY]
        self.assertEqual(remaining, [])

    def test_폼_번호를_올린다(self):
        """번호가 올라가야 브라우저에 남은 입력까지 사라집니다."""
        state = filled_state()

        new_nonce = reset_form_state(state)

        self.assertEqual(new_nonce, 1)
        self.assertEqual(state[NONCE_KEY], 1)

    def test_초기화를_반복하면_번호가_계속_올라간다(self):
        state = filled_state()

        reset_form_state(state)
        second = reset_form_state(state)

        self.assertEqual(second, 2)

    def test_새_번호의_입력칸은_비어_있다(self):
        state = filled_state()

        new_nonce = reset_form_state(state)

        for field in CREATE_FORM_FIELDS:
            self.assertNotIn(field_key(field, new_nonce), state)

    def test_등록_폼과_상관없는_값은_지우지_않는다(self):
        """로그인 정보처럼 다른 값까지 지우면 화면이 로그아웃됩니다."""
        state = filled_state()
        state.update({"loginout": "login", "admin_username": "tester"})

        reset_form_state(state)

        self.assertEqual(state["loginout"], "login")
        self.assertEqual(state["admin_username"], "tester")

    def test_값이_없어도_오류가_나지_않는다(self):
        state = {}

        new_nonce = reset_form_state(state)

        self.assertEqual(new_nonce, 1)

    def test_이전_번호의_값은_남기지_않는다(self):
        state = filled_state(nonce=2)

        reset_form_state(state)

        self.assertNotIn(field_key("title", 2), state)

    def test_초기화하지_않으면_입력값이_남는다(self):
        """등록 뒤에도 값이 남아야 비슷한 공고를 이어서 넣을 수 있습니다."""
        state = filled_state()

        self.assertEqual(state[field_key("title", 0)], "title 값")
        self.assertIn(field_key("image", 0), state)


if __name__ == "__main__":
    unittest.main()
