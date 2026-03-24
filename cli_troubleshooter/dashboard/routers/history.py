from __future__ import annotations
import json
from typing import Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["history"])

@router.get("/history")
async def get_history(target: Optional[str] = None, limit: int = 50):
    from cli_troubleshooter.storage.repositories import get_runs
    runs = get_runs(target=target, limit=limit)
    items = []
    for r in runs:
        items.append({
            "id": r.id,
            "target": r.target,
            "profile": r.profile,
            "timestamp": r.timestamp.isoformat() + "Z",
            "status": r.status,
            "risk_score": r.risk_score,
            "duration_s": r.duration_s,
            "analyzer": r.analyzer,
            "checks_run": r.get_checks_run(),
        })
    return {"items": items, "total": len(items)}

@router.get("/history/{run_id}")
async def get_run(run_id: int):
    from cli_troubleshooter.storage.repositories import get_run
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run nie znaleziony")
    return {
        "id": run.id,
        "target": run.target,
        "profile": run.profile,
        "timestamp": run.timestamp.isoformat() + "Z",
        "status": run.status,
        "risk_score": run.risk_score,
        "duration_s": run.duration_s,
        "analyzer": run.analyzer,
        "checks_run": run.get_checks_run(),
        "results": run.get_results(),
        "ai_summary": run.get_ai_summary(),
    }

@router.delete("/history/{run_id}")
async def delete_run(run_id: int):
    from cli_troubleshooter.storage.repositories import get_run
    from sqlmodel import Session
    from cli_troubleshooter.storage.db import get_engine
    engine = get_engine()
    with Session(engine) as session:
        from cli_troubleshooter.models import DiagnosticRun
        run = session.get(DiagnosticRun, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run nie znaleziony")
        session.delete(run)
        session.commit()
    return {"ok": True}
