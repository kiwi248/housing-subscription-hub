"""아무 엔드포인트에나 동시 요청을 여러 개 보내서 API가 부하를 견디는지 확인합니다.

benchmark_listings.py가 "순차 요청 한 번의 응답시간"을 재는 스크립트라면,
이 스크립트는 "동시에 몰렸을 때 얼마나 실패하고 얼마나 느려지는지"를 봅니다.

부하를 발생시키는 동안 FE_Admin의 "로그 대시보드"를 열어 두면, 여기서 보낸 요청이
실시간으로 로그에 찍히는 것을 볼 수 있습니다 (가짜 시뮬레이터가 아니라 진짜 요청입니다).

사용법:
    python scripts/load_test.py --path /listings/getall
    python scripts/load_test.py --path /listings/search?location=강남구 --count 100 --concurrency 20
    python scripts/load_test.py --path /listings/get/999999 --count 30 --concurrency 10
"""

import argparse
import asyncio
import statistics
import time

import httpx

BACKEND_URL = "http://127.0.0.1:8000"


async def _one_request(client: httpx.AsyncClient, path: str) -> tuple[int | None, float]:
    start = time.perf_counter()
    try:
        response = await client.get(f"{BACKEND_URL}{path}")
        status_code = response.status_code
    except httpx.HTTPError:
        status_code = None
    elapsed_ms = (time.perf_counter() - start) * 1000
    return status_code, elapsed_ms


async def load_test(path: str, count: int, concurrency: int) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_request(client: httpx.AsyncClient):
        async with semaphore:
            return await _one_request(client, path)

    async with httpx.AsyncClient(timeout=30.0) as client:
        start = time.perf_counter()
        results = await asyncio.gather(*[bounded_request(client) for _ in range(count)])
        total_seconds = time.perf_counter() - start

    durations_ms = [elapsed for _, elapsed in results]
    status_codes = [status for status, _ in results]

    success_count = sum(1 for status in status_codes if status is not None and status < 500)
    error_count = count - success_count

    status_counts: dict[int | None, int] = {}
    for status in status_codes:
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"경로: {path}")
    print(f"총 요청: {count}건, 동시 실행: {concurrency}개")
    print(f"전체 소요 시간: {total_seconds:.2f}초 (초당 약 {count / total_seconds:.1f}건)")
    print(f"성공(5xx 아님): {success_count}/{count}, 실패(5xx/연결 오류): {error_count}/{count}")
    print("상태코드별 건수:", status_counts)
    print()
    print(f"응답시간 평균: {statistics.mean(durations_ms):.1f} ms")
    print(f"응답시간 중간값: {statistics.median(durations_ms):.1f} ms")
    print(f"응답시간 최소/최대: {min(durations_ms):.1f} / {max(durations_ms):.1f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="/listings/getall", help="쿼리 파라미터 포함 가능")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=10)
    args = parser.parse_args()

    asyncio.run(load_test(args.path, args.count, args.concurrency))
