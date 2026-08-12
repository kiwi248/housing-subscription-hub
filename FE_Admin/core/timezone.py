"""BE가 UTC로 내려주는 시각을 화면에 한국 시간(KST)으로 보여주기 위한 도우미입니다."""

from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def to_kst_display(value: str) -> str:
    """ISO 8601 문자열을 'YYYY-MM-DD HH:MM:SS' 형태의 한국 시간 문자열로 바꿉니다.

    파싱할 수 없는 값은 원본을 그대로 돌려줍니다.
    """

    if not value:
        return value

    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return value

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
