from __future__ import annotations
import asyncio
import json
import sys
from typing import List, Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.table import Table

app = typer.Typer(
    name="ct",
    help="CLI Troubleshooter - Diagnostyka sieci z AI",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

# ── run ────────────────────────────────────────────────────────────────────────

@app.command()
def run(
    target: str = typer.Argument(..., help="Adres IP lub domena do diagnostyki"),
    profile: str = typer.Option("quick", "--profile", "-p", help="Profil: quick/full/web/connectivity"),
    checks: Optional[str] = typer.Option(None, "--checks", "-c", help="Konkretne checki: ping,dns,http"),
    save: bool = typer.Option(True, "--save/--no-save", help="Zapisz wyniki do bazy danych"),
    ai: bool = typer.Option(True, "--ai/--no-ai", help="Generuj AI Summary"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Zapisz raport JSON do pliku"),
):
    """Uruchom diagnostykę sieci dla podanego celu."""
    check_list = [c.strip() for c in checks.split(",")] if checks else None

    console.print(Panel.fit(
        f"[bold cyan]CLI Troubleshooter[/bold cyan]\n"
        f"Target: [bold]{target}[/bold]  Profil: [yellow]{profile}[/yellow]",
        border_style="cyan"
    ))

    from cli_troubleshooter.diagnostics.runner import run_diagnostics
    from cli_troubleshooter.cli.display.tables import results_table, status_badge

    completed_checks = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        tasks = {}

        def on_start(name: str):
            tasks[name] = progress.add_task(f"[cyan]{name}...", total=1)

        def on_done(name: str, result):
            completed_checks[name] = result.model_dump()
            if name in tasks:
                progress.update(tasks[name], completed=1, description=f"[green]{name} ✓")

        diag = asyncio.run(run_diagnostics(
            target=target,
            profile=profile,
            checks=check_list,
            on_check_start=on_start,
            on_check_done=on_done,
        ))

    console.print(results_table(diag["results"]))

    ai_result = {}
    if ai:
        console.print("\n[bold]Generowanie AI Summary...[/bold]")
        from cli_troubleshooter.ai.analyzer import analyze_with_claude, rule_based_analyze
        try:
            ai_result = analyze_with_claude(target, profile, diag)
            analyzer_label = "[cyan]Claude AI[/cyan]"
        except Exception as e:
            ai_result = rule_based_analyze(target, profile, diag)
            analyzer_label = "[yellow]Reguły (fallback)[/yellow]"

        risk = ai_result.get("risk_score", 0)
        risk_color = "green" if risk < 30 else "yellow" if risk < 60 else "red"

        console.print(Panel(
            ai_result.get("raw_text", ""),
            title=f"[bold]AI Summary[/bold] ({analyzer_label}) — Ryzyko: [{risk_color}]{risk}/100[/]",
            border_style="blue",
        ))

    if save:
        import json as _json
        from cli_troubleshooter.models import DiagnosticRun
        from cli_troubleshooter.storage.repositories import save_run
        run_record = DiagnosticRun(
            target=target,
            profile=profile,
            duration_s=diag["duration_s"],
            risk_score=ai_result.get("risk_score", 0),
            status=diag["overall_status"],
            analyzer=ai_result.get("analyzer", "none"),
            checks_run=_json.dumps(diag["checks_run"]),
            results_json=_json.dumps(diag["results"]),
            ai_summary_json=_json.dumps(ai_result),
        )
        saved = save_run(run_record)
        console.print(f"\n[dim]Zapisano jako run #{saved.id}[/dim]")

    if output:
        data = {**diag, "ai_summary": ai_result}
        output.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[dim]Raport JSON: {output}[/dim]")


# ── history ────────────────────────────────────────────────────────────────────

@app.command()
def history(
    target: Optional[str] = typer.Argument(None, help="Filtruj po target"),
    last: int = typer.Option(20, "--last", "-n", help="Liczba ostatnich wpisów"),
):
    """Pokaż historię diagnostyk."""
    from cli_troubleshooter.storage.repositories import get_runs
    from cli_troubleshooter.cli.display.tables import history_table
    runs = get_runs(target=target, limit=last)
    if not runs:
        console.print("[yellow]Brak historii diagnostyk.[/yellow]")
        return
    console.print(history_table(runs))
    console.print(f"\n[dim]Wyświetlono {len(runs)} wpisów[/dim]")


# ── dashboard ──────────────────────────────────────────────────────────────────

@app.command()
def dashboard(
    port: int = typer.Option(8080, "--port", "-p", help="Port"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Otwórz przeglądarkę"),
):
    """Uruchom web dashboard."""
    import uvicorn
    import threading, webbrowser, time

    if open_browser:
        def _open():
            time.sleep(1.5)
            webbrowser.open(f"http://{host}:{port}")
        threading.Thread(target=_open, daemon=True).start()

    console.print(Panel.fit(
        f"[bold]Dashboard[/bold] uruchomiony na [cyan]http://{host}:{port}[/cyan]\n"
        f"Naciśnij [bold]Ctrl+C[/bold] aby zatrzymać",
        border_style="green"
    ))

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    uvicorn.run(
        "cli_troubleshooter.dashboard.app:app",
        host=host, port=port, log_level="warning"
    )


# ── alerts ─────────────────────────────────────────────────────────────────────

@app.command()
def alerts(
    status: Optional[str] = typer.Option(None, "--status", help="Filtr: new/all"),
    ack_id: Optional[int] = typer.Option(None, "--ack", help="ID alertu do potwierdzenia"),
):
    """Zarządzaj alertami."""
    from cli_troubleshooter.storage.repositories import get_alerts, ack_alert
    if ack_id:
        if ack_alert(ack_id):
            console.print(f"[green]Alert #{ack_id} potwierdzony.[/green]")
        else:
            console.print(f"[red]Alert #{ack_id} nie znaleziony.[/red]")
        return

    items = get_alerts(status=status)
    if not items:
        console.print("[green]Brak alertów.[/green]")
        return

    t = Table(show_header=True, header_style="bold")
    t.add_column("ID")
    t.add_column("Severity")
    t.add_column("Target")
    t.add_column("Opis")
    t.add_column("Czas")
    t.add_column("Status")
    for a in items:
        sev_color = {"critical": "red", "high": "red", "medium": "yellow", "low": "cyan"}.get(a.severity, "white")
        t.add_row(
            str(a.id),
            f"[{sev_color}]{a.severity}[/]",
            a.target,
            a.title,
            a.timestamp.strftime("%Y-%m-%d %H:%M"),
            "[dim]ack[/dim]" if a.acknowledged else "[yellow]new[/yellow]",
        )
    console.print(t)


def main():
    app()


if __name__ == "__main__":
    main()
