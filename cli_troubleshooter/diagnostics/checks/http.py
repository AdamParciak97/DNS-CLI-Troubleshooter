from __future__ import annotations
import asyncio
import time
from typing import Dict, Any
import httpx
from cli_troubleshooter.diagnostics.checks.base import BaseCheck
from cli_troubleshooter.models import CheckResult

SECURITY_HEADERS = [
    "strict-transport-security", "content-security-policy",
    "x-frame-options", "x-content-type-options", "x-xss-protection"
]

class HttpCheck(BaseCheck):
    name = "http"
    description = "HTTP/HTTPS - status, nagłówki bezpieczeństwa, TTFB"
    timeout = 15

    async def run(self, target: str, **kwargs) -> CheckResult:
        start = time.perf_counter()
        host = target
        if not host.startswith("http"):
            urls = [f"https://{host}", f"http://{host}"]
        else:
            urls = [host]

        results = {}
        overall_status = "ok"

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(self.timeout),
            verify=False,
        ) as client:
            for url in urls:
                scheme = "https" if url.startswith("https") else "http"
                try:
                    req_start = time.perf_counter()
                    resp = await client.get(url)
                    ttfb = time.perf_counter() - req_start
                    headers = dict(resp.headers)
                    sec_headers = {h: headers.get(h) for h in SECURITY_HEADERS}
                    missing_sec = [h for h, v in sec_headers.items() if not v]
                    redirects = [str(r.url) for r in resp.history]
                    results[scheme] = {
                        "status_code": resp.status_code,
                        "ttfb_ms": round(ttfb * 1000, 1),
                        "server": headers.get("server"),
                        "content_type": headers.get("content-type"),
                        "security_headers": sec_headers,
                        "missing_security_headers": missing_sec,
                        "redirects": redirects,
                        "final_url": str(resp.url),
                    }
                    if resp.status_code >= 500:
                        overall_status = "error"
                    elif resp.status_code >= 400 and overall_status == "ok":
                        overall_status = "warning"
                except httpx.ConnectError:
                    results[scheme] = {"error": "connection_refused"}
                    overall_status = "error"
                except httpx.TimeoutException:
                    results[scheme] = {"error": "timeout"}
                    overall_status = "error"
                except Exception as e:
                    results[scheme] = {"error": str(e)}
                    if overall_status == "ok":
                        overall_status = "warning"

        https_r = results.get("https", {})
        http_r = results.get("http", {})
        code_https = https_r.get("status_code", "err")
        code_http = http_r.get("status_code", "err")
        summary = f"HTTPS={code_https} HTTP={code_http}"

        return CheckResult(
            check_name=self.name, target=host, status=overall_status,
            duration_s=time.perf_counter() - start, data=results, summary=summary
        )
