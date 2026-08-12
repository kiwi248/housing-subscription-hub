"""관리자 비밀번호를 안전하게 저장하고 로그인할 때 비교하는 함수입니다.

중요:
    비밀번호를 DB에 그대로 저장하면 안 됩니다.
    이 파일은 비밀번호를 원래 값으로 되돌릴 수 없는 해시 문자열로 바꿉니다.
"""

import hashlib
import hmac
import secrets

# PBKDF2 계산을 반복하는 횟수입니다.
# 반복 횟수가 많을수록 공격자가 비밀번호를 빠르게 대입하기 어려워집니다.
ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """비밀번호를 DB에 저장할 해시 문자열로 만듭니다."""

    # salt는 매번 새로 만드는 임의의 문자열입니다.
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS,
    ).hex()

    # 실제 저장 형태: pbkdf2_sha256$200000$salt값$비밀번호해시값
    return f"pbkdf2_sha256${ITERATIONS}${salt}${password_hash}"


def verify_password(password: str, saved_password: str) -> bool:
    """로그인 비밀번호가 DB에 저장된 해시와 같은지 확인합니다."""

    try:
        algorithm, iterations, salt, expected_hash = saved_password.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError):
        return False
