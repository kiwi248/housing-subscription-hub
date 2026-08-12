"""AI 안내원이 기존 상담과 저장소를 건드리지 않는지 검증합니다."""

import os
import unittest
from unittest.mock import patch

from app.schemas.guide_schema import GuideCategory, GuideMessage
from app.services import guide_service


class GuideServiceTest(unittest.TestCase):
    def setUp(self):
        self.mock_mode = patch.dict(os.environ, {"CHAT_GEMINI_MODE": "mock"}, clear=False)
        self.mock_mode.start()

    def tearDown(self):
        self.mock_mode.stop()

    def test_내_정보_조회는_단계별_안내를_반환한다(self):
        answer = guide_service.create_guide_answer([], "회원가입 때 입력한 정보를 어디서 봐?")

        self.assertEqual(answer.category, GuideCategory.PROFILE_VIEW)
        self.assertEqual(answer.response_type, "guide")
        self.assertEqual(answer.title, "내 정보 조회 방법")
        self.assertGreaterEqual(len(answer.steps), 4)
        self.assertIn("My Page", " ".join(answer.steps))

    def test_즐겨찾기_삭제를_별도_카테고리로_분류한다(self):
        answer = guide_service.create_guide_answer([], "즐겨찾기를 지우려면 어떻게 해?")

        self.assertEqual(answer.category, GuideCategory.FAVORITE_DELETE)
        self.assertIn("즐겨찾기 삭제", " ".join(answer.steps))

    def test_공고_추천은_거절한다(self):
        answer = guide_service.create_guide_answer([], "내 조건에 맞는 동작구 공공임대를 추천해줘")

        self.assertEqual(answer.category, GuideCategory.OUT_OF_SCOPE)
        self.assertEqual(answer.response_type, "refusal")
        self.assertIn("공고 추천", answer.answer)

    def test_첫_화면의_공고_검색_예시를_분류한다(self):
        answer = guide_service.create_guide_answer([], "청약 공고는 어떻게 검색하나요?")
        self.assertEqual(answer.category, GuideCategory.LISTING_SEARCH)

    def test_실시간_공고_검색은_거절한다(self):
        answer = guide_service.create_guide_answer([], "실시간 공고를 검색해줘")
        self.assertEqual(answer.category, GuideCategory.OUT_OF_SCOPE)

    def test_용어는_짧은_답변_유형이다(self):
        answer = guide_service.create_guide_answer([], "보증금이 무엇인가요?")

        self.assertEqual(answer.category, GuideCategory.TERM_EXPLANATION)
        self.assertEqual(answer.response_type, "answer")
        self.assertTrue(answer.answer)

    def test_이전_대화_수만_응답에_표시한다(self):
        messages = [
            GuideMessage(role="user", content="즐겨찾기가 뭐야?"),
            GuideMessage(role="assistant", content="즐겨찾기 안내입니다."),
        ]

        answer = guide_service.create_guide_answer(messages, "어디서 확인해?")

        self.assertEqual(answer.history_count, 2)

    def test_잘못된_Gemini_JSON은_안전한_재질문으로_바꾼다(self):
        classification = guide_service._parse_classification("not-json")
        self.assertEqual(classification.category, GuideCategory.OUT_OF_SCOPE)
        self.assertEqual(classification.confidence, 0)

    def test_실제_모드에서는_Gemini를_한_번만_호출한다(self):
        fake_response = type(
            "FakeResponse",
            (),
            {"text": '{"category":"PROFILE_VIEW","confidence":0.98,"short_answer":null}'},
        )()
        fake_client = type(
            "FakeClient",
            (),
            {
                "models": type(
                    "FakeModels",
                    (),
                    {"generate_content": unittest.mock.Mock(return_value=fake_response)},
                )()
            },
        )()

        with (
            patch.dict(os.environ, {"CHAT_GEMINI_MODE": "gemini"}, clear=False),
            patch.object(guide_service, "get_gemini_client", return_value=fake_client),
        ):
            answer = guide_service.create_guide_answer([], "내 정보는 어디서 확인해?")

        self.assertEqual(answer.category, GuideCategory.PROFILE_VIEW)
        fake_client.models.generate_content.assert_called_once()

    def test_Gemini가_내_정보를_거절해도_기능_안내로_보정한다(self):
        fake_response = type(
            "FakeResponse",
            (),
            {"text": '{"category":"OUT_OF_SCOPE","confidence":0.99,"short_answer":null}'},
        )()
        fake_client = type(
            "FakeClient",
            (),
            {
                "models": type(
                    "FakeModels",
                    (),
                    {"generate_content": unittest.mock.Mock(return_value=fake_response)},
                )()
            },
        )()

        with (
            patch.dict(os.environ, {"CHAT_GEMINI_MODE": "gemini"}, clear=False),
            patch.object(guide_service, "get_gemini_client", return_value=fake_client),
        ):
            answer = guide_service.create_guide_answer([], "내 정보는 어디서 확인할 수 있나요?")

        self.assertEqual(answer.category, GuideCategory.PROFILE_VIEW)
        fake_client.models.generate_content.assert_called_once()

    def test_아이디_변경은_불가능하다고_안내한다(self):
        answer = guide_service.create_guide_answer([], "아이디를 바꾸고 싶어")
        self.assertEqual(answer.category, GuideCategory.ACCOUNT_ID_CHANGE)
        self.assertIn("변경할 수 없습니다", " ".join(answer.steps))

    def test_비밀번호_변경은_My_Page_단계를_안내한다(self):
        answer = guide_service.create_guide_answer([], "비밀번호는 어떻게 변경해?")
        self.assertEqual(answer.category, GuideCategory.PASSWORD_CHANGE)
        self.assertIn("My Page", " ".join(answer.steps))
        self.assertIn("6자", " ".join(answer.steps))

    def test_성함과_휴대번호는_프로필_수정으로_분류한다(self):
        for question in ("성함을 수정하고 싶어", "휴대번호를 바꾸고 싶어"):
            with self.subTest(question=question):
                answer = guide_service.create_guide_answer([], question)
                self.assertEqual(answer.category, GuideCategory.PROFILE_EDIT)

    def test_AI_채팅_상담_사용법을_안내한다(self):
        for question in (
            "궁금한 거 물어보고 싶으면 어떻게 해?",
            "대화 저장은 어떻게 해?",
            "저장된 상담을 삭제하고 싶어",
        ):
            with self.subTest(question=question):
                answer = guide_service.create_guide_answer([], question)
                self.assertEqual(answer.category, GuideCategory.AI_CHAT_USAGE)
                self.assertIn("AI 채팅 상담", answer.title)

    def test_AI_안내원_질문_범위를_안내한다(self):
        answer = guide_service.create_guide_answer([], "AI 안내원은 어떤 질문을 할 수 있어?")
        self.assertEqual(answer.category, GuideCategory.AI_GUIDE_SCOPE)
        self.assertIn("공고 추천", " ".join(answer.steps))

    def test_공고_페이지_이동과_로그아웃을_안내한다(self):
        page_answer = guide_service.create_guide_answer([], "청약정보 다음 페이지로 가고 싶어")
        logout_answer = guide_service.create_guide_answer([], "로그아웃은 어떻게 해?")
        self.assertEqual(page_answer.category, GuideCategory.LISTING_PAGINATION)
        self.assertEqual(logout_answer.category, GuideCategory.LOGOUT)

    def test_홈_화면으로_이동하는_방법을_안내한다(self):
        answer = guide_service.create_guide_answer([], "홈 화면으로 가고 싶어")
        self.assertEqual(answer.category, GuideCategory.HOME_GUIDE)


if __name__ == "__main__":
    unittest.main()
