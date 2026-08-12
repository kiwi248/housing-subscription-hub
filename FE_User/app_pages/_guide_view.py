"""Streamlit과 분리해 테스트할 수 있는 AI 안내원 표시 함수입니다."""


def format_answer(data: dict) -> str:
    title = str(data.get("title") or "AI 안내원 답변")
    lines = [f"### {title}"]

    for index, step in enumerate(data.get("steps") or [], start=1):
        lines.append(f"{index}. {step}")

    if answer := data.get("answer"):
        lines.append(str(answer))

    if notice := data.get("notice"):
        lines.append(f"> {notice}")

    return "\n\n".join(lines)
