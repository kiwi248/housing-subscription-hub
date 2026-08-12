from core.api_client import request


def login_process(username: str, password: str):
    return request("POST", "/admin/login", json={"username": username, "password": password})
