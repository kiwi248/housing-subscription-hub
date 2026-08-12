from core.api_client import request


def get_logs(level: str | None = None, limit: int = 50):
    params = {"level": level, "limit": limit}
    return request("GET", "/logs", params=params)


def get_log_history(level: str | None = None, limit: int = 50):
    params = {"level": level, "limit": limit}
    return request("GET", "/logs/history", params=params)
