"""마이페이지에서 백엔드 프로필 API를 호출하는 함수들을 제공합니다."""

from core.api_client import request


def get_profile(user_id: str):
    """사용자 ID에 해당하는 프로필을 백엔드에서 조회합니다."""

    return request("GET", f"/profiles/{user_id}")


def update_profile(
    user_id: str,
    nickname: str,
    phone: str,
    interests: list[str],
):
    """닉네임·휴대번호·관심 분야를 백엔드에 전달해 수정합니다."""

    return request(
        "PUT",
        f"/profiles/{user_id}",
        json={
            "nickname": nickname,
            "phone": phone,
            "interests": interests,
        },
    )
