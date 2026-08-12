# test_session_restore.py
"""새로고침 후 로그인 세션 복원 판단 로직 테스트.

Streamlit이나 Supabase에 연결하지 않는 순수 함수만 확인합니다.
실제 계정 정보나 실제 토큰은 쓰지 않고, 형태만 흉내 낸 가짜 값을 씁니다.

FE_User 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.session_restore import (
    ACCESS_TOKEN_NAME,
    REFRESH_TOKEN_NAME,
    read_tokens,
    restore_session,
    should_restore,
)


# 실제 토큰이 아니라 형태만 흉내 낸 값입니다.
FAKE_ACCESS_TOKEN = "fake-access-token"
FAKE_REFRESH_TOKEN = "fake-refresh-token"
FAKE_NEW_ACCESS_TOKEN = "fake-new-access-token"
FAKE_NEW_REFRESH_TOKEN = "fake-new-refresh-token"


class FakeUser:
    def __init__(self, user_id="user-1", email="tester@example.com"):
        self.id = user_id
        self.email = email


class FakeSession:
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token


class FakeAuthResponse:
    def __init__(self, session, user):
        self.session = session
        self.user = user


class FakeSetSession:
    """supabase.auth.set_session을 흉내 냅니다. 호출 횟수도 셉니다."""

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.call_count = 0
        self.calls = []

    def __call__(self, access_token, refresh_token):
        self.call_count += 1
        self.calls.append((access_token, refresh_token))
        if self.error is not None:
            raise self.error
        return self.response


def make_success_set_session():
    """세션을 갱신해서 돌려주는 정상 응답을 만듭니다."""
    return FakeSetSession(
        FakeAuthResponse(
            FakeSession(FAKE_NEW_ACCESS_TOKEN, FAKE_NEW_REFRESH_TOKEN),
            FakeUser(),
        )
    )


class ReadTokensTest(unittest.TestCase):
    def test_저장된_토큰을_읽는다(self):
        stored = {
            ACCESS_TOKEN_NAME: FAKE_ACCESS_TOKEN,
            REFRESH_TOKEN_NAME: FAKE_REFRESH_TOKEN,
        }
        self.assertEqual(
            read_tokens(stored), (FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN)
        )

    def test_저장소가_비어_있으면_빈_문자열이다(self):
        self.assertEqual(read_tokens({}), ("", ""))

    def test_값이_None이면_빈_문자열이다(self):
        self.assertEqual(read_tokens(None), ("", ""))

    def test_dict가_아니면_빈_문자열이다(self):
        self.assertEqual(read_tokens("이상한 값"), ("", ""))

    def test_공백만_있으면_빈_문자열로_본다(self):
        stored = {ACCESS_TOKEN_NAME: "   ", REFRESH_TOKEN_NAME: "\t"}
        self.assertEqual(read_tokens(stored), ("", ""))

    def test_한쪽만_있으면_나머지는_빈_문자열이다(self):
        stored = {ACCESS_TOKEN_NAME: FAKE_ACCESS_TOKEN}
        self.assertEqual(read_tokens(stored), (FAKE_ACCESS_TOKEN, ""))

    def test_토큰_외의_값은_읽지_않는다(self):
        stored = {
            ACCESS_TOKEN_NAME: FAKE_ACCESS_TOKEN,
            REFRESH_TOKEN_NAME: FAKE_REFRESH_TOKEN,
            "password": "지워야 할 값",
            "email": "tester@example.com",
        }
        self.assertEqual(
            read_tokens(stored), (FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN)
        )


class ShouldRestoreTest(unittest.TestCase):
    def test_토큰이_있고_로그인_전이면_되살린다(self):
        self.assertTrue(
            should_restore(is_logged_in=False, already_tried=False, has_tokens=True)
        )

    def test_이미_로그인했으면_되살리지_않는다(self):
        self.assertFalse(
            should_restore(is_logged_in=True, already_tried=False, has_tokens=True)
        )

    def test_이번_세션에서_이미_시도했으면_다시_하지_않는다(self):
        """이 조건이 없으면 화면이 다시 그려질 때마다 Supabase에 요청합니다."""
        self.assertFalse(
            should_restore(is_logged_in=False, already_tried=True, has_tokens=True)
        )

    def test_토큰이_없으면_되살리지_않는다(self):
        self.assertFalse(
            should_restore(is_logged_in=False, already_tried=False, has_tokens=False)
        )


class RestoreSessionTest(unittest.TestCase):
    def test_정상_토큰이면_로그인_정보를_돌려준다(self):
        set_session = make_success_set_session()

        result = restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(result["status"], "restored")
        self.assertEqual(result["user_id"], "user-1")
        self.assertEqual(result["email"], "tester@example.com")
        self.assertEqual(set_session.call_count, 1)
        self.assertEqual(
            set_session.calls[0], (FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN)
        )

    def test_갱신된_토큰을_돌려준다(self):
        """세션이 만료돼 SDK가 갱신하면 새 토큰을 다시 저장해야 합니다."""
        set_session = make_success_set_session()

        result = restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(result["access_token"], FAKE_NEW_ACCESS_TOKEN)
        self.assertEqual(result["refresh_token"], FAKE_NEW_REFRESH_TOKEN)

    def test_토큰이_없으면_Supabase에_묻지_않는다(self):
        set_session = make_success_set_session()

        result = restore_session("", "", set_session)

        self.assertEqual(result["status"], "empty")
        self.assertEqual(set_session.call_count, 0)

    def test_한쪽_토큰만_있으면_되살리지_않는다(self):
        set_session = make_success_set_session()

        result = restore_session(FAKE_ACCESS_TOKEN, "", set_session)

        self.assertEqual(result["status"], "empty")
        self.assertEqual(set_session.call_count, 0)

    def test_만료되어_갱신할_수_없으면_로그인_처리하지_않는다(self):
        set_session = FakeSetSession(error=RuntimeError("token is expired"))

        result = restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(result["status"], "invalid")
        self.assertNotIn("user_id", result)

    def test_잘못된_토큰이면_로그인_처리하지_않는다(self):
        set_session = FakeSetSession(error=ValueError("invalid JWT"))

        result = restore_session("엉뚱한 값", "엉뚱한 값", set_session)

        self.assertEqual(result["status"], "invalid")

    def test_세션이_없는_응답이면_로그인_처리하지_않는다(self):
        set_session = FakeSetSession(FakeAuthResponse(None, FakeUser()))

        result = restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(result["status"], "invalid")

    def test_사용자가_없는_응답이면_로그인_처리하지_않는다(self):
        """이메일이나 ID 없이 세션만 있으면 로그인으로 보지 않습니다."""
        set_session = FakeSetSession(
            FakeAuthResponse(FakeSession(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN), None)
        )

        result = restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(result["status"], "invalid")

    def test_되살린_결과에_비밀번호가_없다(self):
        set_session = make_success_set_session()

        result = restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(
            set(result),
            {"status", "user_id", "email", "access_token", "refresh_token"},
        )


class NoRepeatedRequestTest(unittest.TestCase):
    """복원 과정에서 같은 요청이 되풀이되지 않는지 확인합니다."""

    def _run_reruns(self, times: int, has_tokens: bool = True) -> int:
        """화면이 여러 번 다시 그려지는 상황을 흉내 냅니다."""
        set_session = make_success_set_session()
        logged_in = False
        tried = False

        for _ in range(times):
            if should_restore(
                is_logged_in=logged_in, already_tried=tried, has_tokens=has_tokens
            ):
                tried = True
                result = restore_session(
                    FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session
                )
                logged_in = result["status"] == "restored"

        return set_session.call_count

    def test_여러_번_다시_그려도_한_번만_요청한다(self):
        self.assertEqual(self._run_reruns(times=10), 1)

    def test_토큰이_없으면_아예_요청하지_않는다(self):
        self.assertEqual(self._run_reruns(times=10, has_tokens=False), 0)

    def test_실패해도_다시_요청하지_않는다(self):
        """복원에 실패해도 계속 재시도하면 화면이 멈추지 않고 돌 수 있습니다."""
        set_session = FakeSetSession(error=RuntimeError("invalid"))
        tried = False

        for _ in range(10):
            if should_restore(
                is_logged_in=False, already_tried=tried, has_tokens=True
            ):
                tried = True
                restore_session(FAKE_ACCESS_TOKEN, FAKE_REFRESH_TOKEN, set_session)

        self.assertEqual(set_session.call_count, 1)


if __name__ == "__main__":
    unittest.main()
