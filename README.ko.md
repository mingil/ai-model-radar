# 📡 AI Model Radar (`ai-model-radar`)

> 🌐 **Language**: [English](./README.md) | **한국어 가이드 (Korean)**

[![Docker Image CI](https://github.com/mingil/ai-model-radar/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/mingil/ai-model-radar/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/docker/v/kimmingil/ai-model-radar?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/kimmingil/ai-model-radar)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

> **각 AI 제조사(Google Gemini, OpenAI, Anthropic Claude, DeepSeek, xAI Grok, Meta Llama, Qwen, Mistral 등)마다 개별 API 키를 일일이 발급받지 않고도, OpenRouter 및 LiteLLM 글로벌 통합 허브를 결합해 현재 시점 정확하게 사용 가능한 최신 모델명·가동률·가격·스펙을 조회하는 올인원 도커 컨테이너입니다.**

---

## ✨ 핵심 특징

1. **🔑 API 키 0개로도 100% 즉시 작동 (Zero-Key Multi-Hub Engine)**
   - **OpenRouter 실시간 모델 API (`450+ 활성 모델`)**와 **LiteLLM 공식 모델 레지스트리 (`4,500+ 모델 스펙`)**를 실시간 결합합니다.
   - 각 AI 사이트마다 가입하고 API 키를 발급받을 필요 없이, 컨테이너 실행 즉시 전 세계 주요 AI 모델의 **정확한 공식 모델명(Native ID)**과 **통합 호출 ID**를 확인할 수 있습니다.
2. **🩺 실시간 클라우드 가동률(Uptime) & 날짜별 스냅샷 버전 진단**
   - 특정 모델을 클릭하면 현재 해당 모델을 서빙 중인 클라우드 백엔드(Google AI Studio, Vertex AI, OpenAI, Anthropic, Bedrock 등)의 **최근 5분 / 30분 / 24시간 실시간 가동률(%)**과 **실제 날짜 스냅샷 버전명(예: `gemini-3.8-flash-20260902`)**을 즉시 조회합니다.
   - 만약 **OpenRouter API 키 단 1개**(또는 보유 중인 소수 API 키)를 입력해 두면, 실제 **1토큰 호출 테스트(Live Ping)**까지 수행하여 응답 속도(`ms`)를 검증합니다.
3. **🏆 제조사별 맞춤 추천 & 전체 모델 일괄 복사**
   - 각 제조사마다 **⚡ 가성비·속도 주력 (Flash / Mini / Haiku)**, **🏆 최고 성능 주력 (Flagship)**, **🧠 추론 특화**, **🎁 무료 모델**을 자동 분류합니다.
   - 개별 모델 `.env` 원클릭 복사는 물론, **각 제조사별 전체 모델 ID 일괄 복사**, **전체 상세표 복사**, **8대 제조사 전체 목록 일괄 복사** 버튼을 모두 지원합니다.
4. **🔒 웹 대시보드 비밀번호 잠금 (`DASHBOARD_PASSWORD`)**
   - 외부 노출 시에도 안전하도록 비밀번호 인증 잠금 화면과 세션 토큰 검증을 기본 탑재했습니다.
5. **🔌 다른 도커 봇을 위한 내부 자동 조회 REST API 제공**
   - 다른 봇 컨테이너에서 `GET http://ai-model-radar:8500/api/resolve/google?tier=fast`를 호출하면 현재 시점 가장 최신 가성비 모델명을 JSON으로 즉시 반환합니다.
6. **✈️ 텔레그램 봇 양방향 조회 & 신규/단종 모델 자동 알림**
   - 새 모델이 출시되거나 기존 모델이 단종 예정(`expiration_date`)으로 바뀌면 텔레그램으로 푸시 알림을 보내며, 채팅방에서 `/models`, `/gemini`, `/openai`, `/claude` 명령어로 언제든 최신 모델명을 조회할 수 있습니다.

---

## 🚀 시놀로지 NAS 1분 설치 가이드 (Container Manager)

### 1. `compose.yaml` 작성

```yaml
services:
  ai-model-radar:
    image: kimmingil/ai-model-radar:latest
    container_name: ai_model_radar
    restart: unless-stopped
    init: true
    user: "1026:100"
    ports:
      - "8500:8500"
    env_file:
      - .env
    environment:
      - TZ=Asia/Seoul
      - PYTHONUNBUFFERED=1
      - PORT=8500
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    deploy:
      resources:
        limits:
          memory: 256M
```

### 2. `.env` 파일 작성 (모두 비워두어도 100% 작동!)

```env
# 선택 사항: 키 1개로 전 모델 1토큰 실호출 Ping 테스트를 원할 때만 입력
OPENROUTER_API_KEY=

# 선택 사항: 보유 중인 개별 API 키가 있다면 입력 (생략 가능)
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# 선택 사항: 텔레그램 알림 및 명령어 조회 연동
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

SCAN_INTERVAL_HOURS=6
PORT=8500
```

### 3. 컨테이너 실행 및 접속

```bash
docker compose up -d
```

- **웹 대시보드 접속**: `http://시놀로지_NAS_IP:8500` (현재 개발 환경에서는 `http://시놀로지_NAS_IP:38500`)
- **내부 REST API 호출 예시**: `http://시놀로지_NAS_IP:8500/api/resolve/google?tier=fast`

---

## 🛠️ 수동 CLI 명령어

```bash
# 1. 현재 캐시된 제조사별 최신 추천 모델 상태 요약 확인
docker exec -it ai_model_radar python -m src.app --status

# 2. 지금 즉시 최신 모델 동기화 1회 실행
docker exec -it ai_model_radar python -m src.app --once

# 3. 특정 제조사(google, openai, claude, deepseek 등) 활성 모델 목록 출력
docker exec -it ai_model_radar python -m src.app --provider google
```
