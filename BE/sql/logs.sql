-- 실시간 로그 중 warning/error만 이력용으로 저장하는 테이블입니다.
-- info 로그는 메모리(deque)에만 남기고 여기엔 저장하지 않습니다.

CREATE TABLE IF NOT EXISTS logs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,       -- 로그가 생성된 시각 (deque 엔트리의 time과 동일)
    level       VARCHAR(10) NOT NULL CHECK (level IN ('warning', 'error')),
    screen      VARCHAR(50) NOT NULL,
    message     TEXT NOT NULL,
    latency_ms  INT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()   -- DB에 저장된 시각
);

-- 최신순 조회, level별 조회용 인덱스
CREATE INDEX IF NOT EXISTS idx_logs_time  ON logs(time DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
