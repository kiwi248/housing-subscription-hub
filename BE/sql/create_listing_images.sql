-- create_listing_images.sql
--
-- 공고 하나에 사진을 여러 장 붙일 수 있게 새 테이블을 만듭니다.
-- Supabase Dashboard의 SQL Editor에 전체를 붙여넣고 한 번만 실행하세요.
--
-- 왜 새 테이블인가
--   listings.image_url 은 칸이 하나뿐이라 사진을 한 장밖에 못 담습니다.
--   favorites 와 같은 모양으로 1:N 테이블을 따로 두면
--   사진 한 장만 지우거나 순서를 바꾸는 일이 간단해집니다.
--
-- listings.image_url 은 그대로 둡니다
--   목록 카드에 보여 줄 대표 이미지(썸네일)로 계속 씁니다.
--   이 칸을 없애지 않아 기존 화면과 테스트가 그대로 동작합니다.
--   대표 이미지는 sort_order = 0 인 행과 같은 값을 가리킵니다.
--
-- 안전 사항
--   * 테이블을 새로 만들기만 합니다. listings 를 바꾸지 않습니다.
--   * 이미 등록된 공고는 이 테이블에 행이 없습니다.
--     그래도 대표 이미지는 그대로 보이므로 화면이 깨지지 않습니다.
--   * 여러 번 실행해도 괜찮습니다. (IF NOT EXISTS)

BEGIN;

CREATE TABLE IF NOT EXISTS listing_images (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    listing_id BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    image_url  TEXT NOT NULL,           -- Storage에 올린 파일의 공개 URL
    sort_order INTEGER NOT NULL DEFAULT 0,  -- 0이 대표 이미지입니다
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 같은 공고에 같은 자리를 두 번 쓸 수 없습니다.
    CONSTRAINT uq_listing_images_order UNIQUE (listing_id, sort_order),
    CONSTRAINT ck_listing_images_sort_order CHECK (sort_order >= 0)
);

COMMENT ON TABLE  listing_images            IS '공고 사진. 공고 하나에 여러 장이 붙습니다.';
COMMENT ON COLUMN listing_images.listing_id IS '어느 공고의 사진인지. 공고를 지우면 함께 지워집니다.';
COMMENT ON COLUMN listing_images.image_url  IS 'Supabase Storage에 올린 파일의 공개 URL';
COMMENT ON COLUMN listing_images.sort_order IS '보여 줄 순서. 0이 대표 이미지이며 listings.image_url과 같은 값입니다.';

-- 공고별로 순서대로 읽는 조회가 대부분이라 두 칸을 함께 묶습니다.
CREATE INDEX IF NOT EXISTS idx_listing_images_listing_id
    ON listing_images(listing_id, sort_order);

-- 파일을 지워도 되는지 확인할 때 URL로 찾습니다.
CREATE INDEX IF NOT EXISTS idx_listing_images_image_url
    ON listing_images(image_url);

COMMIT;

-- 확인용 조회입니다. 위 트랜잭션과 따로 실행하세요.
--
--   -- 1) 테이블이 만들어졌는지
--   SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--   WHERE table_name = 'listing_images'
--   ORDER BY ordinal_position;
--
--   -- 2) 공고를 지우면 사진도 지워지도록 연결됐는지
--   SELECT tc.constraint_name, rc.delete_rule
--   FROM information_schema.table_constraints tc
--   JOIN information_schema.referential_constraints rc
--     ON tc.constraint_name = rc.constraint_name
--   WHERE tc.table_name = 'listing_images';
--   -- delete_rule 이 CASCADE 로 나오면 정상입니다.
