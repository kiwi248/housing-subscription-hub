# admin_service.py
from fastapi import HTTPException

from app.core.password import verify_password
from app.core.supabase_config import get_supabase
from app.schemas.admin_schema import AdminLogin, AdminPublic


def admin_login_process(admin: AdminLogin) -> AdminPublic:
    """ 관리자 로그인 (계정은 중앙에서 미리 부여) """
    db_admin = _admin_get(admin.username)
    if db_admin is None:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    if not verify_password(admin.password, db_admin["password"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    return AdminPublic.model_validate(db_admin)


# ------------------------------------------

def _admin_get(username: str) -> dict | None:
    supabase = get_supabase()

    result = (
        supabase.table("admins")
        .select("*")
        .eq("username", username)
        .execute()
    )
    if not result.data:
        return None
    return result.data[0]
