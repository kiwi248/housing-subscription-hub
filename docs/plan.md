# 공공임대 청약 통합 안내 서비스 계획서

> 현재 코드와 디렉터리 구조를 기준으로 작성한 완성본 기록 문서다.
> 앞으로 할 작업, 새 기능 제안, 리팩터링 항목, 자잘한 오류 목록은 포함하지 않는다.

## 1. 프로젝트 개요

공공임대·분양 청약 공고를 등록하고 조회하며, 사용자별 즐겨찾기와 프로필, 주변 생활권 분석, AI 상담·안내 기능을 제공하는 서비스다.

- `BE`: FastAPI 기반 REST API
- `FE_User`: 일반 사용자용 Streamlit 앱
- `FE_Admin`: 관리자용 Streamlit 앱
- `Supabase`: PostgreSQL, 사용자 인증, 공고 이미지 Storage
- `Redis`: 진행 중인 AI 상담 이력
- `Gemini`: AI 상담 답변·요약 및 AI 안내원 답변
- `Kakao Local API`: 주소 좌표 변환과 주변 시설 검색

## 2. 디렉터리 및 파일 구조

```text
aio-01-p1-team1/
├─ plan.md                         현재 프로젝트 구현 기록
├─ README.md                       프로젝트 실행 안내
├─ docs/
│  └─ plan.md                      기존 상세 기획 문서
├─ BE/
│  ├─ app/
│  │  ├─ main.py                   FastAPI 앱, CORS, 요청 로그, 라우터 등록
│  │  ├─ routers/                  HTTP 요청과 응답 처리
│  │  ├─ services/                 도메인별 데이터·외부 API 처리
│  │  ├─ schemas/                  Pydantic 요청·응답 모델
│  │  ├─ core/                     인증, 설정, 공통 응답, 로그 저장
│  │  └─ exceptions/               공통 예외 응답 처리
│  ├─ sql/                         Supabase 테이블·컬럼·인덱스 SQL
│  ├─ scripts/                     관리자 생성, 벤치마크, 부하 확인
│  └─ tests/                       백엔드 단위·라우터 테스트
├─ FE_User/
│  ├─ app.py                       사용자 앱 진입점과 메뉴 구성
│  ├─ app_pages/                   사용자 화면
│  ├─ clients/                     백엔드 API 기능별 호출
│  ├─ core/                        인증, 세션 복원, UI·목록 공통 로직
│  └─ tests/                       사용자 화면 공통 로직 테스트
└─ FE_Admin/
   ├─ app.py                       관리자 앱 진입점과 메뉴 구성
   ├─ app_pages/                   관리자 화면
   ├─ clients/                     백엔드 API 기능별 호출
   ├─ core/                        인증 상태, UI·공고 관리 공통 로직
   └─ tests/                       관리자 화면 공통 로직 테스트
```

## 3. 전체 호출 흐름

```text
사용자/관리자
  → Streamlit app.py 및 app_pages
  → 기능별 clients
  → FastAPI main.py
  → routers
  → schemas 검증
  → services
  → Supabase / Redis / Gemini / Kakao API
  → ApiResponse { success, message, data }
  → Streamlit 화면 표시
```

- 일반 사용자 회원가입·로그인·비밀번호 변경은 `FE_User`가 Supabase Auth를 직접 호출한다.
- 로그인 토큰은 브라우저 Session Storage에 저장하고 새로고침 시 세션을 복원한다.
- AI 상담 API는 Bearer 토큰을 검증해 현재 사용자를 식별한다.
- 관리자 로그인은 백엔드의 `admins` 테이블과 해시 비밀번호를 사용한다.
- 백엔드 요청 로그는 메모리에 최근 기록을 보관하고 warning/error 기록은 Supabase에도 저장한다.

## 4. 구현된 사용자 기능

- [x] 이메일 회원가입 및 로그인
- [x] Session Storage 기반 로그인 세션 복원과 로그아웃
- [x] 청약 공고 전체 조회, 조건 검색, 정렬, 페이지 이동
- [x] 자치구·최대 보증금·최대 월세 기준 검색
- [x] 공고 카드의 면적, 모집 인원, 금액, 신청 기간, 이미지 표시
- [x] 신청 마감 상태와 D-day 표시
- [x] 즐겨찾기 등록, 목록 조회, 삭제
- [x] 즐겨찾기 공고 위치 지도 표시
- [x] 프로필 조회·수정과 비밀번호 변경
- [x] 공고 주소 기준 좌표 변환
- [x] 반경별 주변 지하철역·마트·병원 조회와 지도 표시
- [x] AI 상담 질문·답변, 진행 이력 조회·종료
- [x] AI 상담 요약 저장·조회·삭제
- [x] 사이트 이용 방법과 청약 용어를 설명하는 AI 안내원

## 5. 구현된 관리자 기능

- [x] 관리자 로그인과 Session Storage 기반 화면 상태 복원
- [x] 청약 공고 등록
- [x] 청약 공고 전체·조건 검색, 정렬, 페이지 이동
- [x] 공고 상세 수정과 삭제
- [x] 단일·다중 이미지 업로드, 교체, 개별 삭제
- [x] 여러 공고 선택 후 일괄 삭제
- [x] 즐겨찾기 순위 조회
- [x] 공고별·사용자별 즐겨찾기 상세 조회
- [x] 최근 요청 로그 대시보드와 5초 주기 갱신
- [x] warning/error 로그 이력 조회

## 6. 구현된 Backend API

모든 주요 응답은 `ApiResponse`의 `success`, `message`, `data` 구조를 사용한다.

| 영역 | Method | Path | 역할 |
|---|---|---|---|
| 관리자 | POST | `/admin/login` | 관리자 로그인 |
| 관리자 | POST | `/admin/listings/create` | 공고 등록 |
| 관리자 | POST | `/admin/listings/images` | 이미지 1개 업로드 |
| 관리자 | POST | `/admin/listings/images/bulk` | 이미지 여러 개 업로드 |
| 관리자 | PUT | `/admin/listings/update/{listing_id}` | 공고 내용과 이미지 수정 |
| 관리자 | DELETE | `/admin/listings/{listing_id}/image` | 대표 이미지 삭제 |
| 관리자 | PUT | `/admin/listings/{listing_id}/images` | 공고 이미지 목록 교체 |
| 관리자 | DELETE | `/admin/listings/delete/{listing_id}` | 공고 삭제 |
| 관리자 | GET | `/admin/favorites/ranking` | 즐겨찾기 순위 조회 |
| 관리자 | GET | `/admin/favorites/detail` | 즐겨찾기 상세 조회 |
| 공고 | GET | `/listings/getall` | 전체 공고 조회 |
| 공고 | GET | `/listings/page` | 페이지 단위 공고 조회 |
| 공고 | GET | `/listings/search` | 조건 검색 |
| 공고 | GET | `/listings/get/{listing_id}` | 공고 단건 조회 |
| 즐겨찾기 | POST | `/favorites/create` | 즐겨찾기 등록 |
| 즐겨찾기 | GET | `/favorites/mypage/{user_id}` | 사용자 즐겨찾기 조회 |
| 즐겨찾기 | DELETE | `/favorites/delete/{user_id}/{listing_id}` | 즐겨찾기 삭제 |
| 프로필 | GET | `/profiles/{user_id}` | 프로필 조회 |
| 프로필 | PUT | `/profiles/{user_id}` | 프로필 수정 |
| 위치 | GET | `/locations/geocode` | 주소를 좌표로 변환 |
| 위치 | GET | `/locations/nearby-subways` | 주변 지하철역 조회 |
| 위치 | GET | `/locations/nearby-facilities` | 주변 지하철역·마트·병원 조회 |
| 로그 | GET | `/logs` | 최근 메모리 로그 조회 |
| 로그 | GET | `/logs/history` | 저장된 warning/error 로그 조회 |
| AI 상담 | GET | `/chat/health` | 상담 API 설정 상태 조회 |
| AI 상담 | GET | `/chat/me` | 인증 사용자 프로필 조회 |
| AI 상담 | POST | `/chat/message` | 상담 답변 생성 |
| AI 상담 | GET | `/chat/history` | 진행 중인 상담 조회 |
| AI 상담 | DELETE | `/chat/history` | 진행 중인 상담 종료 |
| AI 상담 | POST | `/chat/save` | 상담 요약 생성·저장 |
| AI 상담 | GET | `/chat/summaries` | 저장된 상담 요약 조회 |
| AI 상담 | DELETE | `/chat/summaries/{summary_id}` | 상담 요약 삭제 |
| AI 안내원 | GET | `/ai-guide/health` | 안내원 API 상태 조회 |
| AI 안내원 | GET | `/ai-guide/me` | 인증 사용자 프로필 조회 |
| AI 안내원 | POST | `/ai-guide/message` | 사이트 이용·용어 안내 답변 생성 |

## 7. 데이터 구조

| 저장소 | 주요 데이터 | 코드상 역할 |
|---|---|---|
| Supabase Auth | 사용자 계정과 세션 | 회원가입, 로그인, 토큰 검증, 비밀번호 변경 |
| `profiles` | 닉네임, 연락처, 생년월일, 관심분야 | 사용자 프로필 |
| `admins` | 관리자 아이디, 해시 비밀번호 | 관리자 로그인 |
| `listings` | 공고 기본 정보, 금액, 기간, 주소, 좌표 | 청약 공고 |
| `listing_images` | 공고별 다중 이미지와 표시 순서 | 이미지 갤러리 |
| `favorites` | 사용자와 공고 연결 | 즐겨찾기 |
| `logs` | warning/error 요청 기록 | 관리자 로그 이력 |
| `chat_summaries` | 사용자별 상담 제목·요약 | 상담 요약 영구 저장 모드 |
| Redis | 사용자별 진행 중 상담 메시지 | 상담 문맥, TTL, 최대 메시지 수 관리 |
| 프로세스 메모리 | 최근 요청 로그, preview 상담 요약 | 실행 중 임시 데이터 |

## 8. 완성된 작업 순서 기록

### 1단계: 공통 기반

- [x] FastAPI 라우터·서비스·스키마 분리
- [x] Streamlit 사용자/관리자 앱 분리
- [x] 공통 API 응답과 예외 처리
- [x] 환경변수 기반 Supabase, Redis, Gemini, Kakao, CORS 설정

### 2단계: 공고 및 이미지

- [x] 공고 등록·조회·검색·수정·삭제
- [x] 페이지네이션과 정렬
- [x] Supabase Storage 이미지 업로드·교체·삭제
- [x] 다중 이미지 갤러리

### 3단계: 사용자와 즐겨찾기

- [x] Supabase Auth 회원가입·로그인
- [x] 사용자 세션 복원
- [x] 프로필 관리
- [x] 즐겨찾기 사용자·관리자 화면

### 4단계: 위치와 지도

- [x] 공고 상세 주소와 좌표 저장 구조
- [x] Kakao 기반 지오코딩과 주변 시설 조회
- [x] PyDeck 기반 사용자 지도 화면

### 5단계: AI 기능

- [x] Redis 기반 상담 이력
- [x] Gemini 또는 mock 모드 상담 답변
- [x] 상담 요약 저장·조회·삭제
- [x] 세션 단위 AI 안내원

### 6단계: 운영 확인 기능

- [x] 요청 처리 시간과 상태 기반 로그 기록
- [x] 최근 로그 대시보드
- [x] warning/error 이력 저장·조회
- [x] Backend, FE_User, FE_Admin 자동 테스트 구성

## 9. 실행 방법

각 실행 영역은 자체 가상환경과 `requirements.txt`를 사용한다.

### Backend

```powershell
cd BE
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

- API 문서: `http://127.0.0.1:8000/docs`

### 사용자 화면

```powershell
cd FE_User
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### 관리자 화면

```powershell
cd FE_Admin
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## 11. 코드만으로 확정할 수 없는 실행값

- **확인 필요:** 실제 실행 환경이 AI `mock` 모드인지 Gemini 실연동 모드인지는 환경변수 값에 따라 결정된다.
- **확인 필요:** 상담 요약이 메모리 `preview` 모드인지 Supabase 저장 모드인지는 환경변수 값에 따라 결정된다.
- **확인 필요:** 현재 배포 주소와 외부 서비스의 실제 운영 데이터는 저장소 코드만으로 확정할 수 없다.

위 항목은 미완성 작업이 아니라 실행 환경별 설정값의 차이다.
