# [화면기획서] LLMAPI Client 테스트/이력 조회 Web UI (v0.1)

작성일: 2026-04-12  
대상 시스템: `client_gateway`  
문서 목적: 운영자/개발자가 웹페이지에서 LLMAPI 연동 테스트를 수행하고, 요청 이력 및 상세 결과를 조회할 수 있도록 화면 구조와 UX를 정의한다.
정책: 본 UI는 로그인 페이지 및 로그인 기능을 제공하지 않는다.

---

## 1. 기획 배경

현재 Client 서버 API는 `curl` 또는 API 도구(Postman)로만 확인 가능하다.  
운영자와 초급 개발자가 빠르게 테스트하고 장애 원인을 파악할 수 있도록 브라우저 기반 관리 화면이 필요하다.

---

## 2. 사용자 정의

- 운영자(Operator)
- API 연동 개발자(Developer)
- QA 담당자(QA)

공통 목표:
- 동기/비동기 분석을 브라우저에서 즉시 테스트
- 요청 이력 검색 및 상태 추적
- 실패 원인 확인 및 재현 가능성 확보

---

## 3. 화면 IA (Information Architecture)

1. 대시보드 `/ui`
2. 분석 테스트 `/ui/test`
3. 요청 이력 `/ui/history`
4. 요청 상세 `/ui/history/{request_uid}`

---

## 4. 사용자 플로우

### 4.1 동기 테스트 플로우

1. `분석 테스트` 화면 진입
2. `source_system`, `client_request_id`, `text`, `tasks` 입력
3. `동기 요청 실행` 클릭
4. 응답(JSON + 요약 카드) 즉시 확인
5. 필요 시 `이력으로 이동` 클릭

### 4.2 비동기 테스트 플로우

1. 테스트 폼 입력
2. `비동기 요청 등록` 클릭
3. `job_id` 수신 후 폴링 조회 시작
4. 상태(`QUEUED/PROCESSING/COMPLETED/FAILED`) 표시
5. 완료 시 결과 자동 표시

### 4.3 이력 조회 플로우

1. `요청 이력` 화면 진입
2. 필터(기간/상태/source_system) 입력
3. 목록 확인 후 특정 row 클릭
4. 상세 화면에서 요청 본문, 상태 전이, 결과/오류 확인

---

## 5. 화면별 상세 정의

## 5.1 대시보드 화면 (`/ui`)

### 목적
- 현재 시스템 상태를 한눈에 확인
- 테스트/이력 화면으로 빠른 이동

### 주요 컴포넌트
- 상단 요약 카드
  - API Health 상태
  - 오늘 요청 건수
  - 실패 건수
  - 평균 응답시간(선택)
- 빠른 실행 버튼
  - `동기 테스트 바로가기`
  - `비동기 테스트 바로가기`
  - `요청 이력 보기`
- 최근 실패 요청 5건 미니 테이블

### 빈 상태/오류 상태
- 데이터 없음: "표시할 요청 이력이 없습니다"
- Health 실패: 빨간 배지 + "연결 상태를 확인하세요"

---

## 5.2 분석 테스트 화면 (`/ui/test`)

### 목적
- 브라우저에서 즉시 API 호출 검증

### 레이아웃
- 좌측: 요청 입력 폼
- 우측: 응답/로그 패널

### 요청 입력 폼 필드
- `source_system` (text)
- `client_request_id` (text)
- `text` (textarea)
- `tasks` (checkbox: summary/sentiment/category)
- `target_speakers` (radio: agent/customer/both)
- `prompt_version` (text, 기본 `v1.1`)
- `mode` (sync/async)

### 버튼
- `동기 요청 실행`
- `비동기 요청 등록`
- `폼 초기화`
- `JSON 예시 채우기`

### 응답 영역
- HTTP 상태 코드 배지
- `request_uid`, `trace_id`, `job_id`
- 결과 JSON 뷰어
- 에러코드/메시지 강조 박스
- 복사 버튼 (`Copy JSON`)

### 입력 검증 UX
- 필수값 누락 시 필드 하단 즉시 안내
- `tasks` 미선택 시 제출 차단

---

## 5.3 요청 이력 화면 (`/ui/history`)

### 목적
- 저장된 요청을 검색/탐색

### 필터 영역
- `source_system`
- `status` (RECEIVED, QUEUED, PROCESSING, COMPLETED, FAILED, TIMEOUT)
- `from`, `to` (datetime)
- `page`, `size`

### 결과 테이블 컬럼
- 요청시간
- request_uid
- source_system
- client_request_id
- status 배지
- mode(sync/async)
- trace_id
- 액션(상세)

### 테이블 기능
- 상태별 배지 색상
- 정렬(요청시간 desc 기본)
- 페이지네이션
- CSV 다운로드(후속)

### 빈 상태/오류 상태
- 결과 없음: "조건에 맞는 요청이 없습니다"
- 조회 실패: 재시도 버튼 표시

---

## 5.4 요청 상세 화면 (`/ui/history/{request_uid}`)

### 목적
- 단일 요청의 전체 처리 이력 분석

### 섹션 구성
1. 기본 정보 카드
- request_uid, source_system, client_request_id, trace_id, mode, status

2. 요청 페이로드
- text(마스킹), tasks, target_speakers, prompt_version

3. 상태 전이 타임라인
- prev_status -> new_status
- changed_at, reason_code, reason_message, actor

4. 결과/오류 정보
- `result_json` Pretty View
- usage(total_tokens, latency_ms)
- error_code/error_message

### 사용자 액션
- `목록으로`
- `동일 조건으로 재테스트` (test 화면 이동 + 파라미터 프리필)

---

## 6. 화면 공통 정책

- 시간 표시는 `Asia/Seoul` 기준
- UUID/Trace ID는 monospace 폰트로 표시
- 긴 JSON은 접기/펼치기 제공
- 네트워크 지연 시 로딩 스켈레톤 표시
- 모든 API 오류는 사용자 친화 문구 + 원본 코드 동시 표시

---

## 7. 반응형 기준

- Desktop: 1280px 이상
- Tablet: 768~1279px
- Mobile: 767px 이하

모바일에서는:
- 테스트 화면 2단 레이아웃을 1단으로 전환
- 이력 테이블을 카드 리스트로 전환

---

## 8. MVP 범위

1. `/ui/test` (동기/비동기 요청)
2. `/ui/history` (필터/목록)
3. `/ui/history/{request_uid}` (상세)
4. `/ui` (간단 대시보드)

---

## 9. 오픈 이슈

1. 내부망 접근제어를 인프라 레벨(IP 제한)로 고정할지 여부
2. CSV 다운로드를 MVP에 포함할지 여부
3. 실패 재처리 버튼을 UI에 즉시 노출할지 여부
