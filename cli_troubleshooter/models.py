from __future__ import annotations
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlmodel import SQLModel, Field, Column, JSON
from pydantic import BaseModel

class DiagnosticRun(SQLModel, table=True):
    __tablename__ = "diagnostic_runs"
    id: Optional[int] = Field(default=None, primary_key=True)
    target: str = Field(index=True)
    profile: str = Field(default="quick")
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    duration_s: float = Field(default=0.0)
    risk_score: int = Field(default=0)
    status: str = Field(default="ok")  # ok/warning/error
    analyzer: str = Field(default="rule_based")  # claude/rule_based
    checks_run: str = Field(default="[]")  # JSON list
    results_json: str = Field(default="{}")  # JSON dict of check results
    ai_summary_json: str = Field(default="{}")  # JSON AISummary

    def get_results(self) -> Dict[str, Any]:
        return json.loads(self.results_json)

    def get_ai_summary(self) -> Dict[str, Any]:
        return json.loads(self.ai_summary_json)

    def get_checks_run(self) -> List[str]:
        return json.loads(self.checks_run)

class AlertRecord(SQLModel, table=True):
    __tablename__ = "alerts"
    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: Optional[int] = Field(default=None, foreign_key="diagnostic_runs.id")
    target: str
    severity: str  # critical/high/medium/low
    title: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    acknowledged: bool = Field(default=False)

class ScheduleRecord(SQLModel, table=True):
    __tablename__ = "schedules"
    id: Optional[int] = Field(default=None, primary_key=True)
    target: str
    profile: str = "quick"
    cron_expression: str
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class CheckResult(BaseModel):
    check_name: str
    target: str
    status: str  # ok/warning/error/timeout/skipped
    duration_s: float = 0.0
    data: Dict[str, Any] = {}
    summary: str = ""
    error: Optional[str] = None

class AISummary(BaseModel):
    executive_summary: str = ""
    technical_details: str = ""
    issues_found: List[Dict[str, str]] = []
    recommendations: List[str] = []
    risk_score: int = 0
    raw_text: str = ""
