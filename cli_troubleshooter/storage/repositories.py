from __future__ import annotations
import json
from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import Session, select, desc
from cli_troubleshooter.models import DiagnosticRun, AlertRecord, ScheduleRecord
from cli_troubleshooter.storage.db import get_engine

def save_run(run: DiagnosticRun) -> DiagnosticRun:
    from sqlmodel import Session
    with Session(get_engine()) as session:
        session.add(run)
        session.commit()
        session.refresh(run)
        return run

def get_runs(target: Optional[str] = None, limit: int = 50) -> List[DiagnosticRun]:
    with Session(get_engine()) as session:
        stmt = select(DiagnosticRun)
        if target:
            stmt = stmt.where(DiagnosticRun.target == target)
        stmt = stmt.order_by(desc(DiagnosticRun.timestamp)).limit(limit)
        return session.exec(stmt).all()

def get_run(run_id: int) -> Optional[DiagnosticRun]:
    with Session(get_engine()) as session:
        return session.get(DiagnosticRun, run_id)

def save_alert(alert: AlertRecord) -> AlertRecord:
    with Session(get_engine()) as session:
        session.add(alert)
        session.commit()
        session.refresh(alert)
        return alert

def get_alerts(status: Optional[str] = None, limit: int = 50) -> List[AlertRecord]:
    with Session(get_engine()) as session:
        stmt = select(AlertRecord).order_by(desc(AlertRecord.timestamp)).limit(limit)
        if status == "new":
            stmt = select(AlertRecord).where(AlertRecord.acknowledged == False).order_by(desc(AlertRecord.timestamp)).limit(limit)
        return session.exec(stmt).all()

def ack_alert(alert_id: int) -> bool:
    with Session(get_engine()) as session:
        alert = session.get(AlertRecord, alert_id)
        if not alert:
            return False
        alert.acknowledged = True
        session.add(alert)
        session.commit()
        return True

def get_schedules() -> List[ScheduleRecord]:
    with Session(get_engine()) as session:
        return session.exec(select(ScheduleRecord)).all()

def save_schedule(schedule: ScheduleRecord) -> ScheduleRecord:
    with Session(get_engine()) as session:
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        return schedule

def delete_schedule(schedule_id: int) -> bool:
    with Session(get_engine()) as session:
        s = session.get(ScheduleRecord, schedule_id)
        if not s:
            return False
        session.delete(s)
        session.commit()
        return True

def purge_old_runs(days: int = 90) -> int:
    cutoff = datetime.utcnow() - timedelta(days=days)
    with Session(get_engine()) as session:
        old = session.exec(select(DiagnosticRun).where(DiagnosticRun.timestamp < cutoff)).all()
        count = len(old)
        for r in old:
            session.delete(r)
        session.commit()
        return count
