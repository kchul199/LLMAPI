# LLMAPI 현행 구현 점검 및 개선 제안 (v1.3)

## 1. 목적

이 문서는 코드/문서 정합성을 점검하고, 개선 제안 항목 중 실제 반영 상태를 추적하기 위해 작성되었습니다.

## 2. 반영 완료 항목

### 2.1 API 계약/검증
- `AnalysisRequest` 검증 강화
  - 빈 문자열 차단
  - 허용 task 제한(`summary`, `sentiment`, `category`)
  - task 중복 제거
  - 예상치 못한 필드 차단(`extra="forbid"`)

### 2.2 LLM 안정성
- Retry + Fail-over 유지
- Circuit Breaker 도입 (메인/백업)
- task 기반 timeout 정책 도입
- 업스트림 장애 시 `502` 명확화

### 2.3 프롬프트 운영
- 프롬프트 파일 변경 자동 재로딩
- `options.prompt_version` 기반 버전 라우팅
- Health API에 사용 가능한 프롬프트 버전 노출

### 2.4 Redis 큐 정합성
- 비동기 분석 큐 서비스 구현 (`src/services/queue.py`)
- 비동기 API 추가
  - `POST /v1/analyze/async`
  - `GET /v1/analyze/async/{job_id}`
- 앱 시작 시 큐 워커 초기화/종료 훅 연결

### 2.5 품질 게이트
- 단위 테스트 추가/보강
- GitHub Actions CI 추가 (`.github/workflows/ci.yml`)
  - compile check
  - unittest

## 3. 남은 개선 과제 (우선순위)

### P1
1. 장애 코드 표준화(내부 코드 + 운영 대시보드 매핑)
2. 큐 재시도/Dead Letter Queue(DLQ) 정책

### P2
1. 프롬프트 회귀 평가 자동 리포트(샘플셋 기반)
2. 모델 벤더별 어댑터 계층 분리

### P3
1. 비밀정보 관리 고도화(Vault/Secret Manager)
2. PII 마스킹 상태 서버 샘플 검증 로직

---
작성일: 2026-04-12
