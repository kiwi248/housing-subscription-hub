"""독립 AI 안내원 라우터 테스트입니다."""

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_dependency import AuthenticatedUser, get_current_user
from app.exceptions.handlers import register_exception_handlers
from app.routers.guide_router import guide_router


def fake_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id="guide-user", email="guide@example.com")


app = FastAPI()
register_exception_handlers(app)
app.include_router(guide_router)
app.dependency_overrides[get_current_user] = fake_current_user
client = TestClient(app)


class GuideRouterTest(unittest.TestCase):
    def test_health는_저장소를_사용하지_않는다고_알린다(self):
        response = client.get("/ai-guide/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["storage"], "session-only")

    def test_자연어_질문을_단계별_안내로_응답한다(self):
        with patch.dict(os.environ, {"CHAT_GEMINI_MODE": "mock"}, clear=False):
            response = client.post(
                "/ai-guide/message",
                json={"question": "청약 공고를 조건으로 검색하려면?", "messages": []},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["category"], "LISTING_SEARCH")
        self.assertEqual(data["response_type"], "guide")
        self.assertGreater(len(data["steps"]), 0)

    def test_빈_질문은_거절한다(self):
        response = client.post(
            "/ai-guide/message",
            json={"question": "  ", "messages": []},
        )
        self.assertEqual(response.status_code, 422)

    def test_인증_없는_질문은_거절한다(self):
        unauthenticated_app = FastAPI()
        register_exception_handlers(unauthenticated_app)
        unauthenticated_app.include_router(guide_router)

        response = TestClient(unauthenticated_app).post(
            "/ai-guide/message",
            json={"question": "내 정보는 어디서 봐?", "messages": []},
        )
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
