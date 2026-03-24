from __future__ import annotations
import asyncio
import time
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult

class InterfacesCheck(BaseCheck):
    name = "interfaces"
    description = "Lokalne interfejsy sieciowe"
    timeout = 5

    async def run(self, target: str = "local", **kwargs) -> CheckResult:
        start = time.perf_counter()
        try:
            import psutil
            ifaces = []
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            io = psutil.net_io_counters(pernic=True)

            for name, stat in stats.items():
                iface_addrs = addrs.get(name, [])
                ipv4 = [str(a.address) for a in iface_addrs if a.family.name == "AF_INET"]
                iface_io = io.get(name)
                ifaces.append({
                    "name": name,
                    "up": stat.isup,
                    "speed_mbps": stat.speed,
                    "mtu": stat.mtu,
                    "ipv4": ipv4,
                    "bytes_sent": iface_io.bytes_sent if iface_io else 0,
                    "bytes_recv": iface_io.bytes_recv if iface_io else 0,
                })

            up_count = sum(1 for i in ifaces if i["up"])
            status = "ok" if up_count > 0 else "error"
            summary = f"Interfejsy aktywne: {up_count}/{len(ifaces)}"
            return CheckResult(
                check_name=self.name, target="local", status=status,
                duration_s=time.perf_counter() - start,
                data={"interfaces": ifaces, "up_count": up_count},
                summary=summary
            )
        except ImportError:
            return CheckResult(
                check_name=self.name, target="local", status="skipped",
                duration_s=time.perf_counter() - start,
                summary="psutil niedostępny", error="psutil not installed"
            )
        except Exception as e:
            return CheckResult(
                check_name=self.name, target="local", status="error",
                duration_s=time.perf_counter() - start, error=str(e),
                summary=f"Błąd: {e}"
            )
