"""관리자 계정을 admins 테이블에 등록하는 스크립트입니다.

관리자 계정은 회원가입 API가 없고 중앙에서 부여하므로, 이 스크립트로 직접 생성합니다.

사용법:
    python scripts/create_admin.py admin01 pwd1234
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.password import hash_password
from app.core.supabase_config import get_supabase


def create_admin(username: str, password: str) -> None:
    supabase = get_supabase()
    result = (
        supabase.table("admins")
        .insert(
            {
                "username": username,
                "password": hash_password(password),
            }
        )
        .execute()
    )
    if not result.data:
        print("관리자 계정 생성에 실패했습니다.")
        return
    print(f"관리자 계정이 생성되었습니다: {result.data[0]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python scripts/create_admin.py <username> <password>")
        sys.exit(1)

    create_admin(sys.argv[1], sys.argv[2])
