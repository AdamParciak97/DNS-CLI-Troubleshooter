from __future__ import annotations
import asyncio
import platform
import re
import time
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult

class PingCheck(BaseCheck):
    name = "ping"
    description = "ICMP Ping - utrata pakietów i opóźnienie"
    timeout = 30

    async def run(self, target: str, count: int = 10, **kwargs) -> CheckResult:
        start = time.perf_counter()
        try:
            is_win = platform.system() == "Windows"
            cmd = ["ping", "-n" if is_win else "-c", str(count), target]
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
                    check_name=self.name, target=target,
                    status="timeout", duration_s=time.perf_counter() - start,
                    summary="Ping timeout - brak odpowiedzi", error="timeout"
                )

            output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
            data = _parse_ping(output, is_win)
            loss = data.get("packet_loss_percent", 100)
            avg = data.get("avg_rtt_ms")

            if loss >= 100:
                status = "error"
            elif loss > 5 or (avg and avg > 300):
                status = "warning"
            else:
                status = "ok"

            loss_s = f"{loss:.0f}% utrata" if loss is not None else "utrata nieznana"
            avg_s = f"RTT avg {avg:.1f}ms" if isinstance(avg, float) else ""
            summary = f"{loss_s}, {avg_s}".strip(", ")

            return CheckResult(
                check_name=self.name, target=target, status=status,
                duration_s=time.perf_counter() - start, data=data, summary=summary
            )
        except Exception as e:
            return CheckResult(
                check_name=self.name, target=target, status="error",
                duration_s=time.perf_counter() - start, error=str(e),
                summary=f"Błąd ping: {e}"
            )


def _parse_ping(output: str, is_win: bool) -> dict:
    data = {}
    if is_win:
        m = re.search(r"Received = (\d+)", output)
        sent_m = re.search(r"Sent = (\d+)", output)
        lost_m = re.search(r"Lost = (\d+)", output)
        if sent_m and lost_m:
            sent = int(sent_m.group(1))
            lost = int(lost_m.group(1))
            data["packets_sent"] = sent
            data["packets_recv"] = sent - lost
            data["packet_loss_percent"] = (lost / sent * 100) if sent else 100
        m_rtt = re.search(r"Minimum = (\d+)ms.*Maximum = (\d+)ms.*Average = (\d+)ms", output)
        if m_rtt:
            data["min_rtt_ms"] = float(m_rtt.group(1))
            data["max_rtt_ms"] = float(m_rtt.group(2))
            data["avg_rtt_ms"] = float(m_rtt.group(3))
    else:
        m = re.search(r"(\d+) packets transmitted, (\d+) received", output)
        if m:
            sent, recv = int(m.group(1)), int(m.group(2))
            data["packets_sent"] = sent
            data["packets_recv"] = recv
            data["packet_loss_percent"] = ((sent - recv) / sent * 100) if sent else 100
        m_rtt = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)", output)
        if m_rtt:
            data["min_rtt_ms"] = float(m_rtt.group(1))
            data["avg_rtt_ms"] = float(m_rtt.group(2))
            data["max_rtt_ms"] = float(m_rtt.group(3))
            data["mdev_rtt_ms"] = float(m_rtt.group(4))
    return data
