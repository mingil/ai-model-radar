"""
Multi-Hub AI Model Aggregator & Change Radar.
Combines OpenRouter Live API + LiteLLM Official Registry + Optional Direct Provider APIs.
"""
import datetime
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

from src.config import (
    CHANGELOG_FILE,
    HEARTBEAT_FILE,
    MAJOR_PROVIDERS,
    STATE_FILE,
    load_runtime_settings,
)

logger = logging.getLogger("ai_model_radar")

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
LITELLM_REGISTRY_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)

PROVIDER_META_MAP = {p["slug"]: p for p in MAJOR_PROVIDERS}


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _format_timestamp(ts: Any) -> str:
    try:
        val = int(ts)
        if val <= 0:
            return "-"
        dt = datetime.datetime.fromtimestamp(val, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "-"


def classify_model_tier(native_id: str, name: str, is_free: bool, has_reasoning: bool) -> str:
    """Classify a model into flagship, fast, reasoning, or free tier."""
    low = f" {native_id} {name} ".lower()
    if is_free or ":free" in low:
        return "free"
    if any(
        k in low
        for k in [
            "flash",
            "-mini",
            " mini",
            "haiku",
            "nano",
            "-lite",
            " lite",
            "-small",
            " small",
            "ministral",
            "scout",
            "instant",
        ]
    ):
        return "fast"
    if any(k in low for k in ["thinking", "reasoner", "-r1", " o1", " o3", " o4", "/o1", "/o3", "/o4", "qwq"]):
        return "reasoning"
    if any(
        k in low
        for k in [
            "pro",
            "opus",
            "sonnet",
            "argon",
            "terra",
            "sol",
            "max",
            "large",
            "maverick",
            "grok-4",
            "gpt-6",
            "gpt-5",
            "deepseek-v4",
            "deepseek-v3",
        ]
    ):
        return "flagship"
    if has_reasoning:
        return "reasoning"
    return "standard"


def build_litellm_id(provider_slug: str, native_id: str, litellm_registry: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Find matching LiteLLM entry and return (litellm_id, spec_dict)."""
    candidates = [
        native_id,
        f"{provider_slug}/{native_id}",
        f"gemini/{native_id}" if provider_slug == "google" else "",
        f"vertex_ai/{native_id}" if provider_slug == "google" else "",
        f"anthropic/{native_id}" if provider_slug == "anthropic" else "",
        f"openai/{native_id}" if provider_slug == "openai" else "",
        f"deepseek/{native_id}" if provider_slug == "deepseek" else "",
        f"xai/{native_id}" if provider_slug == "x-ai" else "",
        f"mistral/{native_id}" if provider_slug == "mistralai" else "",
        f"openrouter/{provider_slug}/{native_id}",
    ]
    for cand in candidates:
        if cand and cand in litellm_registry:
            spec = litellm_registry[cand]
            if isinstance(spec, dict):
                return cand, spec

    # Prefix fallback
    default_prefix = {
        "google": f"gemini/{native_id}",
        "openai": f"openai/{native_id}",
        "anthropic": f"anthropic/{native_id}",
        "deepseek": f"deepseek/{native_id}",
        "x-ai": f"xai/{native_id}",
        "mistralai": f"mistral/{native_id}",
        "qwen": f"openrouter/qwen/{native_id}",
        "meta-llama": f"openrouter/meta-llama/{native_id}",
    }.get(provider_slug, f"openrouter/{provider_slug}/{native_id}")
    return default_prefix, {}


class ModelAggregator:
    """Fetches, normalizes, and caches AI model availability across global hubs."""

    def __init__(self) -> None:
        self.models: List[Dict[str, Any]] = []
        self.last_sync_ts: float = 0.0
        self.last_sync_iso: str = "-"
        self.hub_status: Dict[str, Any] = {
            "openrouter": {"ok": False, "count": 0, "latency_ms": 0, "error": None},
            "litellm": {"ok": False, "count": 0, "latency_ms": 0, "error": None},
            "direct_keys": {"configured": [], "verified_models": 0},
        }
        self._load_cached_state()

    def _touch_heartbeat(self) -> None:
        try:
            HEARTBEAT_FILE.write_text(str(time.time()), encoding="utf-8")
        except Exception:
            pass

    def _load_cached_state(self) -> None:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self.models = data.get("models", [])
                self.last_sync_ts = data.get("last_sync_ts", 0.0)
                self.last_sync_iso = data.get("last_sync_iso", "-")
                self.hub_status = data.get("hub_status", self.hub_status)
            except Exception as e:
                logger.warning("Failed to load cached state: %s", e)

    def _atomic_write_json(self, path: Path, payload: Any) -> None:
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)

    def fetch_openrouter_models(self, api_key: str = "") -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
        t0 = time.time()
        headers = {"User-Agent": "AI-Model-Radar/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            resp = requests.get(OPENROUTER_MODELS_URL, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            latency = int((time.time() - t0) * 1000)
            return data, latency, None
        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            logger.error("OpenRouter fetch error: %s", e)
            return [], latency, str(e)

    def fetch_litellm_registry(self) -> Tuple[Dict[str, Any], int, Optional[str]]:
        t0 = time.time()
        headers = {"User-Agent": "AI-Model-Radar/1.0"}
        try:
            resp = requests.get(LITELLM_REGISTRY_URL, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            data.pop("sample_spec", None)
            latency = int((time.time() - t0) * 1000)
            return data, latency, None
        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            logger.error("LiteLLM fetch error: %s", e)
            return {}, latency, str(e)

    def fetch_direct_provider_models(self, settings: Dict[str, Any]) -> Tuple[set, List[str]]:
        """
        If optional provider API keys are configured, query their official /models endpoints
        to confirm direct key access.
        """
        verified_native_ids = set()
        configured_providers = []

        if settings.get("OPENROUTER_API_KEY"):
            configured_providers.append("OpenRouter")

        # 1. Google Gemini official API
        gemini_key = settings.get("GEMINI_API_KEY")
        if gemini_key:
            configured_providers.append("Google Gemini")
            try:
                r = requests.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}",
                    timeout=10,
                )
                if r.status_code == 200:
                    for m in r.json().get("models", []):
                        name = m.get("name", "").replace("models/", "")
                        if name:
                            verified_native_ids.add(name)
            except Exception as e:
                logger.warning("Direct Gemini model check failed: %s", e)

        # 2. OpenAI official API
        openai_key = settings.get("OPENAI_API_KEY")
        if openai_key:
            configured_providers.append("OpenAI")
            try:
                r = requests.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    for m in r.json().get("data", []):
                        if m.get("id"):
                            verified_native_ids.add(m["id"])
            except Exception as e:
                logger.warning("Direct OpenAI model check failed: %s", e)

        # 3. Anthropic official API
        anthropic_key = settings.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            configured_providers.append("Anthropic")
            try:
                r = requests.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": anthropic_key,
                        "anthropic-version": "2023-06-01",
                    },
                    timeout=10,
                )
                if r.status_code == 200:
                    for m in r.json().get("data", []):
                        if m.get("id"):
                            verified_native_ids.add(m["id"])
            except Exception as e:
                logger.warning("Direct Anthropic model check failed: %s", e)

        # 4. DeepSeek official API
        deepseek_key = settings.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            configured_providers.append("DeepSeek")
            try:
                r = requests.get(
                    "https://api.deepseek.com/models",
                    headers={"Authorization": f"Bearer {deepseek_key}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    for m in r.json().get("data", []):
                        if m.get("id"):
                            verified_native_ids.add(m["id"])
            except Exception as e:
                logger.warning("Direct DeepSeek model check failed: %s", e)

        # 5. Groq official API
        groq_key = settings.get("GROQ_API_KEY")
        if groq_key:
            configured_providers.append("Groq")
            try:
                r = requests.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    timeout=10,
                )
                if r.status_code == 200:
                    for m in r.json().get("data", []):
                        if m.get("id"):
                            verified_native_ids.add(m["id"])
            except Exception as e:
                logger.warning("Direct Groq model check failed: %s", e)

        return verified_native_ids, configured_providers

    def sync(self, save_state: bool = True) -> Dict[str, Any]:
        """Synchronize live models from OpenRouter + LiteLLM + Direct Keys and detect changes."""
        settings = load_runtime_settings()
        or_models, or_lat, or_err = self.fetch_openrouter_models(settings.get("OPENROUTER_API_KEY", ""))
        ll_registry, ll_lat, ll_err = self.fetch_litellm_registry()
        verified_ids, configured_providers = self.fetch_direct_provider_models(settings)

        self.hub_status = {
            "openrouter": {
                "ok": len(or_models) > 0,
                "count": len(or_models),
                "latency_ms": or_lat,
                "error": or_err,
            },
            "litellm": {
                "ok": len(ll_registry) > 0,
                "count": len(ll_registry),
                "latency_ms": ll_lat,
                "error": ll_err,
            },
            "direct_keys": {
                "configured": configured_providers,
                "verified_models": len(verified_ids),
            },
        }

        if not or_models and self.models:
            logger.warning("OpenRouter returned empty; retaining cached models.")
            self._touch_heartbeat()
            return {"ok": False, "retained_cache": True, "hub_status": self.hub_status}

        previous_ids = {m["id"]: m for m in self.models if not m.get("is_batch")}
        normalized: List[Dict[str, Any]] = []
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

        for item in or_models:
            full_id = item.get("id", "")
            if not full_id or "/" not in full_id:
                continue

            provider_slug, raw_model_part = full_id.split("/", 1)
            is_batch = raw_model_part.endswith(":batch")
            is_free_suffix = raw_model_part.endswith(":free")
            native_id = raw_model_part.replace(":batch", "").replace(":free", "")

            pricing = item.get("pricing") or {}
            prompt_per_token = _safe_float(pricing.get("prompt"), 0.0)
            completion_per_token = _safe_float(pricing.get("completion"), 0.0)
            input_cost_1m = round(prompt_per_token * 1_000_000, 4) if prompt_per_token >= 0 else 0.0
            output_cost_1m = round(completion_per_token * 1_000_000, 4) if completion_per_token >= 0 else 0.0
            is_free = is_free_suffix or (input_cost_1m == 0.0 and output_cost_1m == 0.0)

            litellm_id, ll_spec = build_litellm_id(provider_slug, native_id, ll_registry)

            arch = item.get("architecture") or {}
            in_mods = arch.get("input_modalities") or ll_spec.get("supported_modalities") or ["text"]
            out_mods = arch.get("output_modalities") or ll_spec.get("supported_output_modalities") or ["text"]

            sup_params = item.get("supported_parameters") or []
            has_reasoning = bool(
                item.get("reasoning")
                or "reasoning" in sup_params
                or "include_reasoning" in sup_params
                or ll_spec.get("supports_reasoning")
            )
            supports_tools = bool(
                "tools" in sup_params
                or "tool_choice" in sup_params
                or ll_spec.get("supports_function_calling")
            )
            supports_vision = bool("image" in in_mods or ll_spec.get("supports_vision"))

            expiration_date = item.get("expiration_date") or ll_spec.get("deprecation_date")
            status = "active"
            if expiration_date:
                if str(expiration_date) <= today_str:
                    status = "deprecated"
                else:
                    status = "expiring_soon"

            p_meta = PROVIDER_META_MAP.get(
                provider_slug,
                {
                    "slug": provider_slug,
                    "name": provider_slug.replace("-", " ").title(),
                    "icon": "🤖",
                    "env_var": f"{provider_slug.upper().replace('-', '_')}_MODEL",
                },
            )

            created_ts = int(item.get("created") or 0)
            tier = classify_model_tier(native_id, item.get("name", ""), is_free, has_reasoning)

            top_prov = item.get("top_provider") or {}
            max_out = (
                top_prov.get("max_completion_tokens")
                or ll_spec.get("max_output_tokens")
                or 0
            )

            normalized.append(
                {
                    "id": full_id,
                    "openrouter_id": full_id,
                    "native_id": native_id,
                    "litellm_id": litellm_id,
                    "name": item.get("name") or native_id,
                    "provider": provider_slug,
                    "provider_name": p_meta["name"],
                    "provider_icon": p_meta["icon"],
                    "env_var": p_meta["env_var"],
                    "created_ts": created_ts,
                    "created_date": _format_timestamp(created_ts),
                    "knowledge_cutoff": item.get("knowledge_cutoff") or "-",
                    "expiration_date": expiration_date or None,
                    "status": status,
                    "tier": tier,
                    "is_batch": is_batch,
                    "is_free": is_free,
                    "context_length": int(item.get("context_length") or ll_spec.get("max_input_tokens") or 0),
                    "max_output_tokens": int(max_out or 0),
                    "input_cost_1m": input_cost_1m,
                    "output_cost_1m": output_cost_1m,
                    "input_modalities": in_mods,
                    "output_modalities": out_mods,
                    "supports_vision": supports_vision,
                    "supports_tools": supports_tools,
                    "supports_reasoning": has_reasoning,
                    "in_litellm": bool(ll_spec),
                    "verified_direct": native_id in verified_ids or bool(settings.get("OPENROUTER_API_KEY")),
                    "description": (item.get("description") or "")[:280],
                }
            )

        # Sort by created_ts descending, then provider
        normalized.sort(key=lambda x: (x["created_ts"], x["id"]), reverse=True)

        # Detect changes (excluding :batch models for clean diffs)
        current_non_batch = {m["id"]: m for m in normalized if not m["is_batch"]}
        changes = self._detect_and_record_changes(previous_ids, current_non_batch, save_state=save_state)

        self.models = normalized
        now_kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        self.last_sync_ts = time.time()
        self.last_sync_iso = now_kst.strftime("%Y-%m-%d %H:%M:%S KST")

        if save_state:
            self._atomic_write_json(
                STATE_FILE,
                {
                    "last_sync_ts": self.last_sync_ts,
                    "last_sync_iso": self.last_sync_iso,
                    "hub_status": self.hub_status,
                    "models": self.models,
                },
            )
        self._touch_heartbeat()
        return {
            "ok": True,
            "last_sync_iso": self.last_sync_iso,
            "total_models": len([m for m in self.models if not m["is_batch"]]),
            "hub_status": self.hub_status,
            "changes": changes,
        }

    def _detect_and_record_changes(
        self,
        prev_map: Dict[str, Dict[str, Any]],
        curr_map: Dict[str, Dict[str, Any]],
        save_state: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not prev_map:
            return {"added": [], "removed": [], "expiring": []}

        added_ids = set(curr_map.keys()) - set(prev_map.keys())
        removed_ids = set(prev_map.keys()) - set(curr_map.keys())

        added = [curr_map[i] for i in sorted(added_ids)]
        removed = [prev_map[i] for i in sorted(removed_ids)]
        expiring = [
            m
            for m in curr_map.values()
            if m.get("status") in ("expiring_soon", "deprecated")
            and prev_map.get(m["id"], {}).get("status") == "active"
        ]

        if (added or removed or expiring) and save_state:
            history: List[Dict[str, Any]] = []
            if CHANGELOG_FILE.exists():
                try:
                    history = json.loads(CHANGELOG_FILE.read_text(encoding="utf-8"))
                except Exception:
                    history = []
            now_kst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            entry = {
                "timestamp": now_kst,
                "added": [{"id": m["id"], "native_id": m["native_id"], "name": m["name"], "provider": m["provider"]} for m in added],
                "removed": [{"id": m["id"], "native_id": m["native_id"], "name": m["name"], "provider": m["provider"]} for m in removed],
                "expiring": [
                    {
                        "id": m["id"],
                        "native_id": m["native_id"],
                        "expiration_date": m.get("expiration_date"),
                    }
                    for m in expiring
                ],
            }
            history.insert(0, entry)
            self._atomic_write_json(CHANGELOG_FILE, history[:100])

        return {"added": added, "removed": removed, "expiring": expiring}

    def get_models(
        self,
        provider: Optional[str] = None,
        tier: Optional[str] = None,
        modality: Optional[str] = None,
        search: Optional[str] = None,
        exclude_batch: bool = True,
        active_only: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self.models:
            self.sync()

        results = self.models
        if exclude_batch:
            results = [m for m in results if not m.get("is_batch")]
        if active_only:
            results = [m for m in results if m.get("status") == "active"]
        if provider and provider.lower() != "all":
            p_low = provider.lower()
            results = [m for m in results if m["provider"].lower() == p_low]
        if tier and tier.lower() != "all":
            t_low = tier.lower()
            if t_low == "free":
                results = [m for m in results if m.get("is_free")]
            elif t_low == "reasoning":
                results = [m for m in results if m.get("supports_reasoning")]
            else:
                results = [m for m in results if m.get("tier") == t_low]
        if modality and modality.lower() != "all":
            mod_low = modality.lower()
            results = [m for m in results if mod_low in (m.get("input_modalities") or [])]
        if search:
            q = search.lower().strip()
            results = [
                m
                for m in results
                if q in m["id"].lower()
                or q in m["native_id"].lower()
                or q in m["name"].lower()
                or q in m["provider_name"].lower()
            ]
        return results

    def _is_general_chat_model(self, m: Dict[str, Any]) -> bool:
        """Exclude specialized image-gen, safety-guard, audio-only, or embedding models from primary LLM picks."""
        nid = m["native_id"].lower()
        specialized_keywords = [
            "banana",
            "guard",
            "embed",
            "whisper",
            "tts",
            "moderation",
            "imagen",
            "dall-e",
            "audio",
            "realtime",
            "codex",
            "build-",
        ]
        if any(k in nid for k in specialized_keywords):
            return False
        out_mods = m.get("output_modalities") or ["text"]
        if "image" in out_mods and len(out_mods) == 1:
            return False
        return True

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """
        Return smart per-provider recommendations (Flagship, Fast/Cost-Effective, Reasoning, Free)
        with ready-to-copy Native ID & OpenRouter ID for other bots.
        """
        if not self.models:
            self.sync()

        active_models = [
            m for m in self.models if not m.get("is_batch") and m.get("status") == "active"
        ]
        recs: List[Dict[str, Any]] = []

        for p_info in MAJOR_PROVIDERS:
            slug = p_info["slug"]
            p_models = [m for m in active_models if m["provider"] == slug]
            if not p_models:
                continue

            # Sort newest first
            p_models.sort(key=lambda x: x["created_ts"], reverse=True)
            chat_Pool = [m for m in p_models if self._is_general_chat_model(m)] or p_models

            flagship = next((m for m in chat_Pool if m["tier"] == "flagship"), chat_Pool[0])
            fast = next((m for m in chat_Pool if m["tier"] == "fast"), flagship)
            reasoning = next((m for m in chat_Pool if m.get("supports_reasoning")), flagship)
            free_mod = next((m for m in p_models if m.get("is_free")), None)

            recs.append(
                {
                    "provider": slug,
                    "provider_name": p_info["name"],
                    "icon": p_info["icon"],
                    "env_var": p_info["env_var"],
                    "total_active": len(p_models),
                    "flagship": flagship,
                    "fast": fast,
                    "reasoning": reasoning,
                    "free": free_mod,
                    "top_models": chat_Pool[:6],
                    "all_models": p_models,
                }
            )
        return recs

    def resolve_best_model(self, provider: str, tier: str = "fast") -> Optional[Dict[str, Any]]:
        """Resolve the single best current model for a given provider and tier."""
        alias_map = {
            "gemini": "google",
            "google": "google",
            "gpt": "openai",
            "openai": "openai",
            "claude": "anthropic",
            "anthropic": "anthropic",
            "deepseek": "deepseek",
            "grok": "x-ai",
            "xai": "x-ai",
            "x-ai": "x-ai",
            "llama": "meta-llama",
            "meta": "meta-llama",
            "meta-llama": "meta-llama",
            "qwen": "qwen",
            "mistral": "mistralai",
            "mistralai": "mistralai",
        }
        target_slug = alias_map.get(provider.lower().strip(), provider.lower().strip())
        models = self.get_models(provider=target_slug, exclude_batch=True, active_only=True)
        if not models:
            return None

        models.sort(key=lambda x: x["created_ts"], reverse=True)
        chat_pool = [m for m in models if self._is_general_chat_model(m)] or models
        tier_low = tier.lower().strip()
        if tier_low == "fast":
            match = next((m for m in chat_pool if m["tier"] == "fast"), chat_pool[0])
        elif tier_low == "flagship":
            match = next((m for m in chat_pool if m["tier"] == "flagship"), chat_pool[0])
        elif tier_low == "reasoning":
            match = next((m for m in chat_pool if m.get("supports_reasoning")), chat_pool[0])
        elif tier_low == "free":
            match = next((m for m in models if m.get("is_free")), chat_pool[0])
        else:
            match = chat_pool[0]
        return match
