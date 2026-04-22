from __future__ import annotations
from datetime import datetime
from typing import Literal, Any
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str
    input: dict[str, Any]
    output: str
    error: str | None = None


class AgentStep(BaseModel):
    agent_name: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    reasoning: str
    output: str
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)
    guardrails_triggered: list[str] = Field(default_factory=list)
    tokens_used: int = 0


class SectionReport(BaseModel):
    section: Literal["market", "financial", "competitor", "risk"]
    summary: str
    key_findings: list[str]
    risk_level: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0.0, le=1.0)
    citations: list[str] = Field(default_factory=list)
    llm_judge_score: float | None = None
    guardrails_triggered: list[str] = Field(default_factory=list)
    agent_steps: list[AgentStep] = Field(default_factory=list)
    needs_review: bool = False


class DueDiligenceReport(BaseModel):
    id: str
    company_name: str
    created_at: datetime
    completed_at: datetime | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    sections: list[SectionReport] = Field(default_factory=list)
    overall_recommendation: Literal["pass", "monitor", "invest"] | None = None
    overall_confidence: float | None = None
    agent_trace: list[AgentStep] = Field(default_factory=list)
    eval_scores: dict[str, float] | None = None
    langfuse_trace_id: str | None = None
    error: str | None = None


class AnalyzeRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)


class AnalyzeResponse(BaseModel):
    report_id: str
    status: str
    message: str


class ReportStatusResponse(BaseModel):
    report_id: str
    status: str
    company_name: str
    created_at: datetime
    completed_at: datetime | None = None
    report: DueDiligenceReport | None = None
    error: str | None = None
