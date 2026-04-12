# [기능요건서] LLMAPI 연동 Client 서버 (v0.2)

작성일: 2026-04-12  
목적: Client 서버 개발 범위를 기능/비기능 요구사항으로 명확히 정의한다.

---

## 1. 용어 정의

- Client 서버: 업무 시스템과 LLMAPI 사이의 중계 서버
- 업무 시스템: Client 서버를 호출하는 내부/외부 서비스
- 멱등성: 동일 요청 중복 전송 시 중복 처리되지 않도록 보장하는 성질
- 상태 전이: 요청이 `RECEIVED -> QUEUED -> PROCESSING -> COMPLETED/FAILED/TIMEOUT`로 바뀌는 과정

---

## 2. 기능 요구사항 (FR)

| ID | 기능요건 | 우선순위 | 수용 기준 (Acceptance Criteria) |
| :--- | :--- | :--- | :--- |
| FR-001 | 동기 분석 API 제공 (`POST /client/analyze`) | Must | 유효 요청 수신 시 LLMAPI 동기 API 호출 후 표준 응답 반환 |
| FR-002 | 비동기 분석 등록 API 제공 (`POST /client/analyze/async`) | Must | 요청 접수 후 `job_id` 반환, DB 상태 `QUEUED` 저장 |
| FR-003 | 비동기 상태 조회 API (`GET /client/analyze/async/{job_id}`) | Must | `pending/processing/completed/failed/timeout` 상태 조회 가능 |
| FR-004 | 요청 스키마 검증 | Must | 필수값 누락/형식 오류 시 `422` 반환 |
| FR-005 | LLMAPI 요청 매핑 | Must | `request_id/text/tasks/target_speakers/options.prompt_version` 정확 전달 |
| FR-006 | prompt_version 전달 | Should | 요청 옵션에 버전이 있으면 LLMAPI로 전달 |
| FR-007 | 재시도 정책 적용 | Must | 네트워크 일시 오류 시 설정 기반 재시도 수행 |
| FR-008 | 타임아웃 정책 적용 | Must | timeout 발생 시 표준 오류코드로 실패 처리 |
| FR-009 | 에러 표준화 | Must | LLMAPI/내부 오류를 사내 표준 오류코드로 변환 |
| FR-010 | Trace ID 전파 | Must | 요청 시작부터 DB/로그/응답까지 동일 trace_id 사용 |
| FR-011 | Health API 제공 (`GET /client/health`) | Must | DB, Redis, LLMAPI 연결 상태 반환 |
| FR-012 | 요청 이력 저장 | Must | 수신 즉시 `client_analysis_request`에 저장 |
| FR-013 | 결과 저장 | Must | 완료/실패 시 `client_analysis_result` 저장 |
| FR-014 | 상태이력 저장 | Must | 상태 변경 시 `client_analysis_status_history`에 append |
| FR-015 | 멱등성 보장 | Must | `source_system + client_request_id` 중복 요청 정책 적용 |
| FR-016 | 이력 조회 API | Should | 기간/상태/요청ID/시스템명 기준 페이지 조회 가능 |
| FR-017 | 실패 재처리 API | Could | `FAILED/TIMEOUT` 요청 재큐잉 가능 |
| FR-018 | 감사 필드 기록 | Should | 호출자, source_system, client IP, 오류코드 저장 |
| FR-019 | 마스킹 데이터 저장 원칙 | Must | 원문 대신 마스킹 텍스트 저장, 해시 필드 저장 |
| FR-020 | 데이터 보관정책 적용 | Should | 보관기간 경과 데이터 아카이브/삭제 지원 |

---

## 3. 비기능 요구사항 (NFR)

| ID | 요구사항 | 목표/기준 |
| :--- | :--- | :--- |
| NFR-001 | 가용성 | 서비스 가용성 목표 99.9% (월 기준) |
| NFR-002 | 성능(동기) | p95 응답시간 목표 정의 (예: 3초, 환경별 조정) |
| NFR-003 | 성능(비동기) | 큐 대기시간 및 처리량 모니터링 가능 |
| NFR-004 | 보안 | 서버 간 인증(API Key/mTLS), TLS 적용 |
| NFR-005 | 데이터보호 | 마스킹 텍스트 저장, 민감정보 로그 금지 |
| NFR-006 | 관측성 | 구조화 로그 + trace_id + 메트릭 제공 |
| NFR-007 | 확장성 | 워커 수평 확장 가능 구조 |
| NFR-008 | 운영성 | 환경변수 기반 정책 변경 가능 |
| NFR-009 | 테스트성 | 단위/통합/회복탄력성 테스트 자동화 |
| NFR-010 | 감사추적 | 상태변경/오류 이력 조회 가능 |

---

## 4. API 계약 요약

### 4.1 요청 공통 필드

- `source_system` (예: `qa-admin`, `voc-batch`)
- `client_request_id`
- `text` (마스킹된 데이터)
- `tasks`
- `target_speakers`
- `options.prompt_version`

### 4.2 응답 공통 필드

- `request_uid` (서버 내부 UUID)
- `trace_id`
- `status`
- `error_code`, `error_message` (실패 시)

---

## 5. 상태 전이 규칙

1. `RECEIVED`: API 수신 직후
2. `QUEUED`: 비동기 큐 적재 완료
3. `PROCESSING`: 워커/동기 처리 시작
4. `COMPLETED`: 최종 성공
5. `FAILED`: 비즈니스/업스트림 실패
6. `TIMEOUT`: timeout 기준 초과

제약:
- `COMPLETED`, `FAILED`, `TIMEOUT`은 종결 상태
- 종결 상태 이후 상태 전이 금지(재처리는 신규 job 생성)

---

## 6. 오류코드 표준 (초안)

| 코드 | 설명 |
| :--- | :--- |
| `VALIDATION_ERROR` | 입력값 검증 실패 |
| `UPSTREAM_TIMEOUT` | LLMAPI timeout |
| `UPSTREAM_UNAVAILABLE` | LLMAPI 5xx/연결 실패 |
| `QUEUE_UNAVAILABLE` | Redis 큐 사용 불가 |
| `DUPLICATE_REQUEST` | 멱등성 위반 |
| `INTERNAL_ERROR` | 내부 처리 오류 |

---

## 7. 개선 검토 후 추가사항 (v0.2)

기존 초안 대비 아래를 필수/권장으로 상향했다.

1. 필수 상향
- FR-012, FR-013, FR-014, FR-015, FR-019

2. 권장 추가
- FR-016(이력 조회)
- FR-018(감사 필드)
- FR-020(보관정책)

3. 후속 후보
- FR-017(재처리 API)

---

## 8. MVP 구현 체크리스트

1. 동기/비동기 3개 API 구현
2. MySQL 3개 테이블 연동
3. 상태 전이 이력 저장
4. 표준 오류코드 적용
5. trace_id end-to-end 검증
6. 최소 테스트(정상/실패/timeout/중복요청)
