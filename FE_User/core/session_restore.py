# session_restore.py
"""새로고침 후 로그인 세션을 되살리는 판단 로직입니다.

브라우저를 새로고침하면 st.session_state가 비워지므로, 로그인 상태를 되살리려면
어딘가에 근거를 남겨 두어야 합니다. supabase-py는 Streamlit 서버에서 돌기 때문에
브라우저에는 Supabase 세션이 남지 않고, Python SDK의 세션 저장소도 프로세스 메모리라
새 요청에서는 비어 있습니다. 그래서 토큰을 브라우저 Session Storage에 두었다가
다시 읽어 옵니다.

여기에 담는 값은 access token과 refresh token 두 개뿐입니다.
비밀번호와 그 밖의 개인정보는 담지 않습니다.

Streamlit이나 Supabase에 직접 기대지 않는 함수만 모아 두어 테스트하기 쉽습니다.
"""

# 브라우저 Session Storage에서 쓰는 이름입니다.
STORAGE_KEY = "user_session_storage"
ACCESS_TOKEN_NAME = "sb_access_token"
REFRESH_TOKEN_NAME = "sb_refresh_token"


def read_tokens(stored_values: object) -> tuple[str, str]:
    """브라우저에서 읽어 온 값에서 토큰 두 개만 꺼냅니다.

    값이 없거나 공백뿐이면 빈 문자열로 봅니다.
    """

    if not isinstance(stored_values, dict):
        return "", ""

    access_token = stored_values.get(ACCESS_TOKEN_NAME) or ""
    refresh_token = stored_values.get(REFRESH_TOKEN_NAME) or ""

    return str(access_token).strip(), str(refresh_token).strip()


def should_restore(is_logged_in: bool, already_tried: bool, has_tokens: bool) -> bool:
    """지금 세션을 되살려야 하는지 정합니다.

    이미 로그인돼 있거나 이번 세션에서 한 번 시도했으면 다시 하지 않습니다.
    이 조건이 없으면 화면이 다시 그려질 때마다 Supabase에 요청해
    같은 요청을 되풀이하거나 화면이 계속 다시 실행됩니다.
    """

    if is_logged_in:
        return False

    if already_tried:
        return False

    return has_tokens


def restore_session(access_token: str, refresh_token: str, set_session) -> dict:
    """토큰으로 Supabase 세션을 되살립니다.

    set_session은 supabase.auth.set_session을 그대로 받습니다.
    만료된 세션은 SDK가 refresh token으로 갱신해 줍니다.

    돌려주는 status는 셋 중 하나입니다.
      empty    - 되살릴 토큰이 없음
      restored - 되살렸음. user_id, email, 갱신된 토큰이 함께 옵니다
      invalid  - 토큰이 잘못됐거나 갱신할 수 없음. 저장된 값을 지워야 합니다
    """

    if not access_token or not refresh_token:
        return {"status": "empty"}

    try:
        result = set_session(access_token, refresh_token)
    except Exception:
        # 만료·위조·네트워크 오류를 모두 여기서 받습니다.
        # 어느 쪽이든 로그인 상태로 만들지 않습니다.
        return {"status": "invalid"}

    session = getattr(result, "session", None)
    user = getattr(result, "user", None)

    if session is None or user is None:
        return {"status": "invalid"}

    # 이메일이나 ID만 보고 로그인 처리하지 않습니다.
    # Supabase가 확인해 준 사용자 정보만 씁니다.
    return {
        "status": "restored",
        "user_id": getattr(user, "id", "") or "",
        "email": getattr(user, "email", "") or "",
        # 갱신됐을 수 있으므로 돌려받은 토큰을 다시 저장합니다.
        "access_token": getattr(session, "access_token", "") or "",
        "refresh_token": getattr(session, "refresh_token", "") or "",
    }
