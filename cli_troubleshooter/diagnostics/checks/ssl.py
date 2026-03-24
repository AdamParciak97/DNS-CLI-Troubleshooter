from __future__ import annotations
import asyncio
import ssl
import socket
import time
from datetime import datetime
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult

class SslCheck(BaseCheck):
    name = "ssl"
    description = "Certyfikat TLS/SSL - ważność, konfiguracja"
    timeout = 10

    async def run(self, target: str, port: int = 443, **kwargs) -> CheckResult:
        start = time.perf_counter()
        host = target
        if "://" in target:
            from urllib.parse import urlparse
            parsed = urlparse(target)
            host = parsed.hostname or target
            if parsed.port:
                port = parsed.port

        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, _get_cert_info, host, port)

            days_left = data.get("days_until_expiry", 0)
            if data.get("error"):
                status = "error"
                summary = f"Błąd SSL: {data['error']}"
            elif days_left < 7:
                status = "error"
                summary = f"Certyfikat wygasa za {days_left} dni!"
            elif days_left < 30:
                status = "warning"
                summary = f"Certyfikat wygasa za {days_left} dni"
            else:
                status = "ok"
                summary = f"Certyfikat OK, ważny {days_left} dni (do {data.get('not_after', '')})"

            return CheckResult(
                check_name=self.name, target=host, status=status,
                duration_s=time.perf_counter() - start, data=data, summary=summary
            )
        except Exception as e:
            return CheckResult(
                check_name=self.name, target=host, status="error",
                duration_s=time.perf_counter() - start, error=str(e),
                summary=f"Błąd SSL: {e}"
            )


def _get_cert_info(host: str, port: int) -> dict:
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                tls_version = ssock.version()
                cipher = ssock.cipher()
    except ssl.SSLError as e:
        return {"error": str(e)}
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        return {"error": str(e)}

    not_after_str = cert.get("notAfter", "")
    try:
        not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
        days_left = (not_after - datetime.utcnow()).days
    except Exception:
        not_after = None
        days_left = -1

    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    san = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]

    return {
        "subject_cn": subject.get("commonName"),
        "issuer_o": issuer.get("organizationName"),
        "not_before": cert.get("notBefore"),
        "not_after": not_after_str,
        "days_until_expiry": days_left,
        "tls_version": tls_version,
        "cipher": cipher[0] if cipher else None,
        "san": san,
    }
