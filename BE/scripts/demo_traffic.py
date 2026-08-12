"""시연용으로 배포된 백엔드에 안전한 warning급 트래픽을 만듭니다.

실제 데이터는 전혀 건드리지 않고, 아래 세 가지 방식으로만 warning을 만듭니다.
  - 존재하지 않는 청약정보 조회      -> 404
  - 관리자 로그인 실패(틀린 비밀번호) -> 401
  - 검색 조건에 잘못된 타입 전달     -> 422

실시간 로그 대시보드(FE_Admin)를 열어둔 채로 실행하면, 5초 안에
warning 항목이 쌓이는 걸 바로 확인할 수 있습니다.

사용법:
    python scripts/demo_traffic.py --url https://aio-01-p1-team1.onrender.com
    python scripts/demo_traffic.py --url https://aio-01-p1-team1.onrender.com --rounds 5 --delay 1.5
"""

import argparse
import time

import httpx


def make_warning_traffic(base_url: str) -> list[tuple[str, int | None]]:
    results: list[tuple[str, int | None]] = []

    with httpx.Client(timeout=30.0) as client:
        # 404: 존재하지 않는 청약정보 조회
        response = client.get(f"{base_url}/listings/get/999999999")
        results.append(("GET /listings/get/999999999 (없는 ID)", response.status_code))

        # 401: 관리자 로그인 실패
        response = client.post(
            f"{base_url}/admin/login",
            json={"username": "admin01", "password": "일부러_틀린_비밀번호"},
        )
        results.append(("POST /admin/login (틀린 비밀번호)", response.status_code))

        # 422: 검색 조건에 숫자 대신 문자열 전달
        response = client.get(
            f"{base_url}/listings/search",
            params={"max_deposit": "숫자아님"},
        )
        results.append(("GET /listings/search (잘못된 타입)", response.status_code))

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="예: https://aio-01-p1-team1.onrender.com")
    parser.add_argument("--rounds", type=int, default=3, help="반복 횟수")
    parser.add_argument("--delay", type=float, default=2.0, help="라운드 사이 대기 시간(초)")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")

    for round_number in range(1, args.rounds + 1):
        print(f"--- 라운드 {round_number}/{args.rounds} ---")
        for label, status in make_warning_traffic(base_url):
            print(f"{label} -> {status}")
        if round_number < args.rounds:
            time.sleep(args.delay)

    print("\n완료. FE_Admin 로그 대시보드에서 warning 항목이 쌓인 걸 확인하세요.")
