from __future__ import annotations
import asyncio
import time
from typing import List, Dict, Any
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult

COMMON_PORTS = [21, 22, 25, 53, 80, 443, 465, 587, 993, 995, 3306, 5432, 6379, 8080, 8443]
WEB_PORTS = [80, 443, 8080, 8443]

class PortsCheck(BaseCheck):
    name = "ports"
    description = "Skanowanie portów TCP"
    timeout = 20

    async def run(self, target: str, ports: List[int] = None, **kwargs) -> CheckResult:
        start = time.perf_counter()
        host = target
        if "://" in target:
            from urllib.parse import urlparse
            host = urlparse(target).hostname or target

        scan_ports = ports or WEB_PORTS
        results = await _scan_ports(host, scan_ports, timeout=3)

        open_ports = [r["port"] for r in results if r["open"]]
        closed_ports = [r["port"] for r in results if not r["open"]]

        if not open_ports:
            status = "error"
            summary = f"Wszystkie porty zamknięte: {closed_ports}"
        elif len(closed_ports) > len(open_ports):
            status = "warning"
            summary = f"Otwarte: {open_ports}, Zamknięte: {closed_ports}"
        else:
            status = "ok"
            summary = f"Otwarte porty: {open_ports}"

        return CheckResult(
            check_name=self.name, target=host, status=status,
            duration_s=time.perf_counter() - start,
            data={"ports": results, "open_ports": open_ports, "closed_ports": closed_ports},
            summary=summary
        )


async def _scan_ports(host: str, ports: List[int], timeout: float = 3) -> List[Dict]:
    sem = asyncio.Semaphore(20)

    async def probe(port: int) -> Dict:
        async with sem:
            try:
                fut = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(fut, timeout=timeout)
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass
                return {"port": port, "open": True, "banner": None}
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                return {"port": port, "open": False, "banner": None}

    return await asyncio.gather(*[probe(p) for p in ports])
