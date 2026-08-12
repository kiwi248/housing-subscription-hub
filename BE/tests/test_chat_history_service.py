"""외부 Upstash 호출 없이 Redis 상담 기록 동작을 검증합니다."""

import json
import os
import unittest
from unittest.mock import patch

from app.schemas.chat_schema import ChatMessage
from app.services.chat_history_service import (
    append_chat_exchange,
    delete_chat_history,
    get_chat_history,
    save_chat_history,
)


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        self.expirations[key] = ex

    def delete(self, key):
        self.values.pop(key, None)


class ChatHistoryServiceTest(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()

    def test_사용자별로_기록을_분리하고_1시간_TTL을_설정한다(self):
        with patch.dict(os.environ, {"CHAT_HISTORY_TTL_SECONDS": "3600"}, clear=False):
            save_chat_history(
                "user-a",
                [ChatMessage(role="user", content="질문 A")],
                self.redis,
            )
        save_chat_history(
            "user-b",
            [ChatMessage(role="user", content="질문 B")],
            self.redis,
        )

        self.assertEqual(get_chat_history("user-a", self.redis)[0].content, "질문 A")
        self.assertEqual(get_chat_history("user-b", self.redis)[0].content, "질문 B")
        self.assertEqual(self.redis.expirations["ai-chat:active:user-a"], 3600)

    def test_최대_메시지_수만_보관한다(self):
        messages = [ChatMessage(role="user", content=f"질문 {index}") for index in range(5)]
        with patch.dict(os.environ, {"CHAT_HISTORY_MAX_MESSAGES": "3"}, clear=False):
            saved = save_chat_history("user-a", messages, self.redis)
        self.assertEqual([item.content for item in saved], ["질문 2", "질문 3", "질문 4"])

    def test_질문과_답변을_함께_추가하고_종료하면_삭제한다(self):
        append_chat_exchange("user-a", "질문", "답변", self.redis)
        self.assertEqual(len(get_chat_history("user-a", self.redis)), 2)
        delete_chat_history("user-a", self.redis)
        self.assertEqual(get_chat_history("user-a", self.redis), [])


if __name__ == "__main__":
    unittest.main()
