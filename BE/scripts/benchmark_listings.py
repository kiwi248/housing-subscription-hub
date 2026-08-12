"""청약정보 조회(GET /listings/getall) 응답 시간을 여러 번 재서 통계를 냅니다.

최적화 전/후 숫자를 비교하기 위한 일회성 측정 스크립트입니다.

사용법:
    python scripts/benchmark_listings.py
    python scripts/benchmark_listings.py --count 50
"""

import argparse
import statistics
import time

import httpx

BACKEND_URL = "http://127.0.0.1:8000"


def benchmark(count: int) -> None:
    durations_ms: list[float] = []

    for i in range(count):
        start = time.perf_counter()
        response = httpx.get(f"{BACKEND_URL}/listings/getall", timeout=15.0)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.raise_for_status()
        durations_ms.append(elapsed_ms)
        print(f"[{i + 1}/{count}] {elapsed_ms:.1f} ms")

    print()
    print(f"횟수: {count}")
    print(f"평균: {statistics.mean(durations_ms):.1f} ms")
    print(f"중간값: {statistics.median(durations_ms):.1f} ms")
    print(f"최소: {min(durations_ms):.1f} ms")
    print(f"최대: {max(durations_ms):.1f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()

    benchmark(args.count)
