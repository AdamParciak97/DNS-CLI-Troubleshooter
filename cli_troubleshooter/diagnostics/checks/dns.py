from __future__ import annotations
import asyncio
import time
from typing import List, Dict, Any
import dns.resolver
import dns.exception
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult

RESOLVERS = {
    "Google": "8.8.8.8",
    "Cloudflare": "1.1.1.1",
    "Quad9": "9.9.9.9",
    "System": None,
}

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]

class DnsCheck(BaseCheck):
    name = "dns"
    description = "Diagnostyka DNS - rekordy, propagacja, spójność"
    timeout = 15

    async def run(self, target: str, **kwargs) -> CheckResult:
        start = time.perf_counter()
        # Strip protocol if present
        host = target
        if "://" in target:
            from urllib.parse import urlparse
            host = urlparse(target).hostname or target

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _resolve_all, host)

            a_records = data.get("records", {}).get("A", [])
            has_a = bool(a_records)
            consistency = data.get("resolver_consistency", True)

            if not has_a:
                status = "error"
                summary = f"Brak rekordów A dla {host}"
            elif not consistency:
                status = "warning"
                summary = f"Niespójność DNS między resolverami dla {host}"
            else:
                status = "ok"
                ips = ", ".join(a_records[:3])
                summary = f"Rozwiązano: {ips}"

            return CheckResult(
                check_name=self.name, target=host, status=status,
                duration_s=time.perf_counter() - start, data=data, summary=summary
            )
        except Exception as e:
            return CheckResult(
                check_name=self.name, target=host, status="error",
                duration_s=time.perf_counter() - start, error=str(e),
                summary=f"Błąd DNS: {e}"
            )


def _resolve_all(host: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {"records": {}, "resolver_results": {}, "resolver_consistency": True}

    # Resolve all record types with default resolver
    for rtype in RECORD_TYPES:
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 5
            resolver.lifetime = 5
            answers = resolver.resolve(host, rtype)
            data["records"][rtype] = [str(r) for r in answers]
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
            data["records"][rtype] = []
        except Exception:
            data["records"][rtype] = []

    # Check consistency across resolvers for A records
    a_results = {}
    for name, server in RESOLVERS.items():
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = 3
            resolver.lifetime = 3
            if server:
                resolver.nameservers = [server]
            answers = resolver.resolve(host, "A")
            ips = sorted([str(r) for r in answers])
            a_results[name] = ips
        except Exception as e:
            a_results[name] = []

    data["resolver_results"] = a_results
    all_results = [tuple(v) for v in a_results.values() if v]
    data["resolver_consistency"] = len(set(all_results)) <= 1 if all_results else True
    return data
