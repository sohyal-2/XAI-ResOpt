"""Real Agent Observability: Structured logging, telemetry tracking, and database persistence."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AgentRun, RunStatus

logger = logging.getLogger("xai_resopt.observability")

# Standard 11 execution agents tracked by XAI-ResOpt
EXPECTED_AGENTS = [
    "intake_agent",
    "resume_parser",
    "jd_analyzer",
    "ats_agent",
    "skill_agent",
    "evidence_agent",
    "explainability_agent",
    "optimizer_agent",
    "critic_agent",
    "fact_check_agent",
    "ats_re_evaluator",
]

AGENT_DISPLAY_NAMES: dict[str, str] = {
    "intake_agent": "Intake Agent",
    "resume_parser": "Resume Parser",
    "jd_analyzer": "JD Analyzer",
    "ats_agent": "ATS Agent",
    "skill_agent": "Skill Agent",
    "evidence_agent": "Evidence Agent",
    "explainability_agent": "Explainability",
    "optimizer_agent": "Optimizer",
    "critic_agent": "Critic",
    "fact_check_agent": "Fact Checker",
    "ats_re_evaluator": "ATS Re-Evaluator",
}


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects with telemetry metadata."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in [
            "request_id",
            "analysis_id",
            "agent_name",
            "status",
            "duration_ms",
            "retry_count",
            "retrieval_count",
            "model_calls",
            "token_usage",
            "error",
            "recovery_status",
            "final_score",
        ]:
            if hasattr(record, attr):
                val = getattr(record, attr)
                if val is not None:
                    log_data[attr] = str(val) if isinstance(val, UUID) else val

        return json.dumps(log_data)


def configure_structured_logging() -> None:
    """Configures root structured logger for agent telemetry."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_log = logging.getLogger("xai_resopt")
    if not root_log.handlers:
        root_log.addHandler(handler)
        root_log.setLevel(logging.INFO)


def log_agent_event(
    agent_name: str,
    status: str,
    request_id: str | None = None,
    analysis_id: UUID | None = None,
    duration_ms: int | None = None,
    retry_count: int = 0,
    retrieval_count: int = 0,
    model_calls: int = 0,
    token_usage: dict[str, Any] | None = None,
    error: str | None = None,
    recovery_status: str | None = None,
    final_score: float | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Emits a structured JSON log for agent lifecycle and returns telemetry dictionary."""
    display = AGENT_DISPLAY_NAMES.get(agent_name, agent_name)
    event_data: dict[str, Any] = {
        "event": "agent_execution",
        "agent_name": agent_name,
        "display_name": display,
        "status": status,
        "request_id": request_id,
        "analysis_id": str(analysis_id) if analysis_id else None,
        "duration_ms": duration_ms,
        "retry_count": retry_count,
        "retrieval_count": retrieval_count,
        "model_calls": model_calls,
        "token_usage": token_usage or {},
        "error": error,
        "recovery_status": recovery_status,
        "final_score": final_score,
    }

    log_msg = message or f"Agent '{display}' transitioned to status: {status}"
    logger.info(
        log_msg,
        extra={
            "request_id": request_id,
            "analysis_id": analysis_id,
            "agent_name": agent_name,
            "status": status,
            "duration_ms": duration_ms,
            "retry_count": retry_count,
            "retrieval_count": retrieval_count,
            "model_calls": model_calls,
            "token_usage": token_usage,
            "error": error,
            "recovery_status": recovery_status,
            "final_score": final_score,
        },
    )
    return event_data


async def init_analysis_pipeline_runs(
    db: AsyncSession,
    analysis_id: UUID,
    request_id: str | None = None,
) -> list[AgentRun]:
    """Pre-registers all 11 pipeline agents in queued status for full end-to-end visibility."""
    runs: list[AgentRun] = []
    now = datetime.now(timezone.utc)
    for agent_key in EXPECTED_AGENTS:
        run = AgentRun(
            id=uuid4(),
            analysis_id=analysis_id,
            request_id=request_id,
            agent_name=agent_key,
            status=RunStatus.queued,
            start_time=None,
            end_time=None,
            duration_ms=None,
            retry_count=0,
            retrieval_count=0,
            model_calls=0,
            token_usage=None,
            error=None,
            recovery_status=None,
            final_score=None,
            output=None,
            created_at=now,
        )
        db.add(run)
        runs.append(run)
        log_agent_event(
            agent_name=agent_key,
            status=RunStatus.queued.value,
            request_id=request_id,
            analysis_id=analysis_id,
        )
    await db.flush()
    return runs


class AgentTelemetryTracker:
    """Async context manager tracking agent turn, recording start/end/duration, and persisting state."""

    def __init__(
        self,
        db: AsyncSession,
        analysis_id: UUID,
        request_id: str | None,
        agent_name: str,
        retry_count: int = 0,
        initial_status: RunStatus = RunStatus.running,
    ) -> None:
        self.db = db
        self.analysis_id = analysis_id
        self.request_id = request_id
        self.agent_name = agent_name
        self.retry_count = retry_count
        self.status: RunStatus = initial_status

        self.start_time: datetime = datetime.now(timezone.utc)
        self.end_time: datetime | None = None
        self._start_perf: float = time.perf_counter()
        self.duration_ms: int | None = None

        self.retrieval_count: int = 0
        self.model_calls: int = 0
        self.token_usage: dict[str, Any] = {}
        self.error: str | None = None
        self.recovery_status: str | None = None
        self.final_score: float | None = None
        self.output: dict[str, Any] | None = None

        self.target_record: AgentRun | None = None

    async def __aenter__(self) -> AgentTelemetryTracker:
        stmt = (
            select(AgentRun)
            .where(
                AgentRun.analysis_id == self.analysis_id,
                AgentRun.agent_name == self.agent_name,
                AgentRun.status == RunStatus.queued,
            )
            .order_by(AgentRun.created_at.asc())
        )
        existing = await self.db.scalar(stmt)
        if existing:
            self.target_record = existing
            self.target_record.status = self.status
            self.target_record.start_time = self.start_time
            self.target_record.request_id = self.request_id
        else:
            self.target_record = AgentRun(
                id=uuid4(),
                analysis_id=self.analysis_id,
                request_id=self.request_id,
                agent_name=self.agent_name,
                status=self.status,
                start_time=self.start_time,
                retry_count=self.retry_count,
            )
            self.db.add(self.target_record)

        await self.db.flush()

        log_agent_event(
            agent_name=self.agent_name,
            status=self.status.value,
            request_id=self.request_id,
            analysis_id=self.analysis_id,
            retry_count=self.retry_count,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = int((time.perf_counter() - self._start_perf) * 1000)

        if exc_val is not None:
            self.status = RunStatus.failed
            self.error = str(exc_val)
            if not self.recovery_status:
                self.recovery_status = "unrecovered"
        elif self.status != RunStatus.failed:
            self.status = RunStatus.completed

        log_agent_event(
            agent_name=self.agent_name,
            status=self.status.value,
            request_id=self.request_id,
            analysis_id=self.analysis_id,
            duration_ms=self.duration_ms,
            retry_count=self.retry_count,
            retrieval_count=self.retrieval_count,
            model_calls=self.model_calls,
            token_usage=self.token_usage,
            error=self.error,
            recovery_status=self.recovery_status,
            final_score=self.final_score,
        )

        if self.target_record:
            self.target_record.status = self.status
            self.target_record.end_time = self.end_time
            self.target_record.duration_ms = self.duration_ms
            self.target_record.retry_count = self.retry_count
            self.target_record.retrieval_count = self.retrieval_count
            self.target_record.model_calls = self.model_calls
            self.target_record.token_usage = self.token_usage
            self.target_record.error = self.error
            self.target_record.recovery_status = self.recovery_status
            self.target_record.final_score = self.final_score
            self.target_record.output = self.output
            await self.db.flush()

        if exc_val is not None and self.recovery_status in {"recovered", "fallback_applied"}:
            return True
        return False
