"""실제 Gemini와 Supabase를 호출하지 않는 AI 상담 서비스 테스트입니다."""

import os
import unittest
from unittest.mock import patch

from app.schemas.chat_schema import ChatMessage
from app.services import chat_service


class ChatServiceTest(unittest.TestCase):
    def setUp(self):
        chat_service._preview_summaries.clear()

    def test_이전_AI_답변은_Gemini_model_역할로_변환한다(self):
        messages = [
            ChatMessage(role="user", content="첫 질문"),
            ChatMessage(role="assistant", content="첫 답변"),
        ]

        with patch.dict(os.environ, {"CHAT_HISTORY_LIMIT": "10"}, clear=False):
            contents = chat_service.to_gemini_contents(messages, "후속 질문")

        self.assertEqual([item["role"] for item in contents], ["user", "model", "user"])
        self.assertEqual(contents[-1]["parts"][0]["text"], "후속 질문")

    def test_최근_메시지만_Gemini_문맥으로_사용한다(self):
        messages = [ChatMessage(role="user", content=f"질문 {index}") for index in range(5)]

        with patch.dict(os.environ, {"CHAT_HISTORY_LIMIT": "2"}, clear=False):
            contents = chat_service.to_gemini_contents(messages, "현재 질문")

        self.assertEqual(len(contents), 3)
        self.assertEqual(contents[0]["parts"][0]["text"], "질문 3")
        self.assertEqual(contents[1]["parts"][0]["text"], "질문 4")

    def test_mock_답변은_이전_메시지_수를_반환한다(self):
        messages = [
            ChatMessage(role="user", content="이름은 오현이야"),
            ChatMessage(role="assistant", content="알겠습니다"),
        ]

        with patch.dict(
            os.environ,
            {"CHAT_GEMINI_MODE": "mock", "CHAT_HISTORY_LIMIT": "10"},
            clear=False,
        ):
            answer = chat_service.create_chat_answer(messages, "내 이름은?")

        self.assertEqual(answer.model, "mock-chat")
        self.assertEqual(answer.history_count, 2)
        self.assertIn("이전 메시지 2개", answer.answer)

    def test_preview_요약은_사용자별로_분리한다(self):
        messages = [
            ChatMessage(role="user", content="청약이 무엇인가요?"),
            ChatMessage(role="assistant", content="청약 기본 설명입니다."),
        ]

        with patch.dict(
            os.environ,
            {"CHAT_GEMINI_MODE": "mock", "CHAT_SUMMARY_STORAGE": "preview"},
            clear=False,
        ):
            saved = chat_service.create_chat_summary("user-a", messages)
            user_a_items = chat_service.list_chat_summaries("user-a")
            user_b_items = chat_service.list_chat_summaries("user-b")

        self.assertEqual(saved.user_id, "user-a")
        self.assertEqual(len(user_a_items), 1)
        self.assertEqual(user_b_items, [])
        self.assertEqual(saved.message_count, 2)

    def test_real_summary_uses_all_messages_and_generated_title(self):
        messages = [
            ChatMessage(role="user", content="청약 조건을 알려주세요."),
            ChatMessage(role="assistant", content="조건을 안내해 드리겠습니다."),
        ]

        with (
            patch.dict(
                os.environ,
                {"CHAT_GEMINI_MODE": "gemini", "CHAT_SUMMARY_STORAGE": "preview"},
                clear=False,
            ),
            patch.object(
                chat_service,
                "_generate_summary",
                return_value=("청약 조건 상담", "상담 요약"),
            ) as generate,
        ):
            saved = chat_service.create_chat_summary("user-a", messages)

        self.assertEqual(generate.call_args.args[0], messages)
        self.assertEqual(saved.title, "청약 조건 상담")

    def test_제목은_요약의_상담_주제로_만든다(self):
        summary = "상담 주제:\n- 청약 신청 전 확인 사항\n\n주요 질문:\n- 질문"
        title = chat_service.make_summary_title(summary)

        self.assertEqual(title, "청약 신청 전 확인 사항")

    def test_요약용_내용은_대화_전체를_사용한다(self):
        messages = [ChatMessage(role="user", content=f"질문 {index}") for index in range(12)]
        contents = chat_service.to_gemini_summary_contents(messages)
        self.assertEqual(len(contents), 13)
        self.assertEqual(contents[0]["parts"][0]["text"], "질문 0")
        self.assertEqual(contents[-1]["parts"][0]["text"], chat_service.SUMMARY_REQUEST)

    def test_preview_요약은_소유한_사용자만_삭제한다(self):
        messages = [
            ChatMessage(role="user", content="질문"),
            ChatMessage(role="assistant", content="답변"),
        ]
        with patch.dict(
            os.environ,
            {"CHAT_GEMINI_MODE": "mock", "CHAT_SUMMARY_STORAGE": "preview"},
            clear=False,
        ):
            saved = chat_service.create_chat_summary("user-a", messages)
            with self.assertRaises(Exception):
                chat_service.delete_chat_summary("user-b", str(saved.id))
            self.assertEqual(len(chat_service.list_chat_summaries("user-a")), 1)
            chat_service.delete_chat_summary("user-a", str(saved.id))
            self.assertEqual(chat_service.list_chat_summaries("user-a"), [])


if __name__ == "__main__":
    unittest.main()
