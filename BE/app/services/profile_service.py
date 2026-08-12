"""Supabase의 사용자 프로필을 조회하고 수정하는 서비스입니다."""

from fastapi import HTTPException

from app.core.supabase_config import get_supabase
from app.schemas.profile_schema import ProfilePublic, ProfileUpdate


def profile_get(user_id: str) -> ProfilePublic | None:
    """사용자 ID로 프로필을 조회하며, 존재하지 않으면 ``None``을 반환합니다."""

    supabase = get_supabase()

    result = (
        supabase.table("profiles")
        .select("*")
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        return None

    return ProfilePublic.model_validate(result.data[0])


def profile_update(user_id: str, profile: ProfileUpdate) -> ProfilePublic | None:
    """휴대번호 중복을 검사한 뒤 사용자 프로필을 수정합니다.

    다른 사용자가 같은 휴대번호를 사용 중이면 HTTP 409 오류를 발생시킵니다.
    """

    supabase = get_supabase()

    same_phone = (
        supabase.table("profiles")
        .select("id")
        .eq("phone", profile.phone)
        .neq("id", user_id)
        .execute()
    )

    if same_phone.data:
        raise HTTPException(
            status_code=409,
            detail="이미 사용 중인 휴대번호입니다.",
        )

    result = (
        supabase.table("profiles")
        .update(
            {
                "nickname": profile.nickname,
                "phone": profile.phone,
                "interests": profile.interests,
            }
        )
        .eq("id", user_id)
        .execute()
    )

    if not result.data:
        return None

    return ProfilePublic.model_validate(result.data[0])
