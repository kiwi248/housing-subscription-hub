"""Gemini 멀티턴 답변과 상담 요약 미리보기를 처리합니다.

CHAT_SUMMARY_STORAGE의 기본값은 preview입니다. 이 모드에서는 Supabase에 쓰지 않고
현재 테스트 백엔드 프로세스의 메모리에만 요약을 보관합니다.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.gemini_config import (
    get_gemini_client,
    get_gemini_mode,
    get_gemini_model,
    get_history_limit,
)
from app.core.supabase_config import get_supabase
from app.schemas.chat_schema import ChatAnswer, ChatMessage, ChatProfile, ChatSummaryItem


SYSTEM_PROMPT = """당신은 공공임대 및 분양 청약 서비스의 상담 도우미입니다.
사용자의 질문에 쉽고 간결한 한국어로 답하세요.
확실하지 않은 사실을 만들어내지 마세요.
법률, 금융, 청약 자격을 확정적으로 판단하지 마세요.
중요한 신청 정보는 공식 공고와 담당 기관에서 확인하도록 안내하세요.
개인정보를 요구하지 마세요."""

SUMMARY_PROMPT = """아래 상담 전체를 바탕으로 한국어 제목과 요약을 만드세요.
개인정보를 제목에 포함하지 말고 JSON 이외의 문장은 출력하지 마세요.
반드시 다음 JSON 형식을 유지하세요.

{"title": "상담 내용을 알아볼 수 있는 10~30자 제목", "summary": "아래 형식의 요약"}

summary 값은 다음 형식을 유지하세요.

상담 주제:
- 핵심 주제

주요 질문:
- 사용자의 핵심 질문

안내 내용:
- 상담에서 안내한 핵심 내용

추가 확인 사항:
- 사용자가 공식 자료에서 확인해야 할 내용

한 줄 요약:
- 상담 전체를 한 문장으로 요약"""

SUMMARY_REQUEST = "위 상담 내용을 시스템 지시사항의 형식에 맞게 요약해 주세요."

_preview_lock = threading.Lock()
_preview_summaries: dict[str, list[ChatSummaryItem]] = {}


def to_gemini_contents(messages: list[ChatMessage], question: str | None = None) -> list[dict]:
    """공통 user/assistant 메시지를 Gemini의 user/model 형식으로 바꿉니다."""

    limit = get_history_limit()
    selected = messages[-limit:] if limit else []
    contents = [
        {
            "role": "user" if message.role == "user" else "model",
            "parts": [{"text": message.content}],
        }
        for message in selected
    ]
    if question is not None:
        contents.append({"role": "user", "parts": [{"text": question}]})
    return contents


def _mock_answer(question: str, history_count: int) -> str:
    return (
        f"'{question}'에 대한 테스트 상담 답변입니다. "
        f"이전 메시지 {history_count}개를 문맥으로 받았습니다."
    )


def _generate_text(contents: list[dict], system_prompt: str) -> str:
    client = get_gemini_client()
    try:
        response = client.models.generate_content(
            model=get_gemini_model(),
            contents=contents,
            config={"system_instruction": system_prompt},
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 상담 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from error

    answer = (getattr(response, "text", "") or "").strip()
    if not answer:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 상담 응답이 비어 있습니다. 다시 시도해 주세요.",
        )
    return answer


def create_chat_answer(messages: list[ChatMessage], question: str) -> ChatAnswer:
    history_limit = get_history_limit()
    selected_history = messages[-history_limit:] if history_limit else []
    model = "mock-chat" if get_gemini_mode() == "mock" else get_gemini_model()

    if get_gemini_mode() == "mock":
        answer = _mock_answer(question, len(selected_history))
    else:
        answer = _generate_text(to_gemini_contents(selected_history, question), SYSTEM_PROMPT)

    return ChatAnswer(answer=answer, model=model, history_count=len(selected_history))


def to_gemini_summary_contents(messages: list[ChatMessage]) -> list[dict]:
    """Redis에 보관된 상담 전체와 요약 명령을 Gemini 형식으로 바꿉니다."""

    contents = [
        {
            "role": "user" if message.role == "user" else "model",
            "parts": [{"text": message.content}],
        }
        for message in messages
    ]
    contents.append({"role": "user", "parts": [{"text": SUMMARY_REQUEST}]})
    return contents


def make_summary_title(summary: str) -> str:
    """요약의 상담 주제 항목을 이용해 미리보기 제목을 만듭니다."""

    lines = [line.strip().lstrip("- ").strip() for line in summary.splitlines()]
    candidates = [line for line in lines if line and not line.endswith(":")]
    title = candidates[0] if candidates else "AI 상담 요약"
    return title if len(title) <= 40 else f"{title[:40]}..."


def _mock_summary(messages: list[ChatMessage]) -> str:
    questions = [item.content for item in messages if item.role == "user"]
    first_question = questions[0] if questions else "질문 없음"
    return (
        "상담 주제:\n"
        f"- {first_question}\n\n"
        "주요 질문:\n"
        + "\n".join(f"- {question}" for question in questions[:3])
        + "\n\n안내 내용:\n- 로컬 테스트 모드에서 생성한 요약입니다.\n\n"
        "추가 확인 사항:\n- 실제 상담 저장 전 내용을 확인해 주세요.\n\n"
        f"한 줄 요약:\n- 총 {len(messages)}개 메시지의 상담 요약 미리보기입니다."
    )


def _generate_summary(messages: list[ChatMessage]) -> tuple[str, str]:
    client = get_gemini_client()
    try:
        response = client.models.generate_content(
            model=get_gemini_model(),
            contents=to_gemini_summary_contents(messages),
            config={
                "system_instruction": SUMMARY_PROMPT,
                "response_mime_type": "application/json",
            },
        )
        raw_result = (getattr(response, "text", "") or "").strip()
        result = json.loads(raw_result)
        title = str(result.get("title") or "").strip()
        summary = str(result.get("summary") or "").strip()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI가 상담 요약을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from error

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 상담 요약이 비어 있습니다. 다시 시도해 주세요.",
        )
    return (title[:80] or make_summary_title(summary), summary)


def create_chat_summary(user_id: str, messages: list[ChatMessage]) -> ChatSummaryItem:
    if len(messages) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="저장할 상담 내용이 없습니다.",
        )

    model = "mock-chat" if get_gemini_mode() == "mock" else get_gemini_model()

    if get_gemini_mode() == "mock":
        summary = _mock_summary(messages)
        title = make_summary_title(summary)
    else:
        title, summary = _generate_summary(messages)

    item = ChatSummaryItem(
        id=uuid4(),
        user_id=user_id,
        title=title,
        summary=summary,
        message_count=len(messages),
        model=model,
        created_at=datetime.now(timezone.utc),
    )
    return persist_chat_summary(item)


def get_summary_storage_mode() -> str:
    mode = os.getenv("CHAT_SUMMARY_STORAGE", "preview").strip().lower()
    if mode not in {"preview", "supabase"}:
        raise RuntimeError("CHAT_SUMMARY_STORAGE는 preview 또는 supabase여야 합니다.")
    return mode


def persist_chat_summary(item: ChatSummaryItem) -> ChatSummaryItem:
    if get_summary_storage_mode() == "preview":
        with _preview_lock:
            _preview_summaries.setdefault(item.user_id, []).insert(0, item)
        return item

    try:
        result = (
            get_supabase()
            .table("chat_summaries")
            .insert(item.model_dump(mode="json"))
            .execute()
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상담 요약을 저장하지 못했습니다.",
        ) from error
    return ChatSummaryItem.model_validate(result.data[0])


def list_chat_summaries(user_id: str) -> list[ChatSummaryItem]:
    if get_summary_storage_mode() == "preview":
        with _preview_lock:
            return list(_preview_summaries.get(user_id, []))

    try:
        result = (
            get_supabase()
            .table("chat_summaries")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="저장된 상담을 불러오지 못했습니다.",
        ) from error
    return [ChatSummaryItem.model_validate(row) for row in result.data]


def delete_chat_summary(user_id: str, summary_id: str) -> None:
    """현재 사용자가 소유한 상담 요약 한 건만 삭제합니다."""

    if get_summary_storage_mode() == "preview":
        with _preview_lock:
            items = _preview_summaries.get(user_id, [])
            remaining = [item for item in items if str(item.id) != summary_id]
            if len(remaining) == len(items):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="삭제할 상담 요약을 찾을 수 없습니다.",
                )
            _preview_summaries[user_id] = remaining
        return

    try:
        result = (
            get_supabase()
            .table("chat_summaries")
            .delete()
            .eq("id", summary_id)
            .eq("user_id", user_id)
            .execute()
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상담 요약을 삭제하지 못했습니다.",
        ) from error

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="삭제할 상담 요약을 찾을 수 없습니다.",
        )


def get_chat_profile(user_id: str, email: str) -> ChatProfile:
    try:
        result = get_supabase().table("profiles").select("nickname").eq("id", user_id).execute()
    except Exception as error:
        raise HTTPException(500, "프로필을 불러오지 못했습니다.") from error

    nickname = "회원"
    if result.data:
        nickname = (result.data[0].get("nickname") or "회원").strip()
    return ChatProfile(user_id=user_id, nickname=nickname, email=email)
