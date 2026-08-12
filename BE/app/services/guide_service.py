"""프로젝트 기능만 안내하는 독립 AI 안내원 서비스입니다.

대화는 Redis나 Supabase에 저장하지 않습니다. Gemini는 질문 분류와 짧은
용어·계산 답변에만 사용하고, 프로젝트 사용법은 검증된 고정 단계로 제공합니다.
"""

from __future__ import annotations

import json

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.gemini_config import (
    get_gemini_client,
    get_gemini_mode,
    get_gemini_model,
    get_history_limit,
)
from app.core.supabase_config import get_supabase
from app.schemas.guide_schema import (
    GuideAnswer,
    GuideCategory,
    GuideClassification,
    GuideMessage,
    GuideProfile,
)


CLASSIFIER_PROMPT = """당신은 공공임대 청약 통합 안내 서비스의 질문 분류기입니다.
반드시 JSON 객체 하나만 반환하세요.

허용 category:
HOME_GUIDE, PROFILE_VIEW, PROFILE_EDIT, ACCOUNT_ID_CHANGE, PASSWORD_CHANGE,
LISTING_VIEW, LISTING_SEARCH, LISTING_DETAIL, LISTING_PAGINATION,
FAVORITE_ADD, FAVORITE_VIEW, FAVORITE_DELETE, AI_CHAT_USAGE, AI_GUIDE_SCOPE,
LOGOUT, TERM_EXPLANATION, SIMPLE_CALCULATION, OUT_OF_SCOPE

프로젝트 기능 분류 기준:
- "내 정보 어디서 확인", "회원가입 때 입력한 정보 보기" -> PROFILE_VIEW
- "성함/닉네임/휴대번호/전화번호/관심분야 수정" -> PROFILE_EDIT
- "아이디/이메일 변경" -> ACCOUNT_ID_CHANGE
- "비밀번호 변경" -> PASSWORD_CHANGE
- "청약 공고 목록 보기", "청약정보 조회" -> LISTING_VIEW
- "지역/보증금/월세로 공고 검색", "조건검색 방법" -> LISTING_SEARCH
- "공고 상세/원문 확인" -> LISTING_DETAIL
- "공고 다음 페이지/페이지 번호 이동" -> LISTING_PAGINATION
- "관심 공고를 즐겨찾기에 추가" -> FAVORITE_ADD
- "저장한 즐겨찾기 목록 확인" -> FAVORITE_VIEW
- "즐겨찾기 삭제/취소" -> FAVORITE_DELETE
- "AI에게 질문/채팅 상담/상담 저장·종료·확인·삭제" -> AI_CHAT_USAGE
- "AI 안내원이 할 수 있는 것/질문 가능 범위" -> AI_GUIDE_SCOPE
- "로그아웃 방법" -> LOGOUT
- "홈 화면/처음 화면으로 이동" -> HOME_GUIDE

규칙:
- 프로젝트 화면 사용법 질문은 알맞은 기능 category로 분류합니다.
- 청약·임대의 일반적인 용어 질문은 TERM_EXPLANATION입니다.
- 단순 사칙연산·백분율 금액 계산은 SIMPLE_CALCULATION입니다.
- 특정 공고 추천, 실시간 정보, 청약 자격·당첨 가능성 판단, 의료·법률·투자,
  개인정보 요청, 프로젝트와 무관한 질문은 OUT_OF_SCOPE입니다.
- 기능 category에서는 short_answer를 null로 둡니다.
- TERM_EXPLANATION과 SIMPLE_CALCULATION만 short_answer를 한국어 3문장 이내로 작성합니다.
- 확인되지 않은 사실이나 최신 정책을 만들지 않습니다.

형식:
{"category":"PROFILE_VIEW","confidence":0.95,"short_answer":null}

예시:
질문: 내 정보는 어디서 확인할 수 있나요?
응답: {"category":"PROFILE_VIEW","confidence":0.99,"short_answer":null}

질문: 동작구에서 내 조건에 맞는 공공임대를 추천해줘.
응답: {"category":"OUT_OF_SCOPE","confidence":0.99,"short_answer":null}
"""

REFUSAL = (
    "죄송합니다. AI 안내원은 사이트 이용 방법과 간단한 청약 용어 및 계산만 "
    "안내할 수 있습니다. 공고 추천, 신청 자격 판단 및 당첨 가능성은 안내하지 않습니다."
)

CLARIFICATION = (
    "질문을 정확히 이해하지 못했습니다. 내 정보, 청약정보 조회, 즐겨찾기 또는 "
    "간단한 청약 용어 중 어떤 내용을 알고 싶은지 다시 말씀해 주세요."
)

GUIDES: dict[GuideCategory, dict[str, object]] = {
    GuideCategory.HOME_GUIDE: {
        "title": "홈 화면 이용 방법",
        "steps": [
            "화면 왼쪽 메뉴에서 ‘홈’을 선택합니다.",
            "홈에서 서비스 안내를 확인합니다.",
            "청약 공고를 보려면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
        ],
    },
    GuideCategory.PROFILE_VIEW: {
        "title": "내 정보 조회 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴를 확인합니다.",
            "‘My Page’를 선택합니다.",
            "회원가입할 때 입력한 정보를 확인합니다.",
        ],
    },
    GuideCategory.PROFILE_EDIT: {
        "title": "내 정보 수정 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴에서 ‘My Page’를 선택합니다.",
            "성함, 휴대번호 또는 관심 분야를 수정합니다.",
            "‘수정 완료’ 버튼을 누릅니다.",
            "수정 완료 안내를 확인합니다.",
        ],
    },
    GuideCategory.ACCOUNT_ID_CHANGE: {
        "title": "아이디 변경 안내",
        "steps": [
            "현재 My Page에서는 아이디로 사용하는 이메일을 변경할 수 없습니다.",
            "성함, 휴대번호, 관심 분야와 비밀번호는 My Page에서 변경할 수 있습니다.",
        ],
    },
    GuideCategory.PASSWORD_CHANGE: {
        "title": "비밀번호 변경 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴에서 ‘My Page’를 선택합니다.",
            "‘새 비밀번호’에 6자 이상의 비밀번호를 입력합니다.",
            "‘새 비밀번호 확인’에 같은 값을 입력합니다.",
            "‘수정 완료’ 버튼을 누릅니다.",
        ],
    },
    GuideCategory.LISTING_VIEW: {
        "title": "청약 공고 조회 방법",
        "steps": [
            "화면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
            "화면에 표시된 청약 공고 목록을 확인합니다.",
            "아래의 페이지 이동 기능으로 다른 공고를 확인합니다.",
        ],
    },
    GuideCategory.LISTING_SEARCH: {
        "title": "청약 공고 조건검색 방법",
        "steps": [
            "화면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
            "‘조건검색’ 영역을 펼칩니다.",
            "서울 자치구, 최대 보증금, 최대 월세를 입력합니다.",
            "‘검색’ 버튼을 누릅니다.",
            "조건에 맞는 검색 결과를 확인합니다.",
        ],
    },
    GuideCategory.LISTING_DETAIL: {
        "title": "청약 공고 상세 확인 방법",
        "steps": [
            "화면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
            "확인하려는 청약 공고를 찾습니다.",
            "공고 카드의 ‘상세 정보’ 영역을 펼칩니다.",
            "상세 내용과 원문 공고 링크를 확인합니다.",
        ],
        "notice": "신청 조건과 일정은 반드시 연결된 원문 공고에서 다시 확인해 주세요.",
    },
    GuideCategory.LISTING_PAGINATION: {
        "title": "청약 공고 페이지 이동 방법",
        "steps": [
            "화면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
            "목록 아래의 이전 또는 다음 버튼으로 페이지를 이동합니다.",
            "원하는 페이지 번호를 입력하고 ‘이동’ 버튼을 눌러 바로 이동할 수도 있습니다.",
        ],
    },
    GuideCategory.FAVORITE_ADD: {
        "title": "즐겨찾기 추가 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
            "관심 있는 공고의 ‘상세 정보’ 영역을 펼칩니다.",
            "‘즐겨찾기 추가’ 버튼을 누릅니다.",
            "즐겨찾기 등록 완료 안내를 확인합니다.",
        ],
    },
    GuideCategory.FAVORITE_VIEW: {
        "title": "즐겨찾기 확인 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴에서 ‘즐겨찾기’를 선택합니다.",
            "저장한 청약 공고 목록을 확인합니다.",
        ],
    },
    GuideCategory.FAVORITE_DELETE: {
        "title": "즐겨찾기 삭제 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴에서 ‘즐겨찾기’를 선택합니다.",
            "삭제하려는 공고에서 ‘즐겨찾기 삭제’ 버튼을 누릅니다.",
            "삭제 완료 안내를 확인합니다.",
        ],
    },
    GuideCategory.AI_CHAT_USAGE: {
        "title": "AI 채팅 상담 이용 방법",
        "steps": [
            "로그인을 진행합니다.",
            "화면 왼쪽 메뉴에서 ‘AI 채팅 상담’을 선택합니다.",
            "화면 아래 입력창에 궁금한 내용을 입력합니다.",
            "AI 답변을 확인합니다.",
            "상담을 보관하려면 ‘대화 저장’을 누릅니다.",
            "저장하지 않고 끝내려면 ‘대화 종료’를 누릅니다.",
            "저장된 상담은 ‘확인할 상담’에서 선택하고, 옆의 ‘✕’로 삭제할 수 있습니다.",
        ],
        "notice": "AI 답변은 검증된 정보가 아닐 수 있으므로 중요한 내용은 공식 공고와 담당 기관에서 확인해 주세요.",
    },
    GuideCategory.AI_GUIDE_SCOPE: {
        "title": "AI 안내원이 안내할 수 있는 내용",
        "steps": [
            "사이트 메뉴와 기능의 이용 방법을 안내할 수 있습니다.",
            "My Page, 청약정보 조회, 즐겨찾기와 AI 채팅 상담 사용법을 안내할 수 있습니다.",
            "간단한 청약 용어와 계산을 설명할 수 있습니다.",
            "공고 추천, 신청 자격 판단과 당첨 가능성은 안내하지 않습니다.",
        ],
    },
    GuideCategory.LOGOUT: {
        "title": "로그아웃 방법",
        "steps": [
            "화면 왼쪽 메뉴 아래에서 로그인한 이메일을 확인합니다.",
            "‘LOGOUT’ 버튼을 누릅니다.",
            "로그인 화면으로 이동했는지 확인합니다.",
        ],
    },
}


def _history_contents(messages: list[GuideMessage], question: str) -> list[dict]:
    limit = get_history_limit()
    selected = messages[-limit:] if limit else []
    contents = [
        {
            "role": "user" if item.role == "user" else "model",
            "parts": [{"text": item.content}],
        }
        for item in selected
    ]
    contents.append({"role": "user", "parts": [{"text": question}]})
    return contents


def _mock_classification(question: str) -> GuideClassification:
    text = question.replace(" ", "").lower()

    if any(
        word in text
        for word in ("추천", "자격", "당첨", "실시간", "내조건", "조건에맞는")
    ):
        category = GuideCategory.OUT_OF_SCOPE
    elif any(word in text for word in ("ai안내원", "안내원")) and any(
        word in text for word in ("뭘", "무엇", "어떤", "범위", "할수", "질문")
    ):
        category = GuideCategory.AI_GUIDE_SCOPE
    elif any(
        word in text
        for word in (
            "ai채팅",
            "채팅상담",
            "ai상담",
            "대화저장",
            "대화종료",
            "저장된상담",
            "상담삭제",
            "궁금한거물어",
            "궁금한것물어",
            "질문하려면",
        )
    ):
        category = GuideCategory.AI_CHAT_USAGE
    elif any(word in text for word in ("아이디", "이메일", "id")) and any(
        word in text for word in ("수정", "변경", "바꾸")
    ):
        category = GuideCategory.ACCOUNT_ID_CHANGE
    elif "비밀번호" in text and any(
        word in text for word in ("수정", "변경", "바꾸", "어떻게")
    ):
        category = GuideCategory.PASSWORD_CHANGE
    elif any(word in text for word in ("로그아웃", "logout")):
        category = GuideCategory.LOGOUT
    elif any(word in text for word in ("수정", "변경", "바꾸")) and any(
        word in text
        for word in (
            "내정보",
            "회원정보",
            "프로필",
            "성함",
            "닉네임",
            "휴대번호",
            "전화번호",
            "관심분야",
        )
    ):
        category = GuideCategory.PROFILE_EDIT
    elif any(word in text for word in ("내정보", "회원정보", "프로필", "회원가입때입력")):
        category = GuideCategory.PROFILE_VIEW
    elif "즐겨찾기" in text and any(word in text for word in ("삭제", "지우", "취소")):
        category = GuideCategory.FAVORITE_DELETE
    elif "즐겨찾기" in text and any(word in text for word in ("어디", "확인", "목록", "보여")):
        category = GuideCategory.FAVORITE_VIEW
    elif "즐겨찾기" in text or "관심공고" in text:
        category = GuideCategory.FAVORITE_ADD
    elif (
        "검색" in text and any(word in text for word in ("공고", "청약", "조건"))
    ) or any(word in text for word in ("지역으로", "보증금으로", "월세로")):
        category = GuideCategory.LISTING_SEARCH
    elif any(word in text for word in ("상세", "원문", "자세히")) and any(
        word in text for word in ("공고", "청약")
    ):
        category = GuideCategory.LISTING_DETAIL
    elif any(word in text for word in ("다음페이지", "이전페이지", "페이지이동", "페이지번호")):
        category = GuideCategory.LISTING_PAGINATION
    elif any(word in text for word in ("공고목록", "청약정보", "공고조회")):
        category = GuideCategory.LISTING_VIEW
    elif any(word in text for word in ("홈으로", "홈화면", "처음화면")):
        category = GuideCategory.HOME_GUIDE
    elif any(word in text for word in ("보증금뜻", "월세뜻", "청약뜻", "용어", "무엇인가", "뭐야")):
        return GuideClassification(
            category=GuideCategory.TERM_EXPLANATION,
            confidence=0.9,
            short_answer="테스트 모드의 간단한 용어 설명입니다. 실제 안내는 Gemini 모드에서 3문장 이내로 제공됩니다.",
        )
    elif any(char.isdigit() for char in text) and any(
        word in text for word in ("계산", "%", "퍼센트", "얼마")
    ):
        return GuideClassification(
            category=GuideCategory.SIMPLE_CALCULATION,
            confidence=0.9,
            short_answer="테스트 모드의 단순 계산 답변입니다.",
        )
    else:
        category = GuideCategory.OUT_OF_SCOPE

    return GuideClassification(category=category, confidence=0.9, short_answer=None)


def _parse_classification(raw_text: str) -> GuideClassification:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()
    try:
        return GuideClassification.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError, TypeError):
        return GuideClassification(
            category=GuideCategory.OUT_OF_SCOPE,
            confidence=0,
            short_answer=None,
        )


def classify_question(messages: list[GuideMessage], question: str) -> GuideClassification:
    if get_gemini_mode() == "mock":
        return _mock_classification(question)

    try:
        # 요청이 끝날 때까지 클라이언트 참조를 유지합니다. 임시 객체로 연결 호출하면
        # 최신 SDK에서 요청 전에 client가 닫힐 수 있습니다.
        client = get_gemini_client()
        response = client.models.generate_content(
            model=get_gemini_model(),
            contents=_history_contents(messages, question),
            config={
                "system_instruction": CLASSIFIER_PROMPT,
                "response_mime_type": "application/json",
            },
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 안내원이 질문을 분석하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from error

    classification = _parse_classification((getattr(response, "text", "") or "").strip())

    # Gemini가 "내 정보"를 일반 개인정보 요청으로 오해할 수 있습니다. 명확한 프로젝트
    # 사용법 표현은 허용 목록 안에서만 보정하고, 추천·자격 등 금지 질문은 보정하지 않습니다.
    local_check = _mock_classification(question)
    if (
        classification.category == GuideCategory.OUT_OF_SCOPE
        and local_check.category in GUIDES
    ):
        return local_check

    return classification


def create_guide_answer(messages: list[GuideMessage], question: str) -> GuideAnswer:
    classification = classify_question(messages, question)
    category = classification.category
    model = "mock-guide" if get_gemini_mode() == "mock" else get_gemini_model()
    limit = get_history_limit()
    history_count = len(messages[-limit:]) if limit else 0

    if classification.confidence < 0.5:
        return GuideAnswer(
            category=category,
            response_type="clarification",
            title="질문을 다시 알려주세요",
            answer=CLARIFICATION,
            model=model,
            history_count=history_count,
        )

    if category in GUIDES:
        guide = GUIDES[category]
        return GuideAnswer(
            category=category,
            response_type="guide",
            title=str(guide["title"]),
            steps=list(guide["steps"]),
            notice=guide.get("notice"),
            model=model,
            history_count=history_count,
        )

    if category in {GuideCategory.TERM_EXPLANATION, GuideCategory.SIMPLE_CALCULATION}:
        answer = (classification.short_answer or CLARIFICATION).strip()[:800]
        return GuideAnswer(
            category=category,
            response_type="answer",
            title="간단한 안내" if category == GuideCategory.TERM_EXPLANATION else "계산 결과",
            answer=answer,
            notice="중요한 신청 조건과 금액은 반드시 원문 공고에서 다시 확인해 주세요.",
            model=model,
            history_count=history_count,
        )

    return GuideAnswer(
        category=GuideCategory.OUT_OF_SCOPE,
        response_type="refusal",
        title="안내할 수 없는 질문입니다",
        answer=REFUSAL,
        model=model,
        history_count=history_count,
    )


def get_guide_profile(user_id: str, email: str) -> GuideProfile:
    """닉네임만 읽으며 프로필이나 대화를 저장·수정하지 않습니다."""

    try:
        result = get_supabase().table("profiles").select("nickname").eq("id", user_id).execute()
    except Exception as error:
        raise HTTPException(500, "프로필을 불러오지 못했습니다.") from error

    nickname = "회원"
    if result.data:
        nickname = (result.data[0].get("nickname") or "회원").strip()
    return GuideProfile(user_id=user_id, nickname=nickname, email=email)
