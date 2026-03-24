from __future__ import annotations
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response

router = APIRouter(tags=["export"])

@router.get("/export/{run_id}/json")
async def export_json(run_id: int):
    from cli_troubleshooter.storage.repositories import get_run
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run nie znaleziony")
    data = {
        "id": run.id,
        "target": run.target,
        "profile": run.profile,
        "timestamp": run.timestamp.isoformat() + "Z",
        "status": run.status,
        "risk_score": run.risk_score,
        "duration_s": run.duration_s,
        "checks_run": run.get_checks_run(),
        "results": run.get_results(),
        "ai_summary": run.get_ai_summary(),
    }
    return Response(
        content=json.dumps(data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=run_{run_id}.json"}
    )

@router.get("/export/{run_id}/html", response_class=HTMLResponse)
async def export_html(run_id: int):
    from cli_troubleshooter.storage.repositories import get_run
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run nie znaleziony")
    results = run.get_results()
    ai = run.get_ai_summary()

    rows = ""
    for name, r in results.items():
        status = r.get("status", "unknown")
        colors = {"ok": "#22c55e", "warning": "#eab308", "error": "#ef4444", "timeout": "#ef4444", "skipped": "#9ca3af"}
        color = colors.get(status, "#9ca3af")
        rows += f'<tr><td><b>{name}</b></td><td style="color:{color}">{status}</td><td>{r.get("duration_s",0):.1f}s</td><td>{r.get("summary","")}</td></tr>'

    risk = run.risk_score
    risk_color = "#22c55e" if risk < 30 else "#eab308" if risk < 60 else "#ef4444"
    ai_text = ai.get("raw_text", "").replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="pl">
<head><meta charset="UTF-8"><title>Raport diagnostyczny - {run.target}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; color: #1f2937; }}
  h1 {{ color: #0891b2; }} h2 {{ color: #374151; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  th, td {{ padding: 10px 12px; text-align: left; border: 1px solid #e5e7eb; }}
  th {{ background: #f9fafb; font-weight: 600; }}
  .meta {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .meta-item {{ background: #f9fafb; padding: 12px; border-radius: 8px; border: 1px solid #e5e7eb; }}
  .meta-label {{ font-size: 12px; color: #6b7280; }}
  .meta-value {{ font-size: 18px; font-weight: bold; margin-top: 4px; }}
  .ai-box {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 20px; margin-top: 24px; }}
  @media print {{ body {{ margin: 20px; }} }}
</style>
</head>
<body>
<h1>🔍 Raport diagnostyczny</h1>
<div class="meta">
  <div class="meta-item"><div class="meta-label">Target</div><div class="meta-value" style="font-size:14px">{run.target}</div></div>
  <div class="meta-item"><div class="meta-label">Profil</div><div class="meta-value" style="font-size:14px">{run.profile}</div></div>
  <div class="meta-item"><div class="meta-label">Status</div><div class="meta-value" style="font-size:14px">{run.status}</div></div>
  <div class="meta-item"><div class="meta-label">Ryzyko</div><div class="meta-value" style="color:{risk_color}">{risk}/100</div></div>
</div>
<p style="color:#6b7280;font-size:13px">Wygenerowano: {run.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} | Czas trwania: {run.duration_s:.1f}s | Analizator: {run.analyzer}</p>

<h2>Wyniki checków</h2>
<table><thead><tr><th>Check</th><th>Status</th><th>Czas</th><th>Podsumowanie</th></tr></thead>
<tbody>{rows}</tbody></table>

<div class="ai-box">
<h2 style="border:none;padding:0;margin-bottom:12px">🤖 AI Summary</h2>
<p>{ai_text}</p>
</div>
<p style="margin-top:32px;font-size:11px;color:#9ca3af;text-align:center">CLI Troubleshooter v1.0.0 — Aby wydrukować jako PDF, użyj Ctrl+P w przeglądarce</p>
</body></html>"""
    return HTMLResponse(content=html, headers={"Content-Disposition": f"inline; filename=run_{run_id}.html"})
