from __future__ import annotations
import asyncio
import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from cli_troubleshooter.models import CheckResult, AISummary, DiagnosticRun
from cli_troubleshooter.diagnostics.checks.ping import PingCheck
from cli_troubleshooter.diagnostics.checks.dns import DnsCheck
from cli_troubleshooter.diagnostics.checks.http import HttpCheck
from cli_troubleshooter.diagnostics.checks.ssl import SslCheck
from cli_troubleshooter.diagnostics.checks.ports import PortsCheck
from cli_troubleshooter.diagnostics.checks.traceroute import TracerouteCheck
from cli_troubleshooter.diagnostics.checks.interfaces import InterfacesCheck

PROFILES = {
    "quick": ["interfaces", "dns", "ping", "http"],
    "full": ["interfaces", "dns", "ping", "traceroute", "ports", "http", "ssl"],
    "web": ["dns", "ping", "http", "ssl", "ports"],
    "connectivity": ["interfaces", "dns", "ping", "traceroute"],
}

ALL_CHECKS = {
    "ping": PingCheck(),
    "dns": DnsCheck(),
    "http": HttpCheck(),
    "ssl": SslCheck(),
    "ports": PortsCheck(),
    "traceroute": TracerouteCheck(),
    "interfaces": InterfacesCheck(),
}


async def run_diagnostics(
    target: str,
    profile: str = "quick",
    checks: Optional[List[str]] = None,
    on_check_start: Optional[Callable[[str], None]] = None,
    on_check_done: Optional[Callable[[str, CheckResult], None]] = None,
    sem_limit: int = 5,
) -> Dict[str, Any]:
    check_names = checks or PROFILES.get(profile, PROFILES["quick"])
    sem = asyncio.Semaphore(sem_limit)
    results: Dict[str, CheckResult] = {}
    start = time.perf_counter()

    async def run_one(name: str):
        check = ALL_CHECKS.get(name)
        if not check:
            results[name] = CheckResult(
                check_name=name, target=target, status="skipped",
                summary=f"Nieznany check: {name}"
            )
            return
        if on_check_start:
            on_check_start(name)
        async with sem:
            result = await check.run(target)
        results[name] = result
        if on_check_done:
            on_check_done(name, result)

    await asyncio.gather(*[run_one(n) for n in check_names])

    total_duration = time.perf_counter() - start
    statuses = [r.status for r in results.values()]
    if "error" in statuses:
        overall = "error"
    elif "warning" in statuses:
        overall = "warning"
    else:
        overall = "ok"

    return {
        "target": target,
        "profile": profile,
        "checks_run": check_names,
        "results": {n: r.model_dump() for n, r in results.items()},
        "overall_status": overall,
        "duration_s": round(total_duration, 2),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
