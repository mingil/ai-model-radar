# 📡 AI Model Radar (`ai-model-radar`)

> 🌐 **Language**: **English** | [한국어 가이드 (Korean)](./README.ko.md)

[![Docker Image CI](https://github.com/mingil/ai-model-radar/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/mingil/ai-model-radar/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/docker/v/kimmingil/ai-model-radar?label=Docker%20Hub&logo=docker)](https://hub.docker.com/r/kimmingil/ai-model-radar)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

> **All-in-One Docker container that discovers, verifies, and recommends currently available AI models across all major providers (Google Gemini, OpenAI, Anthropic Claude, DeepSeek, xAI Grok, Meta Llama, Alibaba Qwen, Mistral) using OpenRouter and LiteLLM global registries — requiring zero or minimal API keys.**

---

## ✨ Key Features

- **🌐 Zero-Key Multi-Hub Aggregation**: Combines OpenRouter's live model API (`450+ active models`) and LiteLLM's official specification registry (`4,500+ model specs`) without requiring separate API keys for every provider.
- **🩺 Real-Time Cloud Uptime & Snapshot Inspector**: Inspects 5-minute, 30-minute, and 24-hour live uptime percentages across cloud backends (Google AI Studio, Vertex AI, OpenAI, Anthropic, AWS Bedrock) and reveals exact dated snapshot IDs.
- **🔑 Optional Few-Key Live Ping**: Add just a single `OPENROUTER_API_KEY` (or optional provider keys) to perform 1-token live completion pings and measure latency (`ms`).
- **🏆 Smart Tier Classifier & One-Click `.env` Copy**: Automatically classifies models into `Flagship`, `Fast (Flash/Mini/Haiku)`, `Reasoning`, and `Free` tiers, mapping both **Native Provider IDs** and **OpenRouter IDs**.
- **🔌 Internal Docker Resolver API**: Other bots can query `GET /api/resolve/google?tier=fast` to dynamically retrieve the latest active model ID.
- **✈️ Telegram Bot & Change Alerts**: Sends notifications when new models launch or existing ones enter deprecation, and responds to `/models`, `/gemini`, `/openai`, `/claude`, `/search`, and `/scan`.
