-- Supabase SQL Editor에서 실행합니다.
-- 테이블이 이미 존재한다면 CREATE TABLE 구문은 생략하세요.

-- ============================================
-- 1. profiles (유저 추가정보 - auth.users와 1:1)
--    회원가입/로그인은 Supabase Auth(auth.users)가 처리합니다.
--    지금은 Email 로그인만 사용하고, 나중에 Kakao/Google OAuth를 추가합니다.
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nickname    VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 신규 유저가 auth.users에 생기면 profiles 행을 자동 생성하는 트리거
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, nickname)
    VALUES (NEW.id, NEW.raw_user_meta_data->>'nickname');
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================
-- 2. admins (관리자 - 직접 관리, 회원가입 API 없음)
-- ============================================
CREATE TABLE IF NOT EXISTS admins (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    VARCHAR(50) NOT NULL UNIQUE,
    password    TEXT NOT NULL,              -- 반드시 해시해서 저장 (scripts/create_admin.py 참고)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================
-- 3. listings (청약정보)
--    한 행은 같은 공고 안의 '주택 1개 + 신청유형(면적) 1개'를 의미합니다.
--    같은 공고(title)라도 주택이나 면적이 다르면 행을 나눠서 저장합니다.
-- ============================================
CREATE TABLE IF NOT EXISTS listings (
    id                     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title                  VARCHAR(255) NOT NULL,   -- 공고명
    housing_name           VARCHAR(255) NOT NULL,   -- 주택명
    area_sqm               NUMERIC(10,2) NOT NULL,  -- 전용면적 (제곱미터)
    recruitment_count      INTEGER NOT NULL,        -- 모집 호수
    location               VARCHAR(50) NOT NULL,    -- 위치 (서울시 구 단위)
    detail_address         VARCHAR(255),            -- 상세주소 (도로명 주소, 선택)
    deposit                BIGINT NOT NULL,         -- 임대보증금 (원 단위)
    monthly_rent           BIGINT NOT NULL,         -- 월 임대료 (원 단위)
    application_start_date DATE NOT NULL,           -- 신청 시작일 (최신순 정렬)
    application_end_date   DATE NOT NULL,           -- 신청 종료일
    description            TEXT NOT NULL,           -- 상세 설명
    image_url              TEXT,                    -- 사진 URL (선택)
    source_url             TEXT NOT NULL,           -- 공고 원문 링크
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- 값의 범위를 DB에서 한 번 더 확인하는 제약조건입니다.
    CONSTRAINT ck_listings_area_sqm           CHECK (area_sqm > 0),
    CONSTRAINT ck_listings_recruitment_count  CHECK (recruitment_count > 0),
    CONSTRAINT ck_listings_deposit            CHECK (deposit >= 0),
    CONSTRAINT ck_listings_monthly_rent       CHECK (monthly_rent >= 0),
    CONSTRAINT ck_listings_application_period CHECK (application_end_date >= application_start_date)
);

-- ============================================
-- 4. favorites (즐겨찾기 - user_id는 auth.users를 참조하는 UUID)
-- ============================================
CREATE TABLE IF NOT EXISTS favorites (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    listing_id  BIGINT NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_favorites UNIQUE (user_id, listing_id)
);

-- ============================================
-- 검색/정렬 성능용 인덱스
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

CREATE INDEX IF NOT EXISTS idx_favorites_listing_id  ON favorites(listing_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user_id     ON favorites(user_id);
