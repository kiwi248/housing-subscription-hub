-- 기존 listings 테이블에 지도 표시용 좌표를 추가합니다.
-- 기존 공고에는 좌표가 없으므로 NULL을 허용합니다.

BEGIN;

ALTER TABLE listings
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

COMMENT ON COLUMN listings.latitude IS '주택 위치의 위도';
COMMENT ON COLUMN listings.longitude IS '주택 위치의 경도';

ALTER TABLE listings
    DROP CONSTRAINT IF EXISTS ck_listings_latitude,
    DROP CONSTRAINT IF EXISTS ck_listings_longitude;

ALTER TABLE listings
    ADD CONSTRAINT ck_listings_latitude
        CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    ADD CONSTRAINT ck_listings_longitude
        CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180);

COMMIT;