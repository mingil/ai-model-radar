"""
AI Model Radar — All-in-One FastAPI Server, Background Scheduler, Telegram Bot & CLI.
"""
import argparse
import json
import logging
import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from src.aggregator import ModelAggregator
from src.config import (
    CHANGELOG_FILE,
    LOG_DIR,
    create_auth_token,
    load_runtime_settings,
    save_runtime_settings,
    verify_auth_token,
    verify_password,
)
from src.dashboard_html import DASHBOARD_HTML
from src.telegram_bot import (
    TelegramBotWorker,
    build_change_alert_message,
    build_provider_message,
    build_summary_message,
    send_telegram_message,
)
from src.verifier import check_configured_keys_status, ping_model_with_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "ai_model_radar.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("ai_model_radar")

aggregator = ModelAggregator()
tg_worker = TelegramBotWorker(aggregator)
_scheduler_stop = threading.Event()


def _periodic_sync_loop() -> None:
    """Background thread that periodically syncs models and sends Telegram change alerts."""
    while not _scheduler_stop.is_set():
        settings = load_runtime_settings()
        interval_hours = max(0.5, float(settings.get("SCAN_INTERVAL_HOURS", 6)))
        try:
            res = aggregator.sync()
            changes = res.get("changes") or {}
            if settings.get("ALERT_ON_NEW_MODEL") or settings.get("ALERT_ON_DEPRECATED"):
                alert_msg = build_change_alert_message(changes)
                if alert_msg:
                    send_telegram_message(alert_msg)
        except Exception as e:
            logger.error("Periodic sync error: %s", e)

        _scheduler_stop.wait(interval_hours * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not aggregator.models:
        aggregator.sync()
    sync_thread = threading.Thread(target=_periodic_sync_loop, daemon=True)
    sync_thread.start()
    tg_worker.start()
    yield
    _scheduler_stop.set()
    tg_worker.stop()


app = FastAPI(
    title="AI Model Radar API",
    description="실시간 AI 모델 가용성 조회·검증·추천 통합 허브 (OpenRouter + LiteLLM + Direct Keys)",
    version="1.1.0",
    lifespan=lifespan,
)


class LoginRequest(BaseModel):
    password: str


class PingRequest(BaseModel):
    model_id: str
    native_id: Optional[str] = ""
    provider: Optional[str] = ""


def require_auth(
    request: Request,
    x_radar_token: Optional[str] = Header(default=None),
) -> bool:
    """Verify password-based session token from X-Radar-Token header or radar_auth cookie."""
    token = x_radar_token or request.cookies.get("radar_auth", "")
    if verify_auth_token(token):
        return True
    raise HTTPException(status_code=401, detail="비밀번호 인증이 필요합니다.")


@app.get("/", response_class=HTMLResponse)
def read_dashboard() -> str:
    return DASHBOARD_HTML


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "last_sync_iso": aggregator.last_sync_iso,
        "models_cached": len(aggregator.models),
    }


@app.post("/api/auth/login")
def api_login(req: LoginRequest, response: Response) -> Dict[str, Any]:
    if not verify_password(req.password):
        raise HTTPException(status_code=401, detail="비밀번호가 일치하지 않습니다.")
    token = create_auth_token()
    response.set_cookie(
        key="radar_auth",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=False,
        samesite="lax",
    )
    return {"ok": True, "token": token}


@app.get("/api/auth/check")
def api_auth_check(
    request: Request,
    x_radar_token: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    token = x_radar_token or request.cookies.get("radar_auth", "")
    return {"authenticated": verify_auth_token(token)}


@app.get("/api/status", dependencies=[Depends(require_auth)])
def api_status() -> Dict[str, Any]:
    if not aggregator.models:
        aggregator.sync()
    non_batch = [m for m in aggregator.models if not m.get("is_batch")]
    active = [m for m in non_batch if m.get("status") == "active"]
    free_models = [m for m in active if m.get("is_free")]
    return {
        "ok": True,
        "last_sync_iso": aggregator.last_sync_iso,
        "last_sync_ts": aggregator.last_sync_ts,
        "total_models": len(non_batch),
        "total_active_models": len(active),
        "free_models_count": len(free_models),
        "hub_status": aggregator.hub_status,
        "keys_status": check_configured_keys_status(),
    }


@app.get("/api/models", dependencies=[Depends(require_auth)])
def api_models(
    provider: str = Query("all", description="Provider slug (e.g. google, openai, anthropic, deepseek)"),
    tier: str = Query("all", description="Tier filter (flagship, fast, reasoning, free)"),
    modality: str = Query("all", description="Modality filter (text, image, audio)"),
    search: str = Query("", description="Keyword search"),
    exclude_batch: bool = Query(True, description="Exclude :batch duplicate variants"),
    active_only: bool = Query(False, description="Only active non-deprecated models"),
) -> Dict[str, Any]:
    items = aggregator.get_models(
        provider=provider,
        tier=tier,
        modality=modality,
        search=search,
        exclude_batch=exclude_batch,
        active_only=active_only,
    )
    return {"count": len(items), "models": items}


@app.get("/api/recommendations", dependencies=[Depends(require_auth)])
def api_recommendations() -> Dict[str, Any]:
    recs = aggregator.get_recommendations()
    return {"last_sync_iso": aggregator.last_sync_iso, "recommendations": recs}


@app.get("/api/resolve/{provider}")
def api_resolve_provider(
    provider: str,
    tier: str = Query("fast", description="fast | flagship | reasoning | free"),
) -> Dict[str, Any]:
    """
    Endpoint for other Docker containers/bots to dynamically fetch the best current model ID.
    Example: GET /api/resolve/google?tier=fast -> returns gemini-3.8-flash
    """
    best = aggregator.resolve_best_model(provider=provider, tier=tier)
    if not best:
        raise HTTPException(status_code=404, detail=f"No active model found for provider '{provider}'")
    return {
        "ok": True,
        "provider": best["provider"],
        "provider_name": best["provider_name"],
        "requested_tier": tier,
        "native_id": best["native_id"],
        "openrouter_id": best["openrouter_id"],
        "litellm_id": best["litellm_id"],
        "env_var": best["env_var"],
        "env_snippet": f"{best['env_var']}={best['native_id']}",
        "context_length": best["context_length"],
        "input_cost_1m": best["input_cost_1m"],
        "output_cost_1m": best["output_cost_1m"],
        "created_date": best["created_date"],
    }


@app.get("/api/changes", dependencies=[Depends(require_auth)])
def api_changes() -> Dict[str, Any]:
    history = []
    if CHANGELOG_FILE.exists():
        try:
            history = json.loads(CHANGELOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            history = []
    return {"changelog": history}


@app.post("/api/sync", dependencies=[Depends(require_auth)])
def api_sync() -> Dict[str, Any]:
    return aggregator.sync()


@app.post("/api/ping", dependencies=[Depends(require_auth)])
def api_ping(req: PingRequest) -> Dict[str, Any]:
    return ping_model_with_key(
        model_id=req.model_id,
        native_id=req.native_id or "",
        provider=req.provider or "",
    )


@app.post("/api/settings", dependencies=[Depends(require_auth)])
def api_save_settings(payload: Dict[str, Any], response: Response) -> Dict[str, Any]:
    updated = save_runtime_settings(payload)
    new_token = create_auth_token()
    response.set_cookie(
        key="radar_auth",
        value=new_token,
        max_age=30 * 24 * 3600,
        httponly=False,
        samesite="lax",
    )
    return {
        "ok": True,
        "token": new_token,
        "keys_status": check_configured_keys_status(),
        "scan_interval": updated.get("SCAN_INTERVAL_HOURS"),
    }


@app.post("/api/telegram/test", dependencies=[Depends(require_auth)])
def api_telegram_test() -> Dict[str, Any]:
    msg = build_summary_message(aggregator)
    sent = send_telegram_message(msg)
    return {"ok": sent}


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="AI Model Radar CLI & Server")
    parser.add_argument("--once", action="store_true", help="Run a single model sync and print summary")
    parser.add_argument("--status", action="store_true", help="Show current cached model status and recommendations")
    parser.add_argument("--provider", type=str, help="List active models for a specific provider (e.g. google, openai, claude)")
    parser.add_argument("--dry-run", action="store_true", help="Test hub connectivity without saving state")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8500")), help="Web server port (default 8500)")
    args = parser.parse_args()

    if args.dry_run:
        res = aggregator.sync(save_state=False)
        print(f"[DRY-RUN] Sync OK={res.get('ok')} | Active Models={res.get('total_models')} | Hubs={res.get('hub_status')}")
        return

    if args.once:
        res = aggregator.sync(save_state=True)
        print(f"✅ 동기화 완료 ({res.get('last_sync_iso')}) — 총 {res.get('total_models')}개 활성 모델")
        for r in aggregator.get_recommendations():
            print(
                f"  {r['icon']} {r['provider_name']}: "
                f"가성비(Fast)={r['fast']['native_id']} | 주력(Flagship)={r['flagship']['native_id']}"
            )
        return

    if args.status:
        if not aggregator.models:
            aggregator.sync()
        print(f"📡 AI Model Radar 상태 (최근 동기화: {aggregator.last_sync_iso})")
        for r in aggregator.get_recommendations():
            print(
                f"  {r['icon']} {r['provider_name']} (활성 {r['total_active']}종) -> "
                f"{r['env_var']}={r['fast']['native_id']} (주력: {r['flagship']['native_id']})"
            )
        return

    if args.provider:
        if not aggregator.models:
            aggregator.sync()
        msg = build_provider_message(aggregator, args.provider)
        import re
        print(re.sub(r"<[^>]+>", "", msg))
        return

    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    run_cli()
