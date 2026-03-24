from __future__ import annotations
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(tags=["diagnostics"])

class RunRequest(BaseModel):
    target: str
    profile: str = "quick"
    checks: Optional[List[str]] = None
    use_ai: bool = True

@router.post("/diagnose")
async def diagnose(payload: RunRequest):
    import asyncio
    from cli_troubleshooter.diagnostics.runner import run_diagnostics
    from cli_troubleshooter.ai.analyzer import analyze_with_claude, rule_based_analyze
    from cli_troubleshooter.models import DiagnosticRun
    from cli_troubleshooter.storage.repositories import save_run

    if not payload.target.strip():
        raise HTTPException(status_code=400, detail="Target jest wymagany")

    diag = await run_diagnostics(
        target=payload.target,
        profile=payload.profile,
        checks=payload.checks,
    )

    ai_result = {}
    if payload.use_ai:
        try:
            ai_result = analyze_with_claude(payload.target, payload.profile, diag)
        except Exception:
            ai_result = rule_based_analyze(payload.target, payload.profile, diag)

    run_record = DiagnosticRun(
        target=payload.target,
        profile=payload.profile,
        duration_s=diag["duration_s"],
        risk_score=ai_result.get("risk_score", 0),
        status=diag["overall_status"],
        analyzer=ai_result.get("analyzer", "none"),
        checks_run=json.dumps(diag["checks_run"]),
        results_json=json.dumps(diag["results"]),
        ai_summary_json=json.dumps(ai_result),
    )
    saved = save_run(run_record)

    return {
        "id": saved.id,
        "target": payload.target,
        "profile": payload.profile,
        "timestamp": saved.timestamp.isoformat() + "Z",
        "overall_status": diag["overall_status"],
        "duration_s": diag["duration_s"],
        "checks_run": diag["checks_run"],
        "results": diag["results"],
        "ai_summary": ai_result,
        "risk_score": ai_result.get("risk_score", 0),
    }
