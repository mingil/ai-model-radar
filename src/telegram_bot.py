"""
Telegram Bot notifier and interactive command responder for AI Model Radar.
"""
import logging
import threading
import time
from typing import Any, Dict, Optional
import requests

from src.config import load_runtime_settings

logger = logging.getLogger("ai_model_radar.telegram")


def send_telegram_message(text: str, chat_id: Optional[str] = None, token: Optional[str] = None) -> bool:
    """Send a Telegram message using HTML parse mode."""
    settings = load_runtime_settings()
    bot_token = token or settings.get("TELEGRAM_BOT_TOKEN", "")
    target_chat = chat_id or settings.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not target_chat:
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": target_chat,
                "text": text[:4000],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        logger.warning("Telegram send error: %s", e)
        return False


def build_summary_message(aggregator: Any) -> str:
    """Build a concise Korean summary of currently active flagship & fast models per major provider."""
    recs = aggregator.get_recommendations()
    lines = [
        "📡 <b>[AI Model Radar] 현재 시점 사용 가능한 최신 AI 모델 요약</b>",
        f"🕒 기준 시각: <code>{aggregator.last_sync_iso}</code>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for r in recs:
        flag = r["flagship"]["native_id"] if r.get("flagship") else "-"
        fast = r["fast"]["native_id"] if r.get("fast") else "-"
        lines.append(
            f"{r['icon']} <b>{r['provider_name']}</b> (활성 {r['total_active']}종)\n"
            f"  • 최고성능: <code>{flag}</code>\n"
            f"  • 가성비/속도: <code>{fast}</code>\n"
            f"  • .env 설정: <code>{r['env_var']}={fast}</code>"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💡 상세 조회: <code>/gemini</code> <code>/openai</code> <code>/claude</code> <code>/deepseek</code>")
    return "\n".join(lines)


def build_provider_message(aggregator: Any, provider_query: str) -> str:
    """Build a detailed list of active models for a specific provider."""
    alias = {
        "gemini": "google",
        "google": "google",
        "gpt": "openai",
        "openai": "openai",
        "claude": "anthropic",
        "anthropic": "anthropic",
        "deepseek": "deepseek",
        "grok": "x-ai",
        "xai": "x-ai",
        "llama": "meta-llama",
        "qwen": "qwen",
        "mistral": "mistralai",
    }
    slug = alias.get(provider_query.lower().strip(), provider_query.lower().strip())
    models = aggregator.get_models(provider=slug, exclude_batch=True, active_only=True)
    if not models:
        return f"⚠️ <code>{provider_query}</code> 제조사의 활성 모델을 찾을 수 없습니다."

    p_name = models[0]["provider_name"]
    p_icon = models[0]["provider_icon"]
    lines = [
        f"{p_icon} <b>{p_name} 현재 사용 가능한 최신 모델 ({len(models)}종)</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for m in models[:15]:
        price_str = "무료" if m["is_free"] else f"${m['input_cost_1m']}/${m['output_cost_1m']}"
        lines.append(
            f"• <code>{m['native_id']}</code> ({m['tier'].upper()})\n"
            f"  └ OpenRouter: <code>{m['openrouter_id']}</code> | {price_str} | 출시: {m['created_date']}"
        )
    if len(models) > 15:
        lines.append(f"\n…외 {len(models) - 15}개 모델이 더 있습니다.")
    return "\n".join(lines)


def build_change_alert_message(changes: Dict[str, Any]) -> Optional[str]:
    """Build a Telegram alert message when new models are added or deprecated."""
    added = changes.get("added") or []
    removed = changes.get("removed") or []
    expiring = changes.get("expiring") or []
    if not added and not removed and not expiring:
        return None

    lines = ["🔔 <b>[AI Model Radar] AI 모델 변경 감지 알림</b>", "━━━━━━━━━━━━━━━━━━━━"]
    if added:
        lines.append(f"✨ <b>신규 출시/추가된 모델 ({len(added)}종)</b>")
        for m in added[:10]:
            lines.append(f"  • [{m['provider']}] <code>{m['native_id']}</code> ({m['name']})")
    if expiring:
        lines.append(f"\n⚠️ <b>단종 예정 감지 ({len(expiring)}종)</b>")
        for m in expiring[:10]:
            lines.append(f"  • <code>{m['native_id']}</code> (만료일: {m.get('expiration_date')})")
    if removed:
        lines.append(f"\n🚨 <b>제거/단종된 모델 ({len(removed)}종)</b>")
        for m in removed[:10]:
            lines.append(f"  • [{m['provider']}] <code>{m['native_id']}</code>")
    return "\n".join(lines)


class TelegramBotWorker:
    """Background long-polling responder for Telegram commands."""

    def __init__(self, aggregator: Any) -> None:
        self.aggregator = aggregator
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._offset = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            settings = load_runtime_settings()
            token = settings.get("TELEGRAM_BOT_TOKEN", "")
            if not token:
                time.sleep(15)
                continue

            try:
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                resp = requests.get(
                    url,
                    params={"offset": self._offset, "timeout": 10},
                    timeout=15,
                )
                if resp.status_code == 200:
                    for upd in resp.json().get("result", []):
                        self._offset = upd["update_id"] + 1
                        msg = upd.get("message") or {}
                        text = (msg.get("text") or "").strip()
                        chat_id = str((msg.get("chat") or {}).get("id") or "")
                        if text and chat_id:
                            self._handle_command(text, chat_id, token)
                else:
                    time.sleep(10)
            except Exception:
                time.sleep(10)

    def _handle_command(self, text: str, chat_id: str, token: str) -> None:
        cmd_parts = text.split(maxsplit=1)
        cmd = cmd_parts[0].lower().split("@")[0]
        arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

        if cmd in ("/start", "/help"):
            reply = (
                "📡 <b>AI Model Radar 봇 명령어 안내</b>\n\n"
                "• <code>/models</code> — 제조사별 현재 최신 주력/가성비 모델 요약\n"
                "• <code>/gemini</code> — Google Gemini 사용 가능 모델 목록\n"
                "• <code>/openai</code> — OpenAI GPT/o-시리즈 모델 목록\n"
                "• <code>/claude</code> — Anthropic Claude 모델 목록\n"
                "• <code>/deepseek</code> — DeepSeek 모델 목록\n"
                "• <code>/grok</code> — xAI Grok 모델 목록\n"
                "• <code>/search 키워드</code> — 모델 검색\n"
                "• <code>/scan</code> — 즉시 최신 모델 목록 동기화"
            )
            send_telegram_message(reply, chat_id=chat_id, token=token)
        elif cmd in ("/models", "/summary"):
            send_telegram_message(build_summary_message(self.aggregator), chat_id=chat_id, token=token)
        elif cmd in ("/gemini", "/google", "/openai", "/gpt", "/claude", "/anthropic", "/deepseek", "/grok", "/llama", "/qwen", "/mistral"):
            send_telegram_message(build_provider_message(self.aggregator, cmd.lstrip("/")), chat_id=chat_id, token=token)
        elif cmd == "/provider" and arg:
            send_telegram_message(build_provider_message(self.aggregator, arg), chat_id=chat_id, token=token)
        elif cmd == "/search" and arg:
            matches = self.aggregator.get_models(search=arg, exclude_batch=True)[:12]
            if not matches:
                send_telegram_message(f"🔍 <code>{arg}</code> 검색 결과가 없습니다.", chat_id=chat_id, token=token)
            else:
                lines = [f"🔍 <b>'{arg}' 검색 결과 ({len(matches)}건)</b>"]
                for m in matches:
                    lines.append(f"• [{m['provider']}] <code>{m['native_id']}</code> (OR: <code>{m['openrouter_id']}</code>)")
                send_telegram_message("\n".join(lines), chat_id=chat_id, token=token)
        elif cmd == "/scan":
            res = self.aggregator.sync()
            send_telegram_message(
                f"✅ 동기화 완료! 총 <b>{res.get('total_models', 0)}개</b> 활성 모델 확인됨.\n기준: <code>{res.get('last_sync_iso')}</code>",
                chat_id=chat_id,
                token=token,
            )
