"""AI 상담 API 요청과 응답 모델입니다."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("메시지는 비어 있을 수 없습니다.")
        return cleaned


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    messages: list[ChatMessage] = Field(default_factory=list, max_length=100)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("질문을 입력해 주세요.")
        return cleaned


class ChatAnswer(BaseModel):
    answer: str
    model: str
    history_count: int


class ChatSaveRequest(BaseModel):
    # 이전 프런트엔드와의 호환을 위해 필드는 유지하지만 Redis 기록을 기준으로 저장합니다.
    messages: list[ChatMessage] = Field(default_factory=list, max_length=100)


class ChatSummaryItem(BaseModel):
    id: UUID
    user_id: str
    title: str
    summary: str
    message_count: int
    model: str
    created_at: datetime


class ChatProfile(BaseModel):
    user_id: str
    nickname: str
    email: str
