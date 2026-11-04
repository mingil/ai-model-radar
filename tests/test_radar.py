"""
Unit tests for AI Model Radar aggregator, classifier, verifier, and FastAPI endpoints.
"""
from fastapi.testclient import TestClient
from src.aggregator import ModelAggregator, build_litellm_id, classify_model_tier
from src.app import app, aggregator


def test_classify_model_tier():
    assert classify_model_tier("gemini-3.8-flash", "Gemini 3.8 Flash", False, True) == "fast"
    assert classify_model_tier("gemini-4-argon", "Gemini 4 Argon", False, True) == "flagship"
    assert classify_model_tier("deepseek-r1", "DeepSeek R1", False, True) == "reasoning"
    assert classify_model_tier("llama-4-scout:free", "Llama 4 Scout", True, False) == "free"


def test_build_litellm_id():
    registry = {
        "gemini-3.8-flash": {"max_input_tokens": 1048576, "supports_vision": True},
        "anthropic/claude-sonnet-5.5": {"max_input_tokens": 200000},
    }
    lid, spec = build_litellm_id("google", "gemini-3.8-flash", registry)
    assert lid == "gemini-3.8-flash"
    assert spec["supports_vision"] is True

    lid2, spec2 = build_litellm_id("anthropic", "claude-sonnet-5.5", registry)
    assert lid2 == "anthropic/claude-sonnet-5.5"
    assert spec2["max_input_tokens"] == 200000


def test_aggregator_mock_sync(monkeypatch, tmp_path):
    agg = ModelAggregator()
    sample_or = [
        {
            "id": "google/gemini-3.8-flash",
            "name": "Google: Gemini 3.8 Flash",
            "created": 1756800000,
            "context_length": 1048576,
            "pricing": {"prompt": "0.000000375", "completion": "0.000001875"},
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            "supported_parameters": ["tools", "reasoning"],
        },
        {
            "id": "google/gemini-4-argon",
            "name": "Google: Gemini 4 Argon",
            "created": 1759000000,
            "context_length": 2097152,
            "pricing": {"prompt": "0.00000125", "completion": "0.000005"},
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            "supported_parameters": ["tools", "reasoning"],
        },
        {
            "id": "openai/gpt-6.1-terra",
            "name": "OpenAI: GPT-6.1 Terra",
            "created": 1759500000,
            "context_length": 400000,
            "pricing": {"prompt": "0.000002", "completion": "0.000008"},
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
            "supported_parameters": ["tools"],
        },
    ]
    sample_ll = {
        "gemini-3.8-flash": {"max_output_tokens": 65536, "supports_vision": True}
    }

    monkeypatch.setattr(agg, "fetch_openrouter_models", lambda api_key="": (sample_or, 120, None))
    monkeypatch.setattr(agg, "fetch_litellm_registry", lambda: (sample_ll, 95, None))
    monkeypatch.setattr(agg, "fetch_direct_provider_models", lambda s: (set(), []))

    res = agg.sync(save_state=False)
    assert res["ok"] is True
    assert res["total_models"] == 3

    fast_google = agg.resolve_best_model("google", tier="fast")
    assert fast_google is not None
    assert fast_google["native_id"] == "gemini-3.8-flash"

    flag_google = agg.resolve_best_model("google", tier="flagship")
    assert flag_google is not None
    assert flag_google["native_id"] == "gemini-4-argon"


def test_fastapi_endpoints(monkeypatch):
    # Populate aggregator with mock models if empty
    if not aggregator.models:
        aggregator.models = [
            {
                "id": "google/gemini-3.8-flash",
                "openrouter_id": "google/gemini-3.8-flash",
                "native_id": "gemini-3.8-flash",
                "litellm_id": "gemini/gemini-3.8-flash",
                "name": "Google: Gemini 3.8 Flash",
                "provider": "google",
                "provider_name": "Google Gemini",
                "provider_icon": "💎",
                "env_var": "GEMINI_MODEL",
                "created_ts": 1756800000,
                "created_date": "2026-09-02",
                "knowledge_cutoff": "2026-03",
                "expiration_date": None,
                "status": "active",
                "tier": "fast",
                "is_batch": False,
                "is_free": False,
                "context_length": 1048576,
                "max_output_tokens": 65536,
                "input_cost_1m": 0.375,
                "output_cost_1m": 1.875,
                "input_modalities": ["text", "image"],
                "output_modalities": ["text"],
                "supports_vision": True,
                "supports_tools": True,
                "supports_reasoning": True,
                "in_litellm": True,
                "verified_direct": False,
                "description": "Fast multimodal model",
            }
        ]
        aggregator.last_sync_iso = "2026-11-04 13:20:00 KST"

    client = TestClient(app)
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "healthy"

    # Unauthenticated call to /api/status must return 401
    r_unauth = client.get("/api/status")
    assert r_unauth.status_code == 401

    # Authenticate via /api/auth/login
    from src.config import get_allowed_passwords
    valid_pw = get_allowed_passwords()[0]
    r_login = client.post("/api/auth/login", json={"password": valid_pw})
    assert r_login.status_code == 200
    token = r_login.json()["token"]

    r_status = client.get("/api/status", headers={"X-Radar-Token": token})
    assert r_status.status_code == 200
    assert r_status.json()["ok"] is True

    r_recs = client.get("/api/recommendations", headers={"X-Radar-Token": token})
    assert r_recs.status_code == 200
    recs_list = r_recs.json()["recommendations"]
    assert len(recs_list) >= 1
    assert "all_models" in recs_list[0]

    r_resolve = client.get("/api/resolve/google?tier=fast")
    assert r_resolve.status_code == 200
    assert r_resolve.json()["native_id"] != ""
