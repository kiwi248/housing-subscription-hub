"""기존 app/main.py 없이 독립 FastAPI 앱으로 확인하는 챗봇 라우터 테스트입니다."""

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_dependency import AuthenticatedUser, get_current_user
from app.exceptions.handlers import register_exception_handlers
from app.routers import chat_router as router_module
from app.routers.chat_router import chat_router
from app.schemas.chat_schema import ChatMessage
from app.services import chat_service


def fake_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id="test-user", email="test@example.com")


test_app = FastAPI()
register_exception_handlers(test_app)
test_app.include_router(chat_router)
test_app.dependency_overrides[get_current_user] = fake_current_user
client = TestClient(test_app)


class ChatRouterTest(unittest.TestCase):
    def setUp(self):
        chat_service._preview_summaries.clear()

    def test_mock_채팅은_Redis_기록을_문맥으로_사용하고_답변을_추가한다(self):
        history = [
            ChatMessage(role="user", content="첫 질문"),
            ChatMessage(role="assistant", content="첫 답변"),
        ]
        with (
            patch.dict(os.environ, {"CHAT_GEMINI_MODE": "mock"}, clear=False),
            patch.object(router_module, "get_chat_history", return_value=history),
            patch.object(router_module, "append_chat_exchange") as append,
        ):
            response = client.post("/chat/message", json={"question": "두 번째 질문"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["history_count"], 2)
        append.assert_called_once()

    def test_진행중인_대화_조회와_삭제(self):
        history = [ChatMessage(role="user", content="질문")]
        with (
            patch.object(router_module, "get_chat_history", return_value=history),
            patch.object(router_module, "delete_chat_history") as delete,
        ):
            get_response = client.get("/chat/history")
            delete_response = client.delete("/chat/history")

        self.assertEqual(get_response.json()["data"][0]["content"], "질문")
        self.assertEqual(delete_response.status_code, 200)
        delete.assert_called_once_with("test-user")

    def test_요약_저장은_Redis_전체기록을_사용한_뒤_삭제한다(self):
        history = [
            ChatMessage(role="user", content="청약이 무엇인가요?"),
            ChatMessage(role="assistant", content="청약 기본 설명입니다."),
        ]
        with (
            patch.dict(
                os.environ,
                {"CHAT_GEMINI_MODE": "mock", "CHAT_SUMMARY_STORAGE": "preview"},
                clear=False,
            ),
            patch.object(router_module, "get_chat_history", return_value=history),
            patch.object(router_module, "delete_chat_history") as delete,
        ):
            save_response = client.post("/chat/save", json={})
            list_response = client.get("/chat/summaries")

        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(len(list_response.json()["data"]), 1)
        self.assertEqual(list_response.json()["data"][0]["message_count"], 2)
        delete.assert_called_once_with("test-user")

    def test_빈_질문은_검증_오류(self):
        response = client.post("/chat/message", json={"question": "   "})
        self.assertEqual(response.status_code, 422)

    def test_선택한_상담_요약을_삭제한다(self):
        summary_id = "11111111-1111-1111-1111-111111111111"
        with patch.object(router_module, "delete_chat_summary") as delete:
            response = client.delete(f"/chat/summaries/{summary_id}")

        self.assertEqual(response.status_code, 200)
        delete.assert_called_once_with("test-user", summary_id)


class ChatRouterAuthenticationTest(unittest.TestCase):
    def test_인증_없는_요청은_거절한다(self):
        app = FastAPI()
        register_exception_handlers(app)
        app.include_router(chat_router)
        response = TestClient(app).post("/chat/message", json={"question": "질문"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
