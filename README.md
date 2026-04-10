# 🚀 LLMAPI: 기업용 AI 상담 분석 오케스트레이션 엔진

**LLMAPI**는 고객센터의 상담 대화 데이터를 실시간으로 분석하여 **자동 요약, 감정 분석, 상담 카테고리 분류**를 수행하는 지능형 미들웨어 솔루션입니다. 고성능 상용 엔진(vLLM)과 안정적인 로컬 엔진(Ollama)을 결합하여 365일 중단 없는 AI 서비스를 제공합니다.

---

## 🌟 주요 특징 (Key Features)

- **🧩 엔진 애그노스틱 (Engine Agnostic)**: OpenAI 규격을 준수하여 Ollama, vLLM, OpenAI 등 어떤 엔진으로도 즉시 전환이 가능합니다.
- **🛡️ 장애 복구 (Automatic Fail-over)**: 메인 분석 엔진에 장애가 발생하면 1초 이내에 백업 엔진으로 자동 전환되어 서비스 연속성을 보장합니다.
- **📊 구조화된 로깅 (JSON Logging)**: 모든 분석 이력을 정형화된 JSON 로거로 기록하여 ElasticSearch, Datadog 등 로그 분석 솔루션과 즉시 연동됩니다.
- **🧬 유연한 프롬프트 관리**: 코드 수정 없이 `prompts.yaml` 파일만 편집하여 분석 품질과 페르소나를 실시간으로 튜닝할 수 있습니다.

---

## 🏗️ 시스템 구성 (Architecture)

본 시스템은 최고의 추론 성능을 위해 **하이브리드(Hybrid)** 방식을 채택하고 있습니다.

1.  **FastAPI App (Docker Container)**: 분석 로직 및 API 엔드포인트 관리.
2.  **Redis (Docker Container)**: 대규모 트래픽 처리를 위한 비동기 메시지 큐 담당.
3.  **Ollama (Mac Native App)**: Apple Silicon GPU(Metal) 가속을 활용한 초고속 LLM 추론.

---

## 🛠️ 초보자를 위한 설치 가이드 (Step-by-Step)

### 1단계: Mac 네이티브 Ollama 환경 구축
모델 추론은 CPU보다 GPU가 훨씬 빠르기 때문에 Mac 전용 앱을 사용하는 것이 권장됩니다.

1.  **Ollama 설치**: [Ollama 공식 홈페이지](https://ollama.com/)에서 다운로드 후 설치합니다.
2.  **외부 접속 허용 (가장 중요)**: 기본 설정은 외부 접속이 차단되어 있습니다. 터미널을 열고 아래 명령어를 입력하세요.
    ```bash
    # 컨테이너의 접근을 허용하는 핵심 설정
    launchctl setenv OLLAMA_HOST "0.0.0.0"
    ```
    *입력 후 반드시 상단 메뉴바의 Ollama 아이콘을 클릭하여 'Quit Ollama' 한 뒤, 다시 앱을 실행해 주세요.*
3.  **모델 다운로드**: 터미널에서 아래 모델들을 미리 내려받습니다.
    ```bash
    ollama pull llama3.2:3b  # 메인 분석용
    ollama pull llama3.2:1b  # 장애 대비 백업용
    ```

### 2단계: 프로젝트 실행 (Docker Compose)
프로젝트 폴더로 이동하여 도커 컨테이너를 실행합니다. (Docker Desktop이 실행 중이어야 합니다.)

```bash
cd LLMAPI
docker compose up --build -d
```

### 3단계: 가동 확인 (Health Check)
브라우저에서 아래 주소에 접속하여 서버 상태를 확인합니다.
- `http://localhost:8001/v1/health`
- `{"status":"healthy", ...}` 응답이 나오면 성공입니다!

---

## 🧪 테스트 및 품질 검증

분석 품질이 정상인지 확인하기 위해 두 가지 도구를 제공합니다.

1.  **통합 기능 테스트**: 전체 네트워크와 장애 대응 로직이 정상인지 확인합니다.
    ```bash
    python3 tests/system_test.py
    ```
2.  **프롬프트 품질 평가**: 실제 샘플 데이터를 분석하여 품질(요약 완성도, 감정 정확도)을 확인합니다.
    ```bash
    python3 tests/evaluate_prompts.py
    ```

---

## 🆘 트러블슈팅 (Troubleshooting)

### 1. `Connection Error`가 발생하며 분석이 안 됩니다.
- **원인**: Docker 컨테이너가 Mac 호스트의 Ollama를 찾지 못하는 경우입니다.
- **해결**:
    - Mac 터미널에서 `launchctl setenv OLLAMA_HOST "0.0.0.0"` 명령어를 실행했는지 확인하세요.
    - Ollama 앱을 완전히 종료 후 재기동했는지 확인하세요.
    - `.env` 파일의 `LLM_BASE_URL`이 `http://host.docker.internal:11434/v1`인지 확인하세요.

### 2. 컨테이너가 자꾸 `Restarting` 상태가 됩니다.
- **원인**: 라이브러리 간의 버전 충돌이 발생한 경우입니다. (특히 `openai`와 `httpx`)
- **해결**: 본 프로젝트는 `requirements.txt`에 `httpx==0.27.2`로 버전을 고정하여 패키지 충돌을 방지하고 있습니다. `docker compose build --no-cache` 명령으로 깨끗하게 다시 빌드해 보세요.

### 3. 분석 결과가 너무 느립니다.
- **원인**: GPU가 아닌 CPU로 추론 중일 가능성이 높습니다.
- **해결**: Ollama 앱이 Mac 상단 바에 잘 떠 있는지, Docker 내부가 아닌 Mac 네이티브 앱에서 실행 중인지 확인하세요.

---

## 📄 API 연동 규격
자세한 Request/Response 명세는 [docs/LLMAPI_연동규격서_v1_0.md](docs/LLMAPI_연동규격서_v1_0.md) 파일을 참조해 주세요.

---
**Maintainer**: lkc (kchul199)
**Version**: 1.1.0
