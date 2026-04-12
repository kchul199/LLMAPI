# [기능정의서] LLMAPI Client 테스트/이력 조회 Web UI (v0.1)

작성일: 2026-04-12  
대상 시스템: `client_gateway`  
문서 목적: Web UI의 기능 단위를 구현 가능한 수준으로 정의하고, 수용 기준을 명확히 한다.
정책: 본 UI는 로그인 페이지 및 로그인 기능을 제공하지 않는다.

---

## 1. 문서 적용 범위

본 기능정의서는 아래 UI 기능을 대상으로 한다.

- 대시보드
- 분석 테스트(동기/비동기)
- 요청 이력 조회
- 요청 상세 조회

---

## 2. 기능 목록 (UI-FR)

| ID | 기능명 | 설명 | 우선순위 |
| :--- | :--- | :--- | :--- |
| UI-FR-001 | 공통 레이아웃 | 헤더/네비게이션/콘텐츠 레이아웃 제공 | Must |
| UI-FR-002 | 대시보드 요약 | Health/요청 현황/실패 현황 표시 | Should |
| UI-FR-003 | 동기 테스트 실행 | 폼 입력 후 `/client/v1/analyze` 호출 | Must |
| UI-FR-004 | 비동기 테스트 등록 | `/client/v1/analyze/async` 호출 | Must |
| UI-FR-005 | 비동기 상태 폴링 | job_id 기반 상태 자동 조회 | Must |
| UI-FR-006 | 요청 JSON 편집기 | 테스트 입력 JSON 자동 생성/수정 | Must |
| UI-FR-007 | 입력값 검증 | 필수값, tasks 선택 검증 | Must |
| UI-FR-008 | 요청 이력 검색 | 상태/기간/source_system 필터 조회 | Must |
| UI-FR-009 | 요청 목록 페이지네이션 | page/size 기반 목록 이동 | Must |
| UI-FR-010 | 요청 상세 조회 | request/result/status_history 표시 | Must |
| UI-FR-011 | 상태 타임라인 렌더링 | 상태 전이 순서 시각화 | Should |
| UI-FR-012 | 재테스트 프리필 | 상세 -> 테스트 화면 데이터 전달 | Should |
| UI-FR-013 | 오류 메시지 표준 노출 | error_code/error_message 강조 | Must |
| UI-FR-014 | 결과 JSON 복사 | 응답 JSON 복사 버튼 제공 | Should |
| UI-FR-015 | 로딩/빈/오류 상태 UI | 사용자 이해 가능한 상태 안내 | Must |
| UI-FR-016 | 무인증 접근 | 로그인 없이 화면 진입 및 기능 사용 가능 | Must |
| UI-FR-017 | 시간대 변환 표시 | 화면 시간 `Asia/Seoul` 기준 표시 | Should |
| UI-FR-018 | 접근성 기본 준수 | 라벨/포커스/키보드 접근 가능 | Should |

---

## 3. 상세 기능 정의

## 3.1 공통 UI

### UI-FR-001 공통 레이아웃
- 입력:
  - 없음
- 처리:
  - 좌측 또는 상단 네비게이션에서 `대시보드/테스트/이력` 이동
- 출력:
  - 모든 화면에서 동일한 브랜딩/메뉴/페이지 타이틀 표시
- 수용 기준:
  1. 모든 페이지에서 네비게이션이 동일하게 렌더링된다.
  2. 현재 메뉴가 활성 상태로 강조된다.

### UI-FR-015 로딩/빈/오류 상태 UI
- 수용 기준:
  1. API 요청 중 로딩 표시(버튼 disable + spinner).
  2. 결과 없음 시 빈 상태 문구 표시.
  3. API 오류 시 재시도 버튼과 오류코드 표시.

---

## 3.2 분석 테스트 화면

### UI-FR-003 동기 테스트 실행
- API: `POST /client/v1/analyze`
- 요청 필드:
  - `source_system`, `client_request_id`, `text`, `tasks`, `target_speakers`, `options.prompt_version`
- 수용 기준:
  1. 실행 후 HTTP 상태 코드와 응답 본문이 표시된다.
  2. 성공 시 `request_uid`, `trace_id`, `status=COMPLETED`를 확인할 수 있다.

### UI-FR-004 비동기 테스트 등록
- API: `POST /client/v1/analyze/async`
- 수용 기준:
  1. 성공 시 `job_id`가 표시된다.
  2. `idempotent_replay` 값이 UI에 표시된다.

### UI-FR-005 비동기 상태 폴링
- API: `GET /client/v1/analyze/async/{job_id}`
- 동작:
  - 2초 간격 폴링
  - 종결 상태(`COMPLETED`, `FAILED`, `TIMEOUT`)에서 중지
- 수용 기준:
  1. 상태 변경 시 UI 배지가 즉시 갱신된다.
  2. 종결 상태 시 최종 결과 또는 오류를 표시한다.

### UI-FR-006 요청 JSON 편집기
- 수용 기준:
  1. 폼 입력값이 JSON preview에 실시간 반영된다.
  2. `JSON 예시 채우기` 클릭 시 샘플 데이터가 자동 입력된다.

### UI-FR-007 입력값 검증
- 검증 규칙:
  - `source_system`: 1~64자
  - `client_request_id`: 1~100자
  - `text`: 1자 이상
  - `tasks`: 최소 1개 선택
- 수용 기준:
  1. 검증 실패 시 API 호출이 차단된다.
  2. 오류 필드 하단에 안내 문구가 표시된다.

### UI-FR-013 오류 메시지 표준 노출
- 수용 기준:
  1. `error_code`, `error_message`를 분리 표시한다.
  2. 409(`DUPLICATE_CLIENT_REQUEST_ID`)는 별도 안내 문구를 표시한다.

### UI-FR-014 결과 JSON 복사
- 수용 기준:
  1. 복사 버튼 클릭 시 클립보드에 전체 JSON이 복사된다.
  2. 성공/실패 토스트 메시지가 표시된다.

### UI-FR-016 무인증 접근
- 수용 기준:
  1. `/ui`, `/ui/test`, `/ui/history` 접근 시 로그인 화면으로 리다이렉트되지 않는다.
  2. 사용자 계정 입력 없이 테스트/이력 기능을 바로 사용할 수 있다.

---

## 3.3 요청 이력 화면

### UI-FR-008 요청 이력 검색
- API: `GET /client/v1/requests`
- 쿼리:
  - `source_system`, `status`, `from`, `to`, `page`, `size`
- 수용 기준:
  1. 검색 버튼 클릭 시 조건에 맞는 결과만 표시된다.
  2. `status` 필터는 API Enum 값과 동일하게 동작한다.

### UI-FR-009 페이지네이션
- 수용 기준:
  1. `이전/다음` 이동 시 목록이 갱신된다.
  2. 현재 페이지, 총 건수가 표시된다.

---

## 3.4 요청 상세 화면

### UI-FR-010 요청 상세 조회
- API: `GET /client/v1/requests/{request_uid}`
- 수용 기준:
  1. request/result/status_history 섹션이 모두 렌더링된다.
  2. `request_uid` 미존재 시 404 안내 페이지를 표시한다.

### UI-FR-011 상태 타임라인 렌더링
- 수용 기준:
  1. `status_history`를 시간순으로 보여준다.
  2. `reason_code`가 있으면 강조 표시한다.

### UI-FR-012 재테스트 프리필
- 수용 기준:
  1. 상세에서 `재테스트` 클릭 시 `/ui/test`로 이동한다.
  2. 기존 요청 필드가 테스트 폼에 자동 채워진다.

---

## 4. 비기능 요구사항 (UI-NFR)

| ID | 항목 | 기준 |
| :--- | :--- | :--- |
| UI-NFR-001 | 응답성 | 첫 화면 렌더 2초 이내(내부망 기준) |
| UI-NFR-002 | 호환성 | 최신 Chrome/Edge/Safari 지원 |
| UI-NFR-003 | 가용성 | API 장애 시 UI가 명확한 오류 상태 제공 |
| UI-NFR-004 | 접근성 | 기본 키보드 탐색/라벨 연결 제공 |
| UI-NFR-005 | 보안 | 민감정보 localStorage 저장 금지 |
| UI-NFR-006 | 관측성 | UI 요청 로그에 trace_id/request_uid 연계 가능 |
| UI-NFR-007 | 유지보수성 | 화면별 JS 모듈 분리 |
| UI-NFR-008 | 국제화 준비 | 문자열 리소스 분리 구조 고려 |

---

## 5. 상태값/오류코드 매핑

### 5.1 상태값 표시 규칙

| 상태 | 라벨 | 색상 |
| :--- | :--- | :--- |
| RECEIVED | 접수 | 회색 |
| QUEUED | 대기 | 파랑 |
| PROCESSING | 처리중 | 주황 |
| COMPLETED | 완료 | 초록 |
| FAILED | 실패 | 빨강 |
| TIMEOUT | 시간초과 | 진빨강 |

### 5.2 주요 오류코드 표시 문구

| 오류코드 | UI 문구 |
| :--- | :--- |
| VALIDATION_ERROR | 입력값을 확인해 주세요. |
| DUPLICATE_CLIENT_REQUEST_ID | 동일 요청 ID가 이미 존재합니다. |
| UPSTREAM_UNAVAILABLE | LLMAPI 연결에 실패했습니다. |
| UPSTREAM_TIMEOUT | 분석 처리 시간이 초과되었습니다. |
| QUEUE_UNAVAILABLE | 비동기 큐를 사용할 수 없습니다. |
| INTERNAL_ERROR | 내부 오류가 발생했습니다. 관리자에게 문의하세요. |

---

## 6. 이벤트 및 로그 정의

- `ui_test_sync_submit`
- `ui_test_async_submit`
- `ui_test_async_poll`
- `ui_history_search`
- `ui_history_detail_open`
- `ui_copy_json`

로그 공통 필드:
- `event_name`
- `trace_id`
- `request_uid` (존재 시)
- `source_system`
- `client_ip`
- `timestamp`

---

## 7. 수용 테스트 시나리오

1. 정상 동기 요청 후 결과 표시 확인
2. 비동기 요청 등록 후 완료까지 폴링 확인
3. 409 중복 요청 시 사용자 안내 문구 확인
4. 상태 필터 `FAILED` 조회 시 실패 건만 노출
5. 상세 화면 타임라인과 DB 상태이력 정합성 확인
6. 로그인 절차 없이 주요 화면 접근 가능 확인

---

## 8. 릴리스 기준 (Definition of Done)

1. Must 기능(UI-FR) 100% 구현
2. 핵심 시나리오 수동 테스트 통과
3. 최소 자동 테스트(폼 검증/이력 조회) 통과
4. 운영 가이드(실행/문제해결) 문서 링크 완료
