from __future__ import annotations
import asyncio
import platform
import re
import time
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult


class TracerouteCheck(BaseCheck):
    name = "traceroute"
    description = "Traceroute - ścieżka routingu z geolokalizacją"
    timeout = 60

    async def run(self, target: str, max_hops: int = 20, **kwargs) -> CheckResult:
        start = time.perf_counter()
        host = target
        if "://" in target:
            from urllib.parse import urlparse
            host = urlparse(target).hostname or target

        try:
            is_win = platform.system() == "Windows"
            if is_win:
                cmd = ["tracert", "-d", "-h", str(max_hops), "-w", "1000", host]
            else:
                cmd = ["traceroute", "-n", "-m", str(max_hops), "-w", "2", host]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return CheckResult(
                    check_name=self.name, target=host, status="timeout",
                    duration_s=time.perf_counter() - start,
                    summary="Traceroute timeout"
                )

            output = stdout.decode(errors="replace")
            hops = _parse_traceroute(output, is_win)
            hop_count = len([h for h in hops if h.get("ip")])

            # Geolocation for IPs
            ips = [h["ip"] for h in hops if h.get("ip")]
            geo_map = await _geolocate_ips(ips)
            for h in hops:
                if h.get("ip") and h["ip"] in geo_map:
                    h["geo"] = geo_map[h["ip"]]

            if hop_count == 0:
                status = "error"
                summary = "Brak hopów - ścieżka niedostępna"
            elif hop_count < 3:
                status = "warning"
                summary = f"Tylko {hop_count} hop(ów)"
            else:
                status = "ok"
                summary = f"Trasa: {hop_count} hopów"

            return CheckResult(
                check_name=self.name, target=host, status=status,
                duration_s=time.perf_counter() - start,
                data={"hops": hops, "hop_count": hop_count},
                summary=summary
            )
        except FileNotFoundError:
            return CheckResult(
                check_name=self.name, target=host, status="skipped",
                duration_s=time.perf_counter() - start,
                summary="traceroute/tracert niedostępny", error="command not found"
            )
        except Exception as e:
            return CheckResult(
                check_name=self.name, target=host, status="error",
                duration_s=time.perf_counter() - start, error=str(e),
                summary=f"Błąd traceroute: {e}"
            )


async def _geolocate_ips(ips: list) -> dict:
    """Batch geolocation via ip-api.com (free, no key needed, max 100/batch)."""
    if not ips:
        return {}
    # Filter out private IPs
    public_ips = [ip for ip in ips if not _is_private(ip)]
    if not public_ips:
        return {}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "http://ip-api.com/batch",
                json=[{"query": ip, "fields": "query,country,city,lat,lon,org,as"} for ip in public_ips[:15]],
            )
            if resp.status_code == 200:
                return {item["query"]: item for item in resp.json() if item.get("query")}
    except Exception:
        pass
    return {}


def _is_private(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return True
    try:
        a, b = int(parts[0]), int(parts[1])
        return (a == 10 or (a == 172 and 16 <= b <= 31) or (a == 192 and b == 168)
                or a == 127 or a == 169)
    except Exception:
        return True


def _parse_traceroute(output: str, is_win: bool) -> list:
    hops = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        if is_win:
            m = re.match(r"\s*(\d+)\s+(?:([\d.]+)\s+ms\s+([\d.]+)\s+ms\s+([\d.]+)\s+ms\s+)?([\d.]+|\*)", line)
            if m:
                hop_num = int(m.group(1))
                ip = m.group(5) if m.group(5) != "*" else None
                rtts = [float(m.group(i)) for i in (2, 3, 4) if m.group(i)]
                avg_rtt = sum(rtts) / len(rtts) if rtts else None
                hops.append({"hop": hop_num, "ip": ip, "avg_rtt_ms": avg_rtt})
        else:
            m = re.match(r"\s*(\d+)\s+", line)
            if m:
                hop_num = int(m.group(1))
                ip_m = re.search(r"([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3})", line)
                ip = ip_m.group(1) if ip_m else None
                rtts = [float(x) for x in re.findall(r"([\d.]+)\s+ms", line)]
                avg_rtt = sum(rtts) / len(rtts) if rtts else None
                hops.append({"hop": hop_num, "ip": ip, "avg_rtt_ms": avg_rtt})
    return hops
