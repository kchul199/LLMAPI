# [DB 설계서] Client 서버 MySQL 스키마 설계 (v0.1)

작성일: 2026-04-12  
목적: Client 서버의 요청 이력/결과 저장을 위한 MySQL 테이블 구조를 정의한다.

---

## 1. 설계 원칙

1. 요청/결과/상태이력을 분리해 추적성과 확장성을 확보한다.
2. 멱등키를 강제해 중복 요청을 제어한다.
3. 원문 대신 마스킹 텍스트 저장을 기본 원칙으로 한다.
4. 운영 조회가 빠르도록 상태/시간 기반 인덱스를 우선 설계한다.

---

## 2. 엔티티 개요

### 2.1 `client_analysis_request`
요청의 마스터 레코드

- 누가/언제/무엇을 요청했는지
- 현재 처리 상태
- LLMAPI 호출 결과 메타

### 2.2 `client_analysis_result`
최종 분석 결과

- summary/sentiment/category
- usage, latency, fallback 여부

### 2.3 `client_analysis_status_history`
상태 전이 감사 로그

- 어떤 상태에서 어떤 상태로 바뀌었는지
- 이유 코드/메시지

---

## 3. DDL

```sql
-- MySQL 8.x 기준
CREATE TABLE client_analysis_request (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_uid CHAR(36) NOT NULL COMMENT '내부 고유 요청 ID(UUID)',

    source_system VARCHAR(64) NOT NULL COMMENT '요청 시스템 식별자',
    client_request_id VARCHAR(100) NOT NULL COMMENT '업무시스템 요청 ID',
    trace_id VARCHAR(64) NOT NULL,

    mode ENUM('sync','async') NOT NULL,
    status ENUM('RECEIVED','QUEUED','PROCESSING','COMPLETED','FAILED','TIMEOUT')
        NOT NULL DEFAULT 'RECEIVED',

    text_masked LONGTEXT NOT NULL COMMENT '마스킹된 원문 텍스트',
    text_sha256 CHAR(64) NOT NULL COMMENT '중복 탐지/검색용 해시',

    tasks JSON NOT NULL,
    target_speakers ENUM('agent','customer','both') NOT NULL DEFAULT 'both',
    prompt_version VARCHAR(32) NULL,

    llmapi_request_id VARCHAR(100) NULL,
    llmapi_http_status SMALLINT UNSIGNED NULL,
    retry_count TINYINT UNSIGNED NOT NULL DEFAULT 0,

    error_code VARCHAR(64) NULL,
    error_message VARCHAR(500) NULL,

    received_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    queued_at DATETIME(3) NULL,
    started_at DATETIME(3) NULL,
    completed_at DATETIME(3) NULL,

    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
        ON UPDATE CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_request_uid (request_uid),
    UNIQUE KEY uk_source_client_request (source_system, client_request_id),

    KEY idx_status_created (status, created_at),
    KEY idx_trace_id (trace_id),
    KEY idx_received_at (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE client_analysis_result (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_id BIGINT UNSIGNED NOT NULL,

    result_status ENUM('SUCCESS','FAIL') NOT NULL DEFAULT 'SUCCESS',

    summary TEXT NULL,
    sentiment VARCHAR(32) NULL,
    category VARCHAR(64) NULL,
    result_json JSON NOT NULL COMMENT '원본 결과(JSON)',

    usage_total_tokens INT UNSIGNED NOT NULL DEFAULT 0,
    usage_latency_ms INT UNSIGNED NOT NULL DEFAULT 0,
    llm_model VARCHAR(128) NULL,
    is_fallback TINYINT(1) NOT NULL DEFAULT 0,
    prompt_version_applied VARCHAR(32) NULL,

    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_result_request
      FOREIGN KEY (request_id) REFERENCES client_analysis_request(id)
      ON DELETE CASCADE,

    UNIQUE KEY uk_request_result (request_id),
    KEY idx_result_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE client_analysis_status_history (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_id BIGINT UNSIGNED NOT NULL,

    prev_status ENUM('RECEIVED','QUEUED','PROCESSING','COMPLETED','FAILED','TIMEOUT') NULL,
    new_status  ENUM('RECEIVED','QUEUED','PROCESSING','COMPLETED','FAILED','TIMEOUT') NOT NULL,

    reason_code VARCHAR(64) NULL,
    reason_message VARCHAR(500) NULL,
    actor VARCHAR(32) NOT NULL DEFAULT 'system',
    changed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_status_request
      FOREIGN KEY (request_id) REFERENCES client_analysis_request(id)
      ON DELETE CASCADE,

    KEY idx_status_req_changed (request_id, changed_at),
    KEY idx_status_new_changed (new_status, changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 4. 상태 전이 저장 규칙

1. 요청 수신 시 `client_analysis_request.status = RECEIVED`
2. 비동기 큐 등록 성공 시 `QUEUED`
3. 처리 시작 시 `PROCESSING`
4. 처리 성공 시 `COMPLETED`
5. 실패 시 `FAILED` 또는 `TIMEOUT`
6. 모든 전이는 `client_analysis_status_history`에 append

---

## 5. 조회 패턴과 인덱스 의도

### 5.1 운영 조회

- 상태별 최근 건: `idx_status_created`
- trace_id 단건 추적: `idx_trace_id`
- 기간 필터 조회: `idx_received_at`

### 5.2 멱등 처리

- `uk_source_client_request`를 통해 중복 요청 차단

### 5.3 결과 조인

- `client_analysis_result.request_id` 고유 인덱스로 1:1 조인 보장

---

## 6. 데이터 보관/아카이브 정책 제안

1. 운영 테이블 보관기간 예시: 90일
2. 90일 초과 데이터는 아카이브 테이블/스토리지로 이동
3. 삭제 전 최소 1회 백업 검증

권장 배치 작업:
- 일 배치: 상태 완료건 아카이브 후보 수집
- 주 배치: 아카이브 이동 + 운영 테이블 정리

---

## 7. 보안/컴플라이언스 고려사항

1. 원문 저장 금지(마스킹 텍스트 원칙)
2. `text_sha256`는 복호화 불가 해시만 저장
3. DB 계정 최소 권한(읽기/쓰기 분리)
4. 감사 목적으로 상태이력 테이블 무손실 보관

---

## 8. 구현 시 유의사항

1. 트랜잭션 경계
- 요청 저장 + 상태이력 초기 insert는 하나의 트랜잭션으로 처리

2. 오류 처리
- DB 저장 실패 시 API는 명확한 내부오류 코드 반환

3. 시간대
- 저장은 UTC 권장, 응답 시 필요하면 로컬 변환

---

## 9. 향후 확장

1. 파티셔닝
- `created_at` 기준 월 단위 파티션

2. 재처리 큐
- 실패 레코드 재처리 시도 카운트 필드 추가

3. 감사 확장
- `actor_id`, `client_ip`, `user_agent` 필드 확장
