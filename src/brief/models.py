from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class JobKind(str, Enum):
    posting = "posting"
    pattern = "pattern"
    guide = "guide"


class ApplyChannel(str, Enum):
    clipboard = "clipboard"
    email = "email"
    mailto = "mailto"
    manual = "manual"


class JobStatus(str, Enum):
    discovered = "discovered"
    structured = "structured"
    drafted = "drafted"
    applied = "applied"
    hired = "hired"
    working = "working"
    closed = "closed"


class SourceInfo(BaseModel):
    name: str = ""
    url: str = ""
    accessed_at: str = Field(default_factory=lambda: date.today().isoformat())
    note: str | None = None


class ApplyInfo(BaseModel):
    method: str = ""
    url: str = ""
    notes: str = ""


class DetailSection(BaseModel):
    heading: str = ""
    body: str = ""


class JobDetails(BaseModel):
    company: str | None = None
    summary: str = ""
    sections: list[DetailSection] = Field(default_factory=list)
    model_config = {"extra": "allow"}


class JobRef(BaseModel):
    """Canonical job reference — matches docs/refs/jobs/_template.json."""

    id: str = ""
    collected_at: str = Field(default_factory=lambda: date.today().isoformat())
    url: str = ""
    source: SourceInfo = Field(default_factory=SourceInfo)
    title: str = ""
    remote: bool | Literal["hybrid"] | str = True
    pay: str = ""
    schedule: str = ""
    location: str = ""
    employment_type: str = ""
    duties: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    apply: ApplyInfo = Field(default_factory=ApplyInfo)
    details: JobDetails = Field(default_factory=JobDetails)
    job_text: str = ""
    mapped_task_ids: list[str] = Field(default_factory=list)
    automation_notes: str = ""
    impl_difficulty_hint: int = 1
    tags: list[str] = Field(default_factory=list)

    @field_validator("impl_difficulty_hint")
    @classmethod
    def clamp_difficulty(cls, v: int) -> int:
        return max(1, min(5, int(v)))


class Profile(BaseModel):
    name: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: str = ""
    availability: str = ""
    hourly_hope: str = ""
    tone: str = "polite"
    notes: str = ""
    email: str = ""
    avoid: list[str] = Field(default_factory=list)


class ApplyPackage(BaseModel):
    job_id: str
    url: str = ""
    channel: ApplyChannel = ApplyChannel.clipboard
    materials: dict[str, Any] = Field(default_factory=dict)
    submit: dict[str, Any] = Field(
        default_factory=lambda: {
            "status": "pending_approval",
            "requires_human": True,
        }
    )


class WorkRequest(BaseModel):
    task_id: str
    job_id: str = ""
    input_text: str = ""
    context: dict[str, Any] = Field(default_factory=dict)


class WorkResult(BaseModel):
    task_id: str
    agent: str
    output: str
    human_gate: str = "review"
    meta: dict[str, Any] = Field(default_factory=dict)
