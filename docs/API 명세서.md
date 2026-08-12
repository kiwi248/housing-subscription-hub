# API 명세서

> 담당자: aio-01-p1-team1 / hyunport / 권오현
>
> 문서 버전: 1.0
>
> API 버전 정책: 별도 URL 버전 체계 없음
>
> 이 문서는 최종 서비스에서 실제로 제공하고 호출하는 API를 대상으로 하며, 백엔드 라우터·요청/응답 모델·서비스 로직·프런트엔드 호출 코드와 FastAPI OpenAPI 결과를 종합하여 작성했다.

## 1. 문서 정보

### 1.1 목적 및 범위

본 문서는 공공임대 및 분양 청약 통합 안내 서비스의 FastAPI 백엔드가 제공하는 REST API를 정의한다. 관리자, 프로필, 청약정보, 즐겨찾기, 로그, 위치·생활권, AI 상담 및 AI 안내원 API의 메서드·경로·인증·요청·응답·오류를 기술한다.

### 1.2 배포 및 공통 정보

| 항목 | 내용 |
| --- | --- |
| 사용자 웹 서비스 | `https://aio-01-p1-team1-user.streamlit.app/` |
| 관리자 웹 서비스 | `https://aio-01-p1-team1-admi.streamlit.app/` |
| 백엔드 Base URL | `https://aio-01-p1-team1.onrender.com` |
| 로컬 Base URL | `http://127.0.0.1:8000` |
| Swagger UI | `https://aio-01-p1-team1.onrender.com/docs` |
| OpenAPI JSON | `https://aio-01-p1-team1.onrender.com/openapi.json` |
| OpenAPI 표시 버전 | `0.1.0` *(FastAPI 문서 메타데이터이며 `/v1` 같은 URL 버전은 아님)* |
| 요청·응답 형식 | `application/json` |
| 이미지 요청 형식 | `multipart/form-data` |
| 사용자 인증 | AI API에 Supabase Bearer access token 사용 |
| CORS | `ALLOWED_ORIGINS` 환경변수, 코드 기본값 `*` |

### 1.3 기술 연동

| 서비스 | 사용 목적 |
| --- | --- |
| Supabase Auth | 사용자 회원가입·로그인 및 AI API 토큰 검증 |
| Supabase PostgreSQL | 프로필, 청약정보, 즐겨찾기, 로그 및 설정에 따른 상담 요약 저장 |
| Supabase Storage | 청약정보 이미지 저장 |
| Google Gemini | AI 상담 답변·상담 요약·AI 안내원 질문 분류·관리자 공고문 청약정보 자동 추출 |
| Upstash Redis | 진행 중인 AI 상담 기록의 사용자별 임시 저장 |
| Kakao Local API | 주소 좌표 변환 및 주변 생활시설 검색 |

## 2. 공통 규칙

### 2.1 공통 성공 응답

모든 API는 다음 공통 응답 객체를 사용한다.

```json
{
  "success": true,
  "message": "처리 결과 설명",
  "data": {}
}
```

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `success` | boolean | Y | 요청 성공 여부 |
| `message` | string | Y | 사용자에게 표시할 결과 메시지 |
| `data` | object · array · null | N | 기능별 응답 데이터 |

### 2.2 공통 오류 응답

HTTP 예외와 입력값 검증 오류는 공통 처리기를 거쳐 반환된다.

```json
{
  "success": false,
  "message": "오류 메시지"
}
```

입력값 검증 실패 응답:

```json
{
  "success": false,
  "message": "입력 내용을 확인해 주세요."
}
```

| 상태 코드 | 의미 | 발생 예 |
| --- | --- | --- |
| `200 OK` | 요청 성공 | 조회·등록·수정·삭제 성공 |
| `400 Bad Request` | 잘못된 요청 | 잘못된 정렬값, 이미지 규칙 충돌, 저장할 상담 없음 |
| `401 Unauthorized` | 인증 실패 | 관리자 로그인 실패, AI 토큰 누락·만료 |
| `404 Not Found` | 리소스 없음 | 프로필·공고·즐겨찾기·상담 요약 없음 |
| `409 Conflict` | 중복·충돌 | 즐겨찾기 중복, 휴대번호 중복 |
| `422 Unprocessable Entity` | 요청값 검증 실패 | 필수값 누락, 타입·길이·범위 오류 |
| `500 Internal Server Error` | 서버·DB·설정 오류 | 저장 실패, 필수 API 키 미설정 |
| `502 Bad Gateway` | 외부 서비스 오류 | Gemini·Kakao API 오류 |
| `503 Service Unavailable` | 임시 저장소 오류 | Redis 연결 실패 |
| `504 Gateway Timeout` | 외부 서비스 시간 초과 | Kakao 위치 검색 지연 |

### 2.3 인증

AI 보호 API는 다음 헤더가 필요하다.

```http
Authorization: Bearer {Supabase access token}
```

토큰은 Supabase Auth의 `get_user()`로 검증하며 토큰에서 사용자 ID와 이메일을 가져온다.

- 인증 불필요: `/chat/health`, `/ai-guide/health`
- Bearer 인증 필요: 그 외 `/chat/*`, `/ai-guide/*`
- 현재 `/admin/*`, `/profiles/*`, `/favorites/*`에는 백엔드 토큰 검증이 적용되지 않는다.

사용자 회원가입·로그인과 비밀번호 변경은 FE_User가 Supabase Auth를 직접 호출하므로 이 백엔드 REST API 목록에는 포함되지 않는다.

## 3. API 목록

최종 `app.main:app`에는 총 35개 HTTP operation이 등록되어 있다.

| 분류 | Method | 경로 | 설명 | 인증 |
| --- | --- | --- | --- | --- |
| 관리자 | POST | `/admin/login` | 관리자 로그인 | 없음 |
| 관리자 | POST | `/admin/listings/create` | 청약정보 등록 | 없음 |
| 관리자 | POST | `/admin/listings/images` | 이미지 1장 업로드 | 없음 |
| 관리자 | POST | `/admin/listings/images/bulk` | 이미지 여러 장 업로드 | 없음 |
| 관리자 | PUT | `/admin/listings/update/{listing_id}` | 청약정보 수정 | 없음 |
| 관리자 | DELETE | `/admin/listings/{listing_id}/image` | 대표 이미지 삭제 | 없음 |
| 관리자 | PUT | `/admin/listings/{listing_id}/images` | 사진 목록 교체 | 없음 |
| 관리자 | DELETE | `/admin/listings/delete/{listing_id}` | 청약정보 삭제 | 없음 |
| 관리자 | GET | `/admin/favorites/ranking` | 즐겨찾기 순위 조회 | 없음 |
| 관리자 | GET | `/admin/favorites/detail` | 즐겨찾기 상세 조회 | 없음 |
| 프로필 | GET | `/profiles/{user_id}` | 프로필 조회 | 없음 |
| 프로필 | PUT | `/profiles/{user_id}` | 프로필 수정 | 없음 |
| 청약정보 | GET | `/listings/getall` | 전체 조회 | 없음 |
| 청약정보 | GET | `/listings/page` | 페이지 조회 | 없음 |
| 청약정보 | GET | `/listings/search` | 조건검색 | 없음 |
| 청약정보 | GET | `/listings/get/{listing_id}` | 상세 조회 | 없음 |
| 즐겨찾기 | POST | `/favorites/create` | 즐겨찾기 등록 | 없음 |
| 즐겨찾기 | GET | `/favorites/mypage/{user_id}` | 사용자 즐겨찾기 조회 | 없음 |
| 즐겨찾기 | DELETE | `/favorites/delete/{user_id}/{listing_id}` | 즐겨찾기 삭제 | 없음 |
| 로그 | GET | `/logs` | 최근 요청 로그 조회 | 없음 |
| 로그 | GET | `/logs/history` | 저장된 경고·오류 로그 조회 | 없음 |
| 위치 | GET | `/locations/geocode` | 주소 좌표 변환 | 없음 |
| 위치 | GET | `/locations/nearby-subways` | 주변 지하철역 조회 | 없음 |
| 위치 | GET | `/locations/nearby-facilities` | 주변 생활시설 조회 | 없음 |
| AI 상담 | GET | `/chat/health` | AI 상담 상태 확인 | 없음 |
| AI 상담 | GET | `/chat/me` | 상담 사용자 조회 | Bearer |
| AI 상담 | POST | `/chat/message` | 상담 답변 생성 | Bearer |
| AI 상담 | GET | `/chat/history` | 진행 중 상담 조회 | Bearer |
| AI 상담 | DELETE | `/chat/history` | 진행 중 상담 종료 | Bearer |
| AI 상담 | POST | `/chat/save` | 상담 요약 저장 | Bearer |
| AI 상담 | GET | `/chat/summaries` | 저장된 상담 조회 | Bearer |
| AI 상담 | DELETE | `/chat/summaries/{summary_id}` | 저장된 상담 삭제 | Bearer |
| AI 안내원 | GET | `/ai-guide/health` | 안내원 상태 확인 | 없음 |
| AI 안내원 | GET | `/ai-guide/me` | 안내원 사용자 조회 | Bearer |
| AI 안내원 | POST | `/ai-guide/message` | 사이트 사용법·용어 안내 | Bearer |

## 4. 관리자 API

### 4.1 관리자 로그인

`POST /admin/login`

```json
{
  "username": "admin01",
  "password": "pwd1234"
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `username` | string | Y | 1~50자 |
| `password` | string | Y | 1자 이상 |

성공 시 비밀번호를 제외한 관리자 정보를 `data`로 반환한다.

| 상태 | 발생 조건 |
| --- | --- |
| 200 | 로그인 성공 |
| 401 | 아이디 또는 비밀번호 불일치 |
| 422 | 요청값 검증 실패 |

### 4.2 청약정보 등록

`POST /admin/listings/create`

Content-Type: `application/json`

```json
{
  "title": "행복주택 입주자 모집공고",
  "housing_name": "강남 행복주택",
  "area_sqm": 39.72,
  "recruitment_count": 12,
  "location": "강남구",
  "detail_address": "서울 강남구 도곡로 464",
  "deposit": 50000000,
  "monthly_rent": 350000,
  "application_start_date": "2026-08-20",
  "application_end_date": "2026-08-27",
  "description": "전용면적 39.72㎡ 입주자를 모집합니다.",
  "image_url": null,
  "image_urls": [],
  "source_url": "https://apply.lh.or.kr/"
}
```

- 성공: `200`, 등록된 청약정보 반환
- 오류: `422` 필드 검증 실패, `500` 등록 실패

관리자 자동등록 화면에서는 공고문을 Gemini로 분석해 위 요청 형식의 초깃값을 만든다. 관리자가 내용을 검토·수정한 후 이미지가 있으면 `POST /admin/listings/images/bulk`, 최종 등록 시 `POST /admin/listings/create`를 호출한다. Gemini 분석 자체는 관리자 프런트엔드에서 수행하므로 별도의 백엔드 자동등록 API는 없다.

### 4.3 이미지 1장 업로드

`POST /admin/listings/images`

Content-Type: `multipart/form-data`

| Form 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `image` | binary | Y | JPEG·PNG·WebP 이미지, 최대 5MB |

```json
{
  "success": true,
  "message": "이미지를 업로드했습니다.",
  "data": {"image_url": "https://..."}
}
```

빈 파일, 5MB 초과, 허용되지 않은 MIME 형식 또는 실제 파일 시그니처는 `400`이다.

### 4.4 이미지 여러 장 업로드

`POST /admin/listings/images/bulk`

| Form 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `images` | binary[] | Y | JPEG·PNG·WebP, 최대 20장, 파일당 5MB·요청 전체 60MB 이하 |

```json
{
  "success": true,
  "message": "이미지 2장을 업로드했습니다.",
  "data": {"image_urls": ["https://.../1.jpg", "https://.../2.jpg"]}
}
```

한 장이라도 실패하면 이번 요청에서 업로드한 파일을 정리한다.

### 4.5 청약정보 수정

`PUT /admin/listings/update/{listing_id}`

Content-Type: `multipart/form-data`

| 필드 | 위치 | 타입 | 필수 | 제약·설명 |
| --- | --- | --- | --- | --- |
| `listing_id` | path | integer | Y | 수정 대상 ID |
| `title` | form | string | Y | 1~255자 |
| `housing_name` | form | string | Y | 1~255자 |
| `area_sqm` | form | decimal | Y | 0보다 큼 |
| `recruitment_count` | form | integer | Y | 0보다 큼 |
| `location` | form | string | Y | 1~50자 |
| `deposit` | form | integer | Y | 0 이상 |
| `monthly_rent` | form | integer | Y | 0 이상 |
| `application_start_date` | form | date | Y | `YYYY-MM-DD` |
| `application_end_date` | form | date | Y | `YYYY-MM-DD` |
| `description` | form | string | Y | 공백 불가 |
| `source_url` | form | string | Y | 공백 불가 |
| `detail_address` | form | string | N | 최대 255자, 공백은 null 처리 |
| `image` | form | binary | N | 새 대표 이미지 |
| `remove_image` | form | boolean | N | 기본 false |

새 이미지와 `remove_image=true`를 동시에 보내면 `400`이다. 대상이 없으면 `404`, 수정 실패는 `500`이다.

### 4.6 대표 이미지 삭제

`DELETE /admin/listings/{listing_id}/image`

공고는 유지하고 대표 이미지만 제거한다. 이미지가 이미 없는 경우도 `200`으로 처리한다.

### 4.7 사진 목록 교체

`PUT /admin/listings/{listing_id}/images`

Content-Type: `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `keep_count` | integer | Y | 유지할 기존 사진 수, 0 이상 |
| `kept_image_urls` | string[] | N | 유지할 기존 사진 URL |
| `images` | binary[] | N | 새로 추가할 이미지 |

`keep_count`와 URL 목록 길이가 다르면 사진을 삭제하지 않고 `400`을 반환한다. 기존 유지 사진과 새 사진의 합은 최대 20장이다. 첫 장이 대표 이미지가 된다.

### 4.8 청약정보 삭제

`DELETE /admin/listings/delete/{listing_id}`

공고 삭제 후 연결된 Storage 이미지도 정리한다.

- `404`: 청약정보 없음
- `500`: 삭제 실패

### 4.9 즐겨찾기 순위 조회

`GET /admin/favorites/ranking`

```json
[
  {"listing_id": 1, "title": "행복주택 공고", "favorite_count": 12}
]
```

### 4.10 즐겨찾기 상세 조회

`GET /admin/favorites/detail?listing_id={integer}`

`listing_id`는 선택값이다. 생략하면 전체를 조회한다.

응답 항목: `favorite_id`, `user_id`, `nickname`, `listing_id`, `title`, `created_at`.

## 5. 프로필 API

### 5.1 프로필 조회

`GET /profiles/{user_id}`

```json
{
  "success": true,
  "message": "프로필을 조회했습니다.",
  "data": {
    "id": "user-uuid",
    "nickname": "홍길동",
    "phone": "010-1234-5678",
    "interests": ["임대주택"],
    "created_at": "2026-08-11T12:00:00Z"
  }
}
```

- `404`: 프로필 없음

### 5.2 프로필 수정

`PUT /profiles/{user_id}`

```json
{
  "nickname": "홍길동",
  "phone": "010-1234-5678",
  "interests": ["분양주택", "임대주택"]
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `nickname` | string | Y | 1~50자 |
| `phone` | string | Y | `010-0000-0000` 형식 |
| `interests` | string[] | N | 기본 빈 배열 |

- `404`: 프로필 없음
- `409`: 이미 사용 중인 휴대번호
- `422`: 형식 검증 실패

## 6. 청약정보 API

정렬 허용값:

- `created_desc`
- `end_date_asc`
- `area_desc`, `area_asc`
- `recruitment_desc`, `recruitment_asc`
- `deposit_desc`, `deposit_asc`
- `rent_desc`, `rent_asc`

허용되지 않은 정렬값은 `400`이다.

### 6.1 전체 조회

`GET /listings/getall?sort=end_date_asc`

`sort`는 선택값이며 기본값은 `end_date_asc`이다. `data`로 `ListingPublic[]`을 반환한다.

### 6.2 페이지 조회

`GET /listings/page?page=1&page_size=10&sort=created_desc`

| Query | 타입 | 필수 | 기본값·범위 |
| --- | --- | --- | --- |
| `page` | integer | N | 기본 1, 최소 1 |
| `page_size` | integer | N | 기본 10, 1~100 |
| `sort` | string | N | 허용 정렬값 |

```json
{
  "success": true,
  "message": "청약정보 목록을 조회했습니다.",
  "data": {
    "items": [],
    "page": 1,
    "page_size": 10,
    "total_count": 0,
    "total_pages": 1
  }
}
```

조회 결과가 없어도 현재 구현은 `total_pages`를 최소 `1`로 반환한다. 종료된 공고는 선택한 정렬 조건과 별개로 목록 뒤쪽에 배치된다.

### 6.3 조건검색

`GET /listings/search?location=강남구&max_deposit=50000000&max_monthly_rent=400000&sort=deposit_asc`

| Query | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `location` | string | N | 지역 문자열 |
| `max_deposit` | integer | N | 0 이상 |
| `max_monthly_rent` | integer | N | 0 이상 |
| `sort` | string | N | 허용 정렬값 |

### 6.4 상세 조회

`GET /listings/get/{listing_id}`

- 성공: `ListingPublic` 객체
- `404`: `청약정보 ID {listing_id}를 찾을 수 없습니다.`

## 7. 즐겨찾기 API

### 7.1 즐겨찾기 등록

`POST /favorites/create`

```json
{
  "user_id": "user-uuid",
  "listing_id": 1
}
```

- 성공: 즐겨찾기 ID, 사용자 ID, 공고 ID, 생성 시각
- `409`: 이미 즐겨찾기한 청약정보
- `500`: 등록 실패

### 7.2 사용자 즐겨찾기 조회

`GET /favorites/mypage/{user_id}`

즐겨찾기 정보와 연결된 청약정보 목록을 반환한다. 결과가 없으면 빈 배열이다.

### 7.3 즐겨찾기 삭제

`DELETE /favorites/delete/{user_id}/{listing_id}`

- `404`: 즐겨찾기 없음
- `500`: 삭제 실패

## 8. 로그 API

### 8.1 최근 요청 로그 조회

`GET /logs?level=warning&limit=50`

| Query | 타입 | 필수 | 기본값·범위 |
| --- | --- | --- | --- |
| `level` | string | N | `info`, `warning`, `error` |
| `limit` | integer | N | 기본 50, 1~200 |

응답 항목: `time`, `level`, `screen`, `message`, `latency_ms`.

### 8.2 저장 로그 이력 조회

`GET /logs/history?level=all&limit=50`

warning/error로 Supabase에 저장된 이력을 조회한다. 응답 항목에 `id`, `created_at`이 포함된다.

## 9. 위치·생활권 API

### 9.1 주소 좌표 변환

`GET /locations/geocode?address=서울특별시 중구 세종대로 110`

| Query | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `address` | string | Y | 2~255자 |

```json
{
  "success": true,
  "message": "주소를 좌표로 변환했습니다.",
  "data": {
    "address": "서울 중구 세종대로 110",
    "latitude": 37.56637,
    "longitude": 126.97792,
    "matched_by": "address"
  }
}
```

- `404`: 주소·장소 검색 결과 없음
- `500`: Kakao API 키·설정 오류
- `502`: 외부 API 연결·응답 오류
- `504`: 응답 시간 초과

### 9.2 주변 지하철역 조회

`GET /locations/nearby-subways?latitude=37.56637&longitude=126.97792&radius_m=2000&limit=3`

### 9.3 주변 생활시설 조회

`GET /locations/nearby-facilities?latitude=37.56637&longitude=126.97792&radius_m=2000&limit=3`

공통 파라미터:

| Query | 타입 | 필수 | 기본값·범위 |
| --- | --- | --- | --- |
| `latitude` | number | Y | -90~90 |
| `longitude` | number | Y | -180~180 |
| `radius_m` | integer | N | 기본 2,000, 100~20,000m |
| `limit` | integer | N | 기본 3, 1~15 |

지하철 응답 항목은 이름, 주소, 좌표, 거리, 예상 도보 시간이다. 생활시설은 `subways`, `marts`, `hospitals`로 구분하며 각 항목에 `category`가 추가된다.

## 10. AI 상담 API

최종 프로젝트 설정의 AI 모델은 `gemini-3.5-flash`이다. 아래 응답의 `model` 값은 서버의 실제 `GEMINI_MODEL` 설정에 따라 반환된다.

### 10.1 상태 확인

`GET /chat/health`

```json
{
  "success": true,
  "message": "AI 상담 테스트 API가 실행 중입니다.",
  "data": {"summary_storage": "preview"}
}
```

인증 없이 AI 상담 API 실행 상태와 요약 저장 모드를 확인한다.

### 10.2 상담 사용자 조회

`GET /chat/me`

Bearer 인증이 필요하다.

```json
{
  "success": true,
  "message": "상담 사용자 정보를 조회했습니다.",
  "data": {
    "user_id": "user-uuid",
    "nickname": "홍길동",
    "email": "user@example.com"
  }
}
```

### 10.3 상담 메시지 전송

`POST /chat/message`

Bearer 인증이 필요하다.

```json
{
  "question": "공공임대 청약을 준비할 때 무엇을 확인해야 하나요?"
}
```

요청 모델에는 하위 호환용 `messages` 배열이 있지만, 현재 라우터는 인증된 사용자의 Redis 기록을 문맥 기준으로 사용한다.

```json
{
  "success": true,
  "message": "AI 상담 답변을 생성했습니다.",
  "data": {
    "answer": "먼저 공식 모집공고의 신청 자격과 일정을 확인하세요.",
    "model": "gemini-3.5-flash",
    "history_count": 0
  }
}
```

| 상태 | 발생 조건 |
| --- | --- |
| 401 | 토큰 누락·만료 |
| 422 | 질문 공백, 1,000자 초과 |
| 502 | Gemini 생성 실패·빈 응답 |
| 503 | Redis 기록 저장소 연결 실패 |

### 10.4 진행 중 상담 조회

`GET /chat/history`

```json
{
  "success": true,
  "message": "진행 중인 상담을 조회했습니다.",
  "data": [
    {"role": "user", "content": "질문"},
    {"role": "assistant", "content": "답변"}
  ]
}
```

사용자별 Redis 키의 진행 중 대화를 반환한다. 기록이 없으면 빈 배열이다.

### 10.5 진행 중 상담 종료

`DELETE /chat/history`

인증된 사용자의 Redis 대화 기록을 삭제한다. 성공 시 `data`는 `null`이다.

### 10.6 상담 요약 저장

`POST /chat/save`

```json
{}
```

요청의 `messages` 필드는 호환용이며 실제로는 Redis의 전체 상담 기록을 요약한다. 최소 질문·답변 한 쌍인 2개 메시지가 필요하다.

```json
{
  "success": true,
  "message": "상담 요약 미리보기를 저장했습니다.",
  "data": {
    "id": "11111111-1111-1111-1111-111111111111",
    "user_id": "user-uuid",
    "title": "공공임대 청약 준비 상담",
    "summary": "상담 주제:\n- 공공임대 청약 준비",
    "message_count": 2,
    "model": "gemini-3.5-flash",
    "created_at": "2026-08-12T00:00:00Z"
  }
}
```

- `400`: 저장할 상담 내용 없음
- `500`: Supabase 요약 저장·조회 실패
- `502`: Gemini 요약 생성 실패
- `503`: Redis 연결 실패

진행 중인 상담은 사용자별로 Upstash Redis에 저장되며 마지막 저장 시점부터 1시간 후 자동 만료된다. 사용자가 저장을 요청하면 Redis의 전체 대화를 Gemini가 제목과 요약으로 변환하고, 결과를 Supabase의 `chat_summaries` 테이블에 저장한다. 저장 성공 후 진행 중인 Redis 기록은 삭제한다.

### 10.7 저장된 상담 조회

`GET /chat/summaries`

인증된 사용자의 요약 목록을 최신순으로 반환한다.

### 10.8 저장된 상담 삭제

`DELETE /chat/summaries/{summary_id}`

| Path | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `summary_id` | UUID | Y | 삭제할 상담 요약 ID |

사용자 ID와 요약 ID를 함께 조건으로 사용한다.

- `404`: 현재 사용자가 소유한 요약 없음
- `422`: UUID 형식 오류
- `500`: Supabase 삭제 실패

## 11. AI 안내원 API

AI 안내원은 AI 상담과 별도 세션을 사용하며 서버의 Redis·Supabase에 대화를 저장하지 않는다. 프런트엔드의 현재 Streamlit 세션에만 메시지가 유지된다.

### 11.1 상태 확인

`GET /ai-guide/health`

```json
{
  "success": true,
  "message": "AI 안내원 테스트 API가 실행 중입니다.",
  "data": {"storage": "session-only"}
}
```

### 11.2 안내원 사용자 조회

`GET /ai-guide/me`

Bearer 인증이 필요하며 사용자 ID, 닉네임, 이메일을 반환한다.

### 11.3 안내원 메시지 전송

`POST /ai-guide/message`

```json
{
  "question": "청약 공고는 어떻게 검색하나요?",
  "messages": []
}
```

| 필드 | 타입 | 필수 | 제약 |
| --- | --- | --- | --- |
| `question` | string | Y | 공백 불가, 최대 500자 |
| `messages` | GuideMessage[] | N | 최대 30개 |
| `messages[].role` | string | Y | `user` 또는 `assistant` |
| `messages[].content` | string | Y | 공백 불가, 최대 3,000자 |

```json
{
  "success": true,
  "message": "AI 안내원 답변을 생성했습니다.",
  "data": {
    "category": "LISTING_SEARCH",
    "response_type": "guide",
    "title": "청약 공고 조건검색 방법",
    "steps": [
      "화면 왼쪽 메뉴에서 ‘청약정보 조회’를 선택합니다.",
      "‘조건검색’ 영역을 펼칩니다.",
      "서울 자치구, 최대 보증금, 최대 월세를 입력합니다.",
      "‘검색’ 버튼을 누릅니다."
    ],
    "answer": null,
    "notice": null,
    "model": "gemini-3.5-flash",
    "history_count": 0
  }
}
```

응답 유형:

| `response_type` | 설명 |
| --- | --- |
| `guide` | 코드에 정의된 사이트 이용 단계 |
| `answer` | 간단한 청약 용어·계산 답변 |
| `refusal` | 공고 추천·자격·당첨 가능성 등 범위 밖 질문 거절 |
| `clarification` | 낮은 분류 신뢰도로 재질문 요청 |

- `401`: 토큰 누락·만료
- `422`: 질문·메시지 검증 실패
- `502`: Gemini 질문 분석 실패

## 12. 공통 데이터 모델

### 12.1 `ListingCreate`

| 필드 | 타입 | 필수 | 제약·설명 |
| --- | --- | --- | --- |
| `title` | string | Y | 1~255자 |
| `housing_name` | string | Y | 1~255자 |
| `area_sqm` | decimal | Y | 0보다 큼 |
| `recruitment_count` | integer | Y | 0보다 큼 |
| `location` | string | Y | 1~50자 |
| `detail_address` | string · null | N | 최대 255자 |
| `deposit` | integer | Y | 0 이상 |
| `monthly_rent` | integer | Y | 0 이상 |
| `application_start_date` | date | Y | ISO 날짜 |
| `application_end_date` | date | Y | ISO 날짜 |
| `description` | string | Y | 공백 불가 |
| `image_url` | string · null | N | 대표 이미지 |
| `image_urls` | string[] | N | 전체 이미지, 기본 빈 배열 |
| `source_url` | string | Y | 원문 URL |

### 12.2 `ListingPublic`

`ListingCreate`의 표시 필드에 `id`, `images`, `created_at`이 추가된다. 응답에서는 전체 이미지 목록을 `images`로 반환한다.

### 12.3 `ChatMessage`

| 필드 | 타입 | 제약 |
| --- | --- | --- |
| `role` | `user` · `assistant` | 필수 |
| `content` | string | 공백 불가, 최대 4,000자 |

### 12.4 `ChatSummaryItem`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 요약 식별자 |
| `user_id` | string | 소유 사용자 |
| `title` | string | 상담 제목 |
| `summary` | string | 구조화된 요약 |
| `message_count` | integer | 요약한 메시지 수 |
| `model` | string | 생성 모델 |
| `created_at` | datetime | 생성 시각 |

### 12.5 `GuideAnswer`

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `category` | GuideCategory | 질문 분류 |
| `response_type` | string | `guide`, `answer`, `refusal`, `clarification` |
| `title` | string | 응답 제목 |
| `steps` | string[] | 이용 단계 |
| `answer` | string · null | 짧은 답변·거절·재질문 |
| `notice` | string · null | 공식 자료 확인 안내 |
| `model` | string | 분류 모델 |
| `history_count` | integer | 사용한 이전 메시지 수 |

---