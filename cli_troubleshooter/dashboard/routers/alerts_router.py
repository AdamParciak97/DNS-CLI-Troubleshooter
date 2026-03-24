from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["alerts"])

@router.get("/alerts")
async def get_alerts(status: Optional[str] = None, limit: int = 50):
    from cli_troubleshooter.storage.repositories import get_alerts
    items = get_alerts(status=status, limit=limit)
    return {"items": [
        {
            "id": a.id,
            "target": a.target,
            "severity": a.severity,
            "title": a.title,
            "description": a.description,
            "timestamp": a.timestamp.isoformat() + "Z",
            "acknowledged": a.acknowledged,
        }
        for a in items
    ]}

@router.patch("/alerts/{alert_id}/ack")
async def ack_alert(alert_id: int):
    from cli_troubleshooter.storage.repositories import ack_alert as _ack
    if not _ack(alert_id):
        raise HTTPException(status_code=404, detail="Alert nie znaleziony")
    return {"ok": True}
