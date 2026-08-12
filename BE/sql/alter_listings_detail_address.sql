-- alter_listings_detail_address.sql
--
-- 이미 만들어져 있는 listings 테이블에 상세주소 칸을 하나 더합니다.
-- Supabase Dashboard의 SQL Editor에 전체를 붙여넣고 한 번만 실행하세요.
--
-- 자치구(location)만으로는 어느 동네인지 알기 어려워, 도로명 주소를 따로 담습니다.
--
-- 안전 사항
--   * 칸을 더하기만 합니다. 기존 값을 지우거나 바꾸지 않습니다.
--   * NULL을 허용합니다. 이미 등록된 공고는 빈 값으로 남고, 나중에 채워 넣을 수 있습니다.
--   * 여러 번 실행해도 괜찮습니다. (IF NOT EXISTS)

BEGIN;

ALTER TABLE listings
    ADD COLUMN IF NOT EXISTS detail_address VARCHAR(255);

COMMENT ON COLUMN listings.detail_address IS '상세주소 (도로명 주소). 자치구 아래 단위, 선택 입력';

COMMIT;

-- 확인용 조회입니다. 위 트랜잭션과 따로 실행하세요.
--   SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--   WHERE table_name = 'listings' AND column_name = 'detail_address';
