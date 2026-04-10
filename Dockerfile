# build stage
FROM python:3.9-slim as builder

WORKDIR /app

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 필수 도구 및 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# final stage
FROM python:3.9-slim

WORKDIR /app

# 빌더 작업 결과물 복사
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 소스 코드 및 프롬프트 설정 복사
COPY . .

# 포트 설정
EXPOSE 8001

# 실행 환경 설정
ENV PYTHONPATH=/app

# uvicorn 실행
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
