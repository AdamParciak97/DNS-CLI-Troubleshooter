from __future__ import annotations
from typing import Any, Dict, List
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

STATUS_COLORS = {
    "ok": "green",
    "warning": "yellow",
    "error": "red",
    "timeout": "red",
    "skipped": "dim",
    "unknown": "dim",
}

def status_badge(status: str) -> Text:
    color = STATUS_COLORS.get(status, "dim")
    icons = {"ok": "✓", "warning": "⚠", "error": "✗", "timeout": "⏱", "skipped": "—"}
    icon = icons.get(status, "?")
    return Text(f"{icon} {status}", style=color)

def results_table(results: Dict[str, Any]) -> Table:
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Check", style="bold", min_width=12)
    table.add_column("Status", min_width=12)
    table.add_column("Czas", min_width=8)
    table.add_column("Podsumowanie", overflow="fold")

    for name, result in results.items():
        status = result.get("status", "unknown")
        duration = result.get("duration_s", 0)
        summary = result.get("summary", "")
        table.add_row(
            name,
            status_badge(status),
            f"{duration:.1f}s",
            summary,
        )
    return table

def history_table(runs: List[Any]) -> Table:
    table = Table(box=box.ROUNDED, header_style="bold cyan")
    table.add_column("ID", style="dim", min_width=4)
    table.add_column("Target", min_width=20)
    table.add_column("Profil", min_width=10)
    table.add_column("Status")
    table.add_column("Ryzyko", min_width=8)
    table.add_column("Czas", min_width=20)

    for run in runs:
        risk = run.risk_score
        risk_color = "green" if risk < 30 else "yellow" if risk < 60 else "red"
        table.add_row(
            str(run.id),
            run.target,
            run.profile,
            status_badge(run.status),
            Text(str(risk), style=risk_color),
            run.timestamp.strftime("%Y-%m-%d %H:%M"),
        )
    return table
