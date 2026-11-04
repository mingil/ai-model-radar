"""
Configuration management & authentication helpers for AI Model Radar.
Loads environment variables and runtime key overrides stored in data/settings.json.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
LOG_DIR = Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

SETTINGS_FILE = DATA_DIR / "settings.json"
STATE_FILE = DATA_DIR / "model_state.json"
CHANGELOG_FILE = DATA_DIR / "model_changelog.json"
HEARTBEAT_FILE = Path("/tmp/ai_model_radar_heartbeat")

# Major providers highlighted in dashboard & recommendations
MAJOR_PROVIDERS = [
    {
        "slug": "google",
        "name": "Google Gemini",
        "icon": "💎",
        "env_var": "GEMINI_MODEL",
        "key_env": "GEMINI_API_KEY",
        "litellm_prefixes": ["gemini/", "vertex_ai/"],
    },
    {
        "slug": "openai",
        "name": "OpenAI (GPT / o-시리즈)",
        "icon": "🟢",
        "env_var": "OPENAI_MODEL",
        "key_env": "OPENAI_API_KEY",
        "litellm_prefixes": ["openai/", ""],
    },
    {
        "slug": "anthropic",
        "name": "Anthropic Claude",
        "icon": "🟠",
        "env_var": "ANTHROPIC_MODEL",
        "key_env": "ANTHROPIC_API_KEY",
        "litellm_prefixes": ["anthropic/", "claude-"],
    },
    {
        "slug": "deepseek",
        "name": "DeepSeek",
        "icon": "🐋",
        "env_var": "DEEPSEEK_MODEL",
        "key_env": "DEEPSEEK_API_KEY",
        "litellm_prefixes": ["deepseek/"],
    },
    {
        "slug": "x-ai",
        "name": "xAI Grok",
        "icon": "✖️",
        "env_var": "XAI_MODEL",
        "key_env": "XAI_API_KEY",
        "litellm_prefixes": ["xai/"],
    },
    {
        "slug": "meta-llama",
        "name": "Meta Llama",
        "icon": "🦙",
        "env_var": "LLAMA_MODEL",
        "key_env": "GROQ_API_KEY",
        "litellm_prefixes": ["meta_llama/", "groq/"],
    },
    {
        "slug": "qwen",
        "name": "Alibaba Qwen",
        "icon": "🟣",
        "env_var": "QWEN_MODEL",
        "key_env": "OPENROUTER_API_KEY",
        "litellm_prefixes": ["qwen/", "dashscope/"],
    },
    {
        "slug": "mistralai",
        "name": "Mistral AI",
        "icon": "🌪️",
        "env_var": "MISTRAL_MODEL",
        "key_env": "MISTRAL_API_KEY",
        "litellm_prefixes": ["mistral/"],
    },
]


def load_runtime_settings() -> Dict[str, Any]:
    """Load runtime settings saved via Web UI, merged with .env defaults."""
    saved: Dict[str, Any] = {}
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            saved = {}

    keys = [
        "OPENROUTER_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "GROQ_API_KEY",
        "XAI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "DASHBOARD_PASSWORD",
    ]
    result: Dict[str, Any] = {}
    for k in keys:
        val = saved.get(k) or os.getenv(k, "")
        if val and not str(val).startswith("your_") and not str(val).startswith("당신의_"):
            result[k] = str(val).strip()
        else:
            result[k] = ""

    # Fallback password from APP_PASSWORD or BOT_PASSWORD if DASHBOARD_PASSWORD is not explicitly set
    if not result["DASHBOARD_PASSWORD"]:
        fallback_pw = os.getenv("APP_PASSWORD") or os.getenv("BOT_PASSWORD") or "admin1234"
        result["DASHBOARD_PASSWORD"] = fallback_pw.strip()

    result["SCAN_INTERVAL_HOURS"] = float(
        saved.get("SCAN_INTERVAL_HOURS") or os.getenv("SCAN_INTERVAL_HOURS", "6")
    )
    result["ALERT_ON_NEW_MODEL"] = str(
        saved.get("ALERT_ON_NEW_MODEL", os.getenv("ALERT_ON_NEW_MODEL", "true"))
    ).lower() in ("true", "1", "yes")
    result["ALERT_ON_DEPRECATED"] = str(
        saved.get("ALERT_ON_DEPRECATED", os.getenv("ALERT_ON_DEPRECATED", "true"))
    ).lower() in ("true", "1", "yes")
    return result


def get_allowed_passwords() -> List[str]:
    """Return list of valid dashboard passwords (supports comma-separated multiple passwords)."""
    settings = load_runtime_settings()
    raw = settings.get("DASHBOARD_PASSWORD", "admin1234")
    pws = [p.strip() for p in raw.split(",") if p.strip()]
    return pws or ["admin1234"]


def verify_password(candidate: str) -> bool:
    """Verify if the candidate password matches any configured allowed password."""
    if not candidate:
        return False
    cand = candidate.strip()
    for pw in get_allowed_passwords():
        if hmac.compare_digest(cand.encode("utf-8"), pw.encode("utf-8")):
            return True
    return False


def create_auth_token() -> str:
    """Create a deterministic HMAC token bound to the current password setting."""
    pws = ",".join(get_allowed_passwords())
    secret = f"ai-model-radar-auth:{pws}".encode("utf-8")
    return hmac.new(secret, b"radar-authenticated-session", hashlib.sha256).hexdigest()


def verify_auth_token(token: str) -> bool:
    """Verify if a client token matches the active session token."""
    if not token:
        return False
    expected = create_auth_token()
    return hmac.compare_digest(token.strip(), expected)


def save_runtime_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Atomically save runtime settings to data/settings.json."""
    current = {}
    if SETTINGS_FILE.exists():
        try:
            current = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            current = {}

    for k, v in updates.items():
        if v is not None:
            current[k] = v.strip() if isinstance(v, str) else v

    tmp_path = SETTINGS_FILE.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, SETTINGS_FILE)
    return load_runtime_settings()


def mask_key(key: str) -> str:
    """Return a masked preview of an API key for safe display."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"
