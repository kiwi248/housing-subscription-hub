"""프로필 수정 요청과 조회 응답에 사용하는 데이터 모델입니다."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    """사용자가 마이페이지에서 변경할 수 있는 프로필 항목입니다."""

    nickname: str = Field(
        min_length=1,
        max_length=50,
        examples=["홍길동"],
    )
    phone: str = Field(
        pattern=r"^010-\d{4}-\d{4}$",
        examples=["010-1234-5678"],
    )
    interests: list[str] = Field(
        default_factory=list,
        examples=[["분양주택", "임대주택"]],
    )


class ProfilePublic(BaseModel):
    """백엔드가 사용자 화면에 반환하는 공개 프로필 정보입니다."""

    id: str = Field(
        examples=["b3f1c2a0-1234-4a5b-9c3d-abcdef123456"]
    )
    nickname: str | None = None
    phone: str | None = None
    interests: list[str] = Field(default_factory=list)
    created_at: datetime
