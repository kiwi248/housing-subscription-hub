"""AI 안내원 전용 요청·응답 모델입니다.

기존 AI 상담 모델과 세션을 공유하지 않습니다.
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GuideCategory(StrEnum):
    HOME_GUIDE = "HOME_GUIDE"
    PROFILE_VIEW = "PROFILE_VIEW"
    PROFILE_EDIT = "PROFILE_EDIT"
    ACCOUNT_ID_CHANGE = "ACCOUNT_ID_CHANGE"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    LISTING_VIEW = "LISTING_VIEW"
    LISTING_SEARCH = "LISTING_SEARCH"
    LISTING_DETAIL = "LISTING_DETAIL"
    LISTING_PAGINATION = "LISTING_PAGINATION"
    FAVORITE_ADD = "FAVORITE_ADD"
    FAVORITE_VIEW = "FAVORITE_VIEW"
    FAVORITE_DELETE = "FAVORITE_DELETE"
    AI_CHAT_USAGE = "AI_CHAT_USAGE"
    AI_GUIDE_SCOPE = "AI_GUIDE_SCOPE"
    LOGOUT = "LOGOUT"
    TERM_EXPLANATION = "TERM_EXPLANATION"
    SIMPLE_CALCULATION = "SIMPLE_CALCULATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class GuideMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("메시지는 비어 있을 수 없습니다.")
        return cleaned


class GuideRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    messages: list[GuideMessage] = Field(default_factory=list, max_length=30)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("질문을 입력해 주세요.")
        return cleaned


class GuideClassification(BaseModel):
    category: GuideCategory
    confidence: float = Field(ge=0, le=1)
    short_answer: str | None = Field(default=None, max_length=800)


class GuideAnswer(BaseModel):
    category: GuideCategory
    response_type: Literal["guide", "answer", "refusal", "clarification"]
    title: str
    steps: list[str] = Field(default_factory=list)
    answer: str | None = None
    notice: str | None = None
    model: str
    history_count: int


class GuideProfile(BaseModel):
    user_id: str
    nickname: str
    email: str
