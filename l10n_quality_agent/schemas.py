"""chains, workflow, CLI, storage가 공유하는 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ErrorCategory = Literal[
    "accuracy", "terminology", "spelling", "grammar", "style", "fluency"
]
Severity = Literal["minor", "major", "critical"]


class AgentStatus(StrEnum):
    DRAFT = "DRAFT"
    EVALUATING = "EVALUATING"
    REVISING = "REVISING"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TranslationRequest(BaseModel):
    source: str = Field(min_length=1, description="번역할 한국어 원문")
    target_language: str = Field(min_length=1, description="목표 언어")
    target_country: str = Field(min_length=1, description="목표 국가 또는 로케일")
    additional_instruction: str = Field(
        default="", description="사용자가 제공한 선택적 추가 번역 지시"
    )
    protected_terms: list[str] = Field(
        default_factory=list, description="정확한 표기를 유지해야 하는 브랜드 및 제품명"
    )


class MQMError(BaseModel):
    category: ErrorCategory = Field(description="MQM 오류 영역")
    severity: Severity = Field(description="오류 심각도")
    span: str = Field(
        description="오류가 있는 번역문 구간. 특정할 수 없으면 빈 문자열"
    )
    explanation: str = Field(description="원문과 번역문에 근거한 오류 설명")
    suggested_fix: str | None = Field(
        default=None, description="가능한 수정안. 확신할 수 없으면 null"
    )


class MQMResult(BaseModel):
    errors: list[MQMError] = Field(
        default_factory=list,
        description="발견된 오류 목록. 근거 있는 오류가 없으면 빈 목록",
    )


class TranslationVersion(BaseModel):
    version: int
    translation: str
    created_at: str = Field(default_factory=lambda: now_iso())
    based_on_version: int | None = None
    instruction: str = ""
    mqm: MQMResult | None = None


class AttemptRecord(BaseModel):
    step: int
    category: ErrorCategory
    attempt: int
    input_translation: str
    candidate: str
    selected_errors: list[MQMError]
    accepted: bool
    failure_reasons: list[str] = Field(default_factory=list)
    mqm_before: MQMResult
    mqm_after: MQMResult | None = None
    created_at: str = Field(default_factory=lambda: now_iso())


class RunRecord(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    request: TranslationRequest
    status: AgentStatus = AgentStatus.DRAFT
    model_name: str = "qwen3.5:4b"
    temperature: float = 0
    seed: int = 42
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: now_iso())
    updated_at: str = Field(default_factory=lambda: now_iso())
    parent_run_id: str | None = None
    parent_version: int | None = None
    versions: list[TranslationVersion] = Field(default_factory=list)
    attempts: list[AttemptRecord] = Field(default_factory=list)
    unresolved_errors: list[MQMError] = Field(default_factory=list)
    failure_reasons: list[str] = Field(default_factory=list)
    tm_hit: bool = Field(
        default=False, description="Translation Memory 정확 매칭으로 초기 번역을 대체했는지"
    )
    tm_source_id: str | None = Field(
        default=None, description="매칭된 TM 항목의 source_id (매칭 없으면 None)"
    )
    agent_decisions: list[str] = Field(
        default_factory=list,
        description="고정 Workflow 실패 후 Agent(Qwen/OpenAI)가 내린 전략 선택과 근거",
    )

    @property
    def current_version(self) -> TranslationVersion:
        if not self.versions:
            raise ValueError("저장된 번역 버전이 없습니다.")
        return self.versions[-1]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

