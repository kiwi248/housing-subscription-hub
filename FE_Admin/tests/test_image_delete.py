# test_image_delete.py
"""이미지 삭제 확인 흐름 테스트.

Streamlit이나 서버에 연결하지 않는 순수 함수만 확인합니다.
FE_Admin 폴더에서 아래 명령으로 실행합니다.

    python -m unittest discover -s tests
"""

import unittest

from core.image_delete import (
    CONFIRMING,
    IDLE,
    build_delete_request,
    next_step,
    should_show_delete_button,
    summarize_result,
)


class ShouldShowDeleteButtonTest(unittest.TestCase):
    def test_이미지가_있으면_삭제_버튼을_보여_준다(self):
        self.assertTrue(should_show_delete_button("https://example.com/a.png"))

    def test_이미지가_없으면_삭제_버튼을_보여_주지_않는다(self):
        self.assertFalse(should_show_delete_button(None))
        self.assertFalse(should_show_delete_button(""))

    def test_공백뿐이면_이미지가_없는_것으로_본다(self):
        self.assertFalse(should_show_delete_button("   "))

    def test_문자열이_아니면_보여_주지_않는다(self):
        self.assertFalse(should_show_delete_button(123))
        self.assertFalse(should_show_delete_button({"url": "x"}))


class NextStepTest(unittest.TestCase):
    def test_삭제_버튼을_누르면_경고창_단계로만_간다(self):
        """이 버튼만으로는 지워지지 않습니다."""
        self.assertEqual(
            next_step(IDLE, clicked_delete_button=True, clicked_cancel=False),
            CONFIRMING,
        )

    def test_취소하면_처음_상태로_돌아간다(self):
        self.assertEqual(
            next_step(CONFIRMING, clicked_delete_button=False, clicked_cancel=True),
            IDLE,
        )

    def test_아무것도_누르지_않으면_그대로다(self):
        self.assertEqual(
            next_step(CONFIRMING, clicked_delete_button=False, clicked_cancel=False),
            CONFIRMING,
        )

    def test_취소가_삭제_버튼보다_우선한다(self):
        self.assertEqual(
            next_step(CONFIRMING, clicked_delete_button=True, clicked_cancel=True),
            IDLE,
        )


class BuildDeleteRequestTest(unittest.TestCase):
    def test_공고_id만_담는다(self):
        self.assertEqual(build_delete_request(13), {"listing_id": 13})

    def test_수정_폼의_미저장_값은_담기지_않는다(self):
        """제목·보증금·월세를 화면에서 고쳐도 삭제 요청에는 들어가지 않습니다."""
        request = build_delete_request(13)
        for field in ("title", "deposit", "monthly_rent", "description", "image_url"):
            self.assertNotIn(field, request)

    def test_담기는_값은_공고_id_하나뿐이다(self):
        self.assertEqual(set(build_delete_request(13)), {"listing_id"})


class SummarizeResultTest(unittest.TestCase):
    def test_성공이면_서버_문구를_보여_준다(self):
        succeeded, message = summarize_result(
            {"success": True, "message": "이미지를 삭제했습니다."}
        )
        self.assertTrue(succeeded)
        self.assertEqual(message, "이미지를 삭제했습니다.")

    def test_실패하면_원인_문구를_그대로_보여_준다(self):
        succeeded, message = summarize_result(
            {"success": False, "message": "이미지 삭제에 실패했습니다. (500)"}
        )
        self.assertFalse(succeeded)
        self.assertIn("500", message)

    def test_문구가_없으면_기본_문구를_쓴다(self):
        self.assertEqual(summarize_result({"success": False})[1], "이미지 삭제에 실패했습니다.")

    def test_응답이_dict가_아니면_실패로_본다(self):
        self.assertFalse(summarize_result(None)[0])
        self.assertFalse(summarize_result("이상한 값")[0])


class ConfirmFlowTest(unittest.TestCase):
    """버튼을 누르는 순서에 따라 API가 몇 번 불리는지 확인합니다."""

    def _run(self, clicks: list[str]) -> tuple[int, str]:
        """clicks 예: ["open", "cancel"] / ["open", "confirm"]"""
        api_calls = 0
        step = IDLE

        for click in clicks:
            step = next_step(
                step,
                clicked_delete_button=(click == "open"),
                clicked_cancel=(click == "cancel"),
            )
            # 실제 삭제는 경고창이 떠 있을 때 "confirm"을 눌러야만 일어납니다.
            if click == "confirm" and step == CONFIRMING:
                api_calls += 1

        return api_calls, step

    def test_삭제_버튼만_누르면_API를_부르지_않는다(self):
        calls, step = self._run(["open"])
        self.assertEqual(calls, 0)
        self.assertEqual(step, CONFIRMING)

    def test_경고창에서_취소하면_API를_부르지_않는다(self):
        calls, step = self._run(["open", "cancel"])
        self.assertEqual(calls, 0)
        self.assertEqual(step, IDLE)

    def test_경고창에서_삭제하면_한_번만_부른다(self):
        calls, _ = self._run(["open", "confirm"])
        self.assertEqual(calls, 1)

    def test_취소한_뒤_다시_열어_삭제해도_한_번만_부른다(self):
        calls, _ = self._run(["open", "cancel", "open", "confirm"])
        self.assertEqual(calls, 1)

    def test_경고창을_열지_않고는_삭제할_수_없다(self):
        calls, _ = self._run(["confirm"])
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
