from __future__ import annotations
import json
import os
import re
from typing import Any, Callable, Dict, List, Optional
from dotenv import load_dotenv
import pathlib

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
DOTENV_PATH = ROOT_DIR / ".env"

CATEGORIES = ["DNS", "routing", "application", "firewall", "TLS", "performance", "ok"]

def _build_prompt(target: str, profile: str, diagnostic_data: Dict[str, Any], history: List[Dict] = None) -> str:
    results = diagnostic_data.get("results", {})
    overall = diagnostic_data.get("overall_status", "unknown")
    duration = diagnostic_data.get("duration_s", 0)

    lines = [
        "## Cel diagnostyki",
        f"Target: {target}",
        f"Profil: {profile}",
        f"Czas trwania: {duration:.1f}s",
        f"Ogólny status: {overall}",
        "",
        "## Wyniki checków",
    ]

    for check_name, result in results.items():
        status = result.get("status", "unknown")
        summary = result.get("summary", "")
        data = result.get("data", {})
        lines.append(f"\n### {check_name.upper()} [{status.upper()}]")
        lines.append(f"Podsumowanie: {summary}")
        if data:
            if check_name == "ping":
                loss = data.get("packet_loss_percent")
                avg = data.get("avg_rtt_ms")
                if loss is not None: lines.append(f"Utrata pakietów: {loss:.1f}%")
                if avg is not None: lines.append(f"RTT avg: {avg:.1f}ms")
            elif check_name == "dns":
                a = data.get("records", {}).get("A", [])
                consistency = data.get("resolver_consistency", True)
                lines.append(f"Rekordy A: {a}")
                lines.append(f"Spójność resolverów: {'TAK' if consistency else 'NIE - UWAGA!'}")
            elif check_name == "ssl":
                days = data.get("days_until_expiry")
                tls = data.get("tls_version")
                lines.append(f"Dni do wygaśnięcia: {days}")
                lines.append(f"Wersja TLS: {tls}")
            elif check_name == "http":
                https = data.get("https", {})
                http = data.get("http", {})
                lines.append(f"HTTPS status: {https.get('status_code', 'brak')}")
                lines.append(f"HTTP status: {http.get('status_code', 'brak')}")
                missing = https.get("missing_security_headers", [])
                if missing: lines.append(f"Brakujące nagłówki bezpieczeństwa: {missing}")
            elif check_name == "ports":
                open_p = data.get("open_ports", [])
                closed_p = data.get("closed_ports", [])
                lines.append(f"Otwarte porty: {open_p}")
                lines.append(f"Zamknięte porty: {closed_p}")
            elif check_name == "traceroute":
                lines.append(f"Liczba hopów: {data.get('hop_count', 0)}")
            elif check_name == "interfaces":
                up = data.get("up_count", 0)
                total = len(data.get("interfaces", []))
                lines.append(f"Aktywne interfejsy: {up}/{total}")

    if history:
        lines += ["", "## Kontekst historyczny (ostatnie 3 runy dla tego celu)"]
        for h in history[:3]:
            lines.append(f"- {h.get('timestamp','?')}: status={h.get('status','?')}, ryzyko={h.get('risk_score','?')}/100")
            ai_prev = h.get("ai_summary", {})
            if isinstance(ai_prev, dict) and ai_prev.get("category"):
                lines.append(f"  Kategoria problemu: {ai_prev['category']}")

    lines += [
        "",
        "## Zadanie",
        "Przeanalizuj wyniki i dostarcz raport w języku POLSKIM w następującym formacie:",
        "",
        "**PODSUMOWANIE WYKONAWCZE**",
        "(2-3 zdania dla osoby bez wiedzy technicznej)",
        "",
        "**WYKRYTE PROBLEMY**",
        "(lista z poziomem: KRYTYCZNY / WYSOKI / ŚREDNI / NISKI)",
        "",
        "**ANALIZA TECHNICZNA**",
        "(root cause każdego problemu)",
        "",
        "**KROKI NAPRAWCZE**",
        "(numerowana lista konkretnych kroków, ZAWIERAJ dokładne komendy do wklejenia w terminal gdy to możliwe)",
        "",
        "**SUGEROWANE KOMENDY**",
        "(blok z komendami CLI do uruchomienia w celu dalszej diagnostyki lub naprawy)",
        "",
        f"**KATEGORIA PROBLEMU**: (wybierz JEDNĄ z: {', '.join(CATEGORIES)})",
        "",
        "**OCENA RYZYKA**: (liczba 0-100)",
        "",
        "Odpowiadaj wyłącznie po polsku.",
    ]
    return "\n".join(lines)


def analyze_with_claude(
    target: str,
    profile: str,
    diagnostic_data: Dict[str, Any],
    history: List[Dict] = None,
    on_token: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    load_dotenv(dotenv_path=str(DOTENV_PATH), override=False)
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY nie jest ustawiony")

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    prompt = _build_prompt(target, profile, diagnostic_data, history or [])

    raw_text = ""
    if on_token:
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1800,
            temperature=0.2,
            system=(
                "Jesteś ekspertem diagnostyki sieci i infrastruktury IT. "
                "Analizujesz wyniki diagnostyki i dostarczasz raporty wyłącznie w języku POLSKIM. "
                "Twoje odpowiedzi są precyzyjne technicznie, zawierają konkretne komendy naprawcze."
            ),
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                raw_text += text
                on_token(text)
    else:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1800,
            temperature=0.2,
            system=(
                "Jesteś ekspertem diagnostyki sieci i infrastruktury IT. "
                "Analizujesz wyniki diagnostyki i dostarczasz raporty wyłącznie w języku POLSKIM. "
                "Twoje odpowiedzi są precyzyjne technicznie, zawierają konkretne komendy naprawcze."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        content = getattr(msg, "content", None)
        if isinstance(content, list) and content:
            raw_text = getattr(content[0], "text", str(content[0])).strip()

    risk_score = 0
    m = re.search(r"OCENA RYZYKA[:\s*]*(\d+)", raw_text)
    if m:
        risk_score = min(100, max(0, int(m.group(1))))

    category = "ok"
    m_cat = re.search(r"KATEGORIA PROBLEMU[:\s*]*([A-Za-z]+)", raw_text)
    if m_cat:
        cat = m_cat.group(1).strip()
        if cat in CATEGORIES:
            category = cat

    commands = []
    m_cmd = re.search(r"SUGEROWANE KOMENDY.*?```(?:bash|shell)?\n?(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
    if not m_cmd:
        m_cmd = re.search(r"SUGEROWANE KOMENDY[:\n]+((?:.*\n)+?)(?:\n\*\*|\Z)", raw_text, re.IGNORECASE)
    if m_cmd:
        commands = [l.strip() for l in m_cmd.group(1).splitlines() if l.strip() and not l.strip().startswith("#")]

    return {
        "raw_text": raw_text,
        "risk_score": risk_score,
        "category": category,
        "commands": commands,
        "analyzer": "claude",
    }


def rule_based_analyze(target: str, profile: str, diagnostic_data: Dict[str, Any], history: List[Dict] = None) -> Dict[str, Any]:
    results = diagnostic_data.get("results", {})
    issues = []
    risk = 0
    category = "ok"
    commands = []

    dns = results.get("dns", {})
    ping = results.get("ping", {})
    ssl = results.get("ssl", {})
    http = results.get("http", {})
    ports = results.get("ports", {})

    if dns.get("status") == "error":
        issues.append("KRYTYCZNY: Rozwiązywanie DNS nie powiodło się")
        category = "DNS"
        risk += 40
        commands += [f"nslookup {target}", f"nslookup {target} 8.8.8.8", "ipconfig /flushdns"]
    if ping.get("status") == "error":
        issues.append("WYSOKI: Cel niedostępny przez ICMP")
        if category == "ok": category = "routing"
        risk += 30
        commands.append(f"ping -n 20 {target}")
    elif ping.get("status") == "warning":
        loss = ping.get("data", {}).get("packet_loss_percent", 0)
        issues.append(f"ŚREDNI: Utrata pakietów {loss:.0f}%")
        if category == "ok": category = "performance"
        risk += 15
    if ssl.get("status") in ("error", "warning"):
        days = ssl.get("data", {}).get("days_until_expiry", 0)
        issues.append(f"WYSOKI: Certyfikat SSL wygasa za {days} dni")
        if category == "ok": category = "TLS"
        risk += 25
        commands.append(f"openssl s_client -connect {target}:443 -servername {target}")
    if http.get("status") == "error":
        issues.append("WYSOKI: Serwis HTTP/HTTPS niedostępny")
        if category == "ok": category = "application"
        risk += 25
        commands.append(f"curl -v https://{target}")
    if ports.get("status") == "error":
        issues.append("WYSOKI: Wszystkie porty zamknięte")
        if category == "ok": category = "firewall"
        risk += 25

    if not issues:
        text = f"Diagnostyka dla {target} zakończona bez wykrycia problemów. Wszystkie sprawdzone usługi działają prawidłowo.\n\nOCENA RYZYKA: 0"
    else:
        text = f"Diagnostyka dla {target} wykryła następujące problemy:\n\n"
        for i, issue in enumerate(issues, 1):
            text += f"{i}. {issue}\n"
        if commands:
            text += f"\nSUGEROWANE KOMENDY:\n" + "\n".join(f"  {c}" for c in commands)
        text += f"\n\nOCENA RYZYKA: {min(100, risk)}"

    return {
        "raw_text": text,
        "risk_score": min(100, risk),
        "category": category,
        "commands": commands,
        "analyzer": "rule_based",
    }
