# image_delete.py
"""공고 수정 화면에서 현재 이미지를 지울 때 쓰는 판단 함수들입니다.

이미지 삭제는 되돌릴 수 없으므로, 버튼을 한 번 누른 것만으로 지우지 않고
경고창에서 다시 한 번 고르게 합니다. 그 단계 판단과 요청 만들기를 여기 모아 두어
Streamlit 없이도 확인할 수 있게 했습니다.

Storage 파일을 지우는 일은 여기서 하지 않습니다. 백엔드 서비스가 맡습니다.
"""

# 삭제 확인이 어디까지 왔는지 나타내는 값입니다.
IDLE = "idle"              # 아직 아무것도 누르지 않음
CONFIRMING = "confirming"  # 경고창을 띄운 상태. 여기서는 아직 지우지 않습니다.


def should_show_delete_button(image_url: object) -> bool:
    """지금 이미지가 있을 때만 삭제 버튼을 보여 줍니다."""

    if not isinstance(image_url, str):
        return False

    return bool(image_url.strip())


def next_step(current_step: str, clicked_delete_button: bool, clicked_cancel: bool) -> str:
    """버튼을 눌렀을 때 확인 단계가 어떻게 바뀌는지 정합니다.

    삭제 버튼을 눌러도 CONFIRMING까지만 갑니다. 실제 삭제는 경고창에서 따로 고릅니다.
    """

    if clicked_cancel:
        return IDLE

    if clicked_delete_button:
        return CONFIRMING

    return current_step


def build_delete_request(listing_id: int) -> dict[str, int]:
    """이미지 삭제 요청에 실어 보낼 값을 만듭니다.

    공고 id 하나만 담습니다. 제목·보증금·월세처럼 화면에 입력만 해 두고
    아직 저장하지 않은 값은 절대 담지 않습니다.
    """

    return {"listing_id": int(listing_id)}


def summarize_result(response: object) -> tuple[bool, str]:
    """삭제 API 결과를 화면에 보여 줄 문구로 바꿉니다.

    성공 여부와 문구를 함께 돌려줍니다. 실패하면 원인을 알 수 있게
    서버가 준 문구를 그대로 보여 줍니다.
    """

    if not isinstance(response, dict):
        return False, "이미지 삭제에 실패했습니다."

    if response.get("success"):
        return True, response.get("message") or "이미지를 삭제했습니다."

    return False, response.get("message") or "이미지 삭제에 실패했습니다."
