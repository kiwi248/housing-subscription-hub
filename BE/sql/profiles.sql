-- 기존 profiles 테이블에 회원 추가정보 열 추가
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS phone VARCHAR(13),
    ADD COLUMN IF NOT EXISTS birth_date DATE,
    ADD COLUMN IF NOT EXISTS interests JSONB NOT NULL DEFAULT '[]'::jsonb;


-- 신규 유저의 추가정보를 profiles에 저장하도록 기존 함수 변경
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (
        id,
        nickname,
        phone,
        birth_date,
        interests
    )
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'nickname',
        NEW.raw_user_meta_data->>'phone',
        NULLIF(NEW.raw_user_meta_data->>'birth_date', '')::DATE,
        COALESCE(
            NEW.raw_user_meta_data->'interests',
            '[]'::jsonb
        )
    );

    RETURN NEW;
END;
$$;