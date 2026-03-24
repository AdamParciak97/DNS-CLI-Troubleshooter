from __future__ import annotations
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/diagnose")
async def ws_diagnose(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        target = data.get("target", "").strip()
        profile = data.get("profile", "quick")
        use_ai = data.get("use_ai", True)

        if not target:
            await websocket.send_json({"event": "error", "message": "Brak target"})
            return

        from cli_troubleshooter.diagnostics.runner import PROFILES, ALL_CHECKS
        checks_list = PROFILES.get(profile, PROFILES["quick"])

        await websocket.send_json({
            "event": "init",
            "target": target,
            "profile": profile,
            "checks": checks_list,
        })

        results = {}
        sem = asyncio.Semaphore(3)

        async def run_one(name: str):
            check = ALL_CHECKS.get(name)
            if not check:
                return
            await websocket.send_json({"event": "check_start", "check": name})
            async with sem:
                result = await check.run(target)
            results[name] = result.model_dump()
            await websocket.send_json({
                "event": "check_done",
                "check": name,
                "result": result.model_dump(),
            })

        await asyncio.gather(*[run_one(n) for n in checks_list])

        statuses = [r.get("status") for r in results.values()]
        overall = "error" if "error" in statuses else "warning" if "warning" in statuses else "ok"
        diag_data = {"results": results, "overall_status": overall}

        import json as _json
        from cli_troubleshooter.models import DiagnosticRun
        from cli_troubleshooter.storage.repositories import save_run, get_runs
        from cli_troubleshooter.ai.analyzer import analyze_with_claude, rule_based_analyze

        ai_result = {}

        if use_ai:
            await websocket.send_json({"event": "ai_start"})

            prev_runs = get_runs(target=target, limit=4)
            history = [
                {"timestamp": r.timestamp.isoformat(), "status": r.status,
                 "risk_score": r.risk_score, "ai_summary": r.get_ai_summary()}
                for r in prev_runs
            ]

            loop = asyncio.get_event_loop()

            async def stream_ai():
                nonlocal ai_result

                def on_token(text: str):
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({"event": "ai_token", "token": text}),
                        loop
                    )

                try:
                    ai_result = await loop.run_in_executor(
                        None,
                        lambda: analyze_with_claude(target, profile, diag_data, history, on_token)
                    )
                except Exception:
                    ai_result = rule_based_analyze(target, profile, diag_data, history)

            await stream_ai()
            await websocket.send_json({"event": "ai_done", "ai_summary": ai_result})

        # Zawsze zapisuj run do bazy
        run_record = DiagnosticRun(
            target=target, profile=profile,
            risk_score=ai_result.get("risk_score", 0),
            status=overall,
            analyzer=ai_result.get("analyzer", "none"),
            checks_run=_json.dumps(checks_list),
            results_json=_json.dumps(results),
            ai_summary_json=_json.dumps(ai_result),
        )
        saved = save_run(run_record)
        await websocket.send_json({"event": "saved", "run_id": saved.id})

        await websocket.send_json({"event": "complete", "overall_status": overall})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except Exception:
            pass
