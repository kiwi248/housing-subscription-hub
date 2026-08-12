-- alter_listings.sql
--
-- 이미 만들어져 있는 listings 테이블을 최종 구조로 바꾸는 SQL입니다.
-- Supabase Dashboard의 SQL Editor에 전체를 붙여넣고 한 번만 실행하세요.
--
-- 최종 구조의 의미:
--   listings 한 행 = 같은 공고 안의 '주택 1개 + 신청유형(면적) 1개'
--   같은 공고(title)라도 주택이나 면적이 다르면 행을 나눠서 저장합니다.
--
-- ============================================
-- 안전장치 1: 트랜잭션
-- ============================================
-- 아래 모든 변경은 BEGIN; 과 COMMIT; 사이에서 실행됩니다.
-- 중간에 오류가 한 번이라도 나면 그 앞에서 성공했던 변경까지 전부 취소되고
-- 테이블은 실행 전 상태로 되돌아갑니다.
-- 따라서 '절반만 바뀐' 어중간한 상태가 생기지 않습니다.
--
-- ============================================
-- 안전장치 2: 데이터 0건 자동 검사
-- ============================================
-- housing_name, area_sqm, recruitment_count, deposit, monthly_rent를
-- 기본값 없이 NOT NULL로 추가하기 때문에, 기존 데이터가 있으면 값을 채울 수 없습니다.
-- 그래서 컬럼을 바꾸기 전에 DO 블록으로 listings가 비어 있는지 먼저 검사합니다.
-- 데이터가 한 건이라도 있으면 예외가 발생하고, 트랜잭션이 취소되어
-- 이후 SQL은 하나도 실행되지 않습니다.
--
-- ============================================
-- 안전성
-- ============================================
-- 이 SQL은 listings 테이블을 DROP 하지 않습니다.
-- favorites 테이블은 전혀 건드리지 않습니다.
-- favorites.listing_id -> listings(id) 외래키와 ON DELETE CASCADE는 그대로 유지됩니다.
--   이유: 외래키가 참조하는 listings.id 컬럼을 바꾸지 않기 때문입니다.
--
-- ============================================
-- 참고
-- ============================================
-- 2번 단계의 RENAME COLUMN에는 IF EXISTS를 쓸 수 없습니다.
-- 이미 이름을 바꾼 뒤 다시 실행하면 그 줄에서 오류가 나지만,
-- 트랜잭션 덕분에 테이블이 망가지지 않고 그대로 유지됩니다.


BEGIN;


-- ============================================
-- 0. listings 데이터가 0건인지 검사
--    데이터가 있으면 여기서 멈추고 아래 SQL은 실행되지 않습니다.
-- ============================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM listings LIMIT 1) THEN
        RAISE EXCEPTION
            'listings 테이블에 데이터가 있어 구조를 변경할 수 없습니다. 데이터를 먼저 백업하고 비운 뒤 다시 실행하세요.';
    END IF;
END
$$;


-- ============================================
-- 1. 더 이상 쓰지 않는 인덱스 삭제
--    컬럼을 삭제하면 그 컬럼의 인덱스도 함께 사라지지만,
--    무엇을 없애는지 눈에 보이도록 먼저 명시적으로 삭제합니다.
-- ============================================
DROP INDEX IF EXISTS idx_listings_type;
DROP INDEX IF EXISTS idx_listings_price;
DROP INDEX IF EXISTS idx_listings_eligibility;
DROP INDEX IF EXISTS idx_listings_announced_at;


-- ============================================
-- 2. 컬럼 이름 변경
--    데이터는 그대로 두고 이름만 바꿉니다.
-- ============================================
ALTER TABLE listings RENAME COLUMN announced_at TO application_start_date;
ALTER TABLE listings RENAME COLUMN deadline     TO application_end_date;


-- ============================================
-- 3. 사용하지 않는 컬럼 삭제
-- ============================================
ALTER TABLE listings DROP COLUMN IF EXISTS type;
ALTER TABLE listings DROP COLUMN IF EXISTS price;
ALTER TABLE listings DROP COLUMN IF EXISTS eligibility;


-- ============================================
-- 4. 새 컬럼 추가
--    0번 단계에서 데이터가 0건인 것을 확인했으므로
--    기본값 없이 NOT NULL로 추가할 수 있습니다.
-- ============================================
ALTER TABLE listings ADD COLUMN IF NOT EXISTS housing_name      VARCHAR(255)  NOT NULL;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS area_sqm          NUMERIC(10,2) NOT NULL;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS recruitment_count INTEGER       NOT NULL;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS deposit           BIGINT        NOT NULL;
ALTER TABLE listings ADD COLUMN IF NOT EXISTS monthly_rent      BIGINT        NOT NULL;


-- ============================================
-- 5. 기존 컬럼의 타입과 NOT NULL 조건 변경
--    location은 서울시 구 이름만 저장하므로 길이를 50으로 줄입니다.
--    타입을 바꾸면 idx_listings_location 인덱스는 PostgreSQL이 자동으로 다시 만듭니다.
-- ============================================
ALTER TABLE listings ALTER COLUMN location TYPE VARCHAR(50);

ALTER TABLE listings ALTER COLUMN location               SET NOT NULL;
ALTER TABLE listings ALTER COLUMN description            SET NOT NULL;
ALTER TABLE listings ALTER COLUMN source_url             SET NOT NULL;
ALTER TABLE listings ALTER COLUMN application_start_date SET NOT NULL;
ALTER TABLE listings ALTER COLUMN application_end_date   SET NOT NULL;

-- title은 이미 NOT NULL이라 바꾸지 않습니다.
-- image_url은 선택 입력이라 NULL을 그대로 허용합니다.
-- created_at은 이미 NOT NULL DEFAULT now()라 바꾸지 않습니다.


-- ============================================
-- 6. CHECK 제약조건 추가
--    같은 이름의 제약조건이 있으면 먼저 지우고 다시 만듭니다.
-- ============================================
ALTER TABLE listings DROP CONSTRAINT IF EXISTS ck_listings_area_sqm;
ALTER TABLE listings ADD  CONSTRAINT ck_listings_area_sqm
    CHECK (area_sqm > 0);

ALTER TABLE listings DROP CONSTRAINT IF EXISTS ck_listings_recruitment_count;
ALTER TABLE listings ADD  CONSTRAINT ck_listings_recruitment_count
    CHECK (recruitment_count > 0);

ALTER TABLE listings DROP CONSTRAINT IF EXISTS ck_listings_deposit;
ALTER TABLE listings ADD  CONSTRAINT ck_listings_deposit
    CHECK (deposit >= 0);

ALTER TABLE listings DROP CONSTRAINT IF EXISTS ck_listings_monthly_rent;
ALTER TABLE listings ADD  CONSTRAINT ck_listings_monthly_rent
    CHECK (monthly_rent >= 0);

ALTER TABLE listings DROP CONSTRAINT IF EXISTS ck_listings_application_period;
ALTER TABLE listings ADD  CONSTRAINT ck_listings_application_period
    CHECK (application_end_date >= application_start_date);


-- ============================================
-- 7. 새 인덱스 생성
--    idx_listings_location은 이미 있으므로 IF NOT EXISTS로 건너뜁니다.
-- ============================================
-- 위치는 '강남구'처럼 정확히 일치하는 값으로 검색합니다.
CREATE INDEX IF NOT EXISTS idx_listings_location               ON listings(location);
-- 보증금과 월세는 최소~최대 범위로 검색합니다.
CREATE INDEX IF NOT EXISTS idx_listings_deposit                ON listings(deposit);
CREATE INDEX IF NOT EXISTS idx_listings_monthly_rent           ON listings(monthly_rent);
-- 신청 시작일은 최신순 정렬에 사용하므로 DESC로 만듭니다.
CREATE INDEX IF NOT EXISTS idx_listings_application_start_date ON listings(application_start_date DESC);
-- 신청 종료일은 마감 임박순 정렬이나 마감 지난 공고 제외에 사용합니다.
CREATE INDEX IF NOT EXISTS idx_listings_application_end_date   ON listings(application_end_date);


COMMIT;


-- ============================================
-- 8. 실행 후 확인용 쿼리
--    아래 쿼리를 하나씩 복사해서 실행하면 결과를 확인할 수 있습니다.
--    COMMIT 뒤에 있으므로 위 변경과는 별개로 동작합니다.
-- ============================================
-- 컬럼 목록 확인 (14개가 나와야 합니다)
--     SELECT column_name, data_type, is_nullable, column_default
--     FROM information_schema.columns
--     WHERE table_name = 'listings'
--     ORDER BY ordinal_position;
--
-- CHECK 제약조건 확인 (ck_listings_로 시작하는 5개가 나와야 합니다)
--     SELECT conname, pg_get_constraintdef(oid)
--     FROM pg_constraint
--     WHERE conrelid = 'listings'::regclass AND contype = 'c'
--     ORDER BY conname;
--
-- 인덱스 확인 (PK 포함 6개가 나와야 합니다)
--     SELECT indexname, indexdef
--     FROM pg_indexes
--     WHERE tablename = 'listings'
--     ORDER BY indexname;
--
-- favorites 외래키가 그대로인지 확인 (fk 1개가 ON DELETE CASCADE로 나와야 합니다)
--     SELECT conname, pg_get_constraintdef(oid)
--     FROM pg_constraint
--     WHERE conrelid = 'favorites'::regclass AND contype = 'f';
