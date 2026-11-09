"""Qwen Agent: 고정 우선순위 Workflow(workflow.py)가 포기하고 RunRecord를
HUMAN_REVIEW_REQUIRED로 넘긴 뒤에만 개입한다.

Tool-calling Agent가 아니라 Planner Chain이다 - LLM은 전략 이름만 고르고
(QwenAgentPlanner.plan), 실제 실행은 고정 Workflow와 똑같은
revise/evaluate/validate 함수를 파이썬이 그대로 호출한다. 후보 채택 여부는
LLM이 아니라 항상 Python Validator와 MQM 재평가가 결정한다.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .chains import ChainProvider
from .schemas import (
    AgentStatus,
    AttemptRecord,
    MQMError,
    MQMResult,
    RunRecord,
    TranslationVersion,
)
from .validation import category_count, critical_count, validate_candidate, validate_spans

MAX_AGENT_STRATEGIES = 2

StrategyName = Literal[
    "accuracy", "terminology", "spelling", "grammar", "style", "fluency", "human_review"
]

AGENT_PLANNER_SYSTEM = """당신은 번역 품질 Agent Planner입니다.
고정 우선순위 Workflow가 카테고리별 2회 수정에 실패해 넘어온 사례를 검토합니다.
이미 실패한 전략을 근거 없이 반복하지 마세요.
해결 가능성이 낮다고 판단되면 human_review를 선택하세요.
당신은 후보 번역문을 직접 만들지 않습니다 - 다음에 시도할 전략 하나만 고르세요."""


class AgentPlan(BaseModel):
    strategy: StrategyName = Field(
        description="다음에 시도할 전문 수정 영역, 또는 더 시도할 가치가 없으면 human_review"
    )
    reasoning: str = Field(description="과거 실패 이력에 근거한 선택 이유")


class PlannerModel(Protocol):
    def invoke(self, values: dict) -> AgentPlan: ...


class QwenAgentPlanner:
    """ChatOllama 구조화 출력 호출 하나를 감싼 것뿐 - Tool-calling Agent 아님."""

    def __init__(self, model) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", AGENT_PLANNER_SYSTEM),
                (
                    "human",
                    "원문: {source}\n현재 번역: {translation}\n"
                    "목표 언어: {target_language}\n목표 국가: {target_country}\n"
                    "남은 오류: {unresolved_errors}\n"
                    "이미 시도한 전략: {tried_categories}\n"
                    "과거 실패 사유: {feedback}",
                ),
            ]
        )
        self.chain = prompt | model.with_structured_output(AgentPlan, method="json_schema")

    def plan(self, **values) -> AgentPlan:
        result = self.chain.invoke(values)
        return result if isinstance(result, AgentPlan) else AgentPlan.model_validate(result)


class QwenAgent:
    """Planner가 고른 전략을 고정 Workflow의 revise/evaluate/validate 함수로
    실행한다. 고정 Workflow가 이미 포기한 건에만 개입한다.
    """

    def __init__(self, chains: ChainProvider, planner: PlannerModel | None = None) -> None:
        self.chains = chains
        self.planner = planner or QwenAgentPlanner(chains.model)

    def run(
        self, record: RunRecord, progress_callback: Callable[[str], None] | None = None
    ) -> RunRecord:
        # Agent는 초기 번역과 안전 검증이 끝난 검토 대기 건만 처리한다.
        if record.status != AgentStatus.HUMAN_REVIEW_REQUIRED or not record.versions:
            return record

        request = record.request
        current = record.current_version.translation
        errors: list[MQMError] = list(record.unresolved_errors)

        if not errors:
            # 보호 용어·숫자/단위 같은 결정적 검사만으로도 여기 넘어올 수 있어
            # MQM이 아직 안 돌았을 수 있다 - 그럴 땐 직접 한 번 돌려본다.
            mqm_result = self.chains.evaluate(request, current)
            errors = list(mqm_result.errors)
            original_reason = "; ".join(record.failure_reasons) or "알 수 없음"
            note = (
                f"[조사] 원인 파악을 위해 MQM 재평가 실행 (원래 실패 사유: {original_reason}) "
                f"-> 오류 {len(errors)}개 발견"
            )
            if errors:
                note += "\n" + "\n".join(
                    f"{index}. [{error.category} · {error.severity}] "
                    f"{error.explanation}"
                    for index, error in enumerate(errors, 1)
                )
            record.agent_decisions.append(note)
            self._emit(progress_callback, f"[Agent] {note}")
            if not errors:
                conclusion = (
                    "[조사 결론] MQM 재평가에서 추가 오류를 찾지 못함 - "
                    "원래는 결정적 검증(숫자/단위·보호 용어 등) 실패였음에 유의하고 승인 대기로 전환"
                )
                record.agent_decisions.append(conclusion)
                self._emit(progress_callback, f"[Agent] {conclusion}")
                record.unresolved_errors = []
                record.status = AgentStatus.AWAITING_HUMAN_APPROVAL
                return record

        tried = {attempt.category for attempt in record.attempts}

        # Planner가 고른 한 영역만 수정하고, 후보마다 같은 검증을 다시 거친다.
        for i in range(MAX_AGENT_STRATEGIES):
            if not errors:
                break
            feedback = "; ".join(
                f"{a.category}: {'; '.join(a.failure_reasons)}"
                for a in record.attempts
                if not a.accepted
            )
            plan = self.planner.plan(
                source=request.source,
                translation=current,
                target_language=request.target_language,
                target_country=request.target_country,
                unresolved_errors=[(e.category, e.severity, e.explanation) for e in errors],
                tried_categories=sorted(tried),
                feedback=feedback or "없음",
            )
            record.agent_decisions.append(
                f"[전략 {i + 1}/{MAX_AGENT_STRATEGIES}] {plan.strategy}: {plan.reasoning}"
            )
            self._emit(
                progress_callback,
                f"[Agent {i + 1}/{MAX_AGENT_STRATEGIES}] 전략 선택: {plan.strategy} - {plan.reasoning}",
            )
            if plan.strategy == "human_review":
                break

            selected = [e for e in errors if e.category == plan.strategy]
            if not selected:
                record.agent_decisions.append(
                    f"[{plan.strategy}] 호출 안 함 - 해당 카테고리에 미해결 오류 없어 건너뜀"
                )
                tried.add(plan.strategy)
                continue

            record.agent_decisions.append(f"[{plan.strategy}] 수정 Tool 호출")
            candidate = self.chains.revise(
                request, current, plan.strategy, selected, failure_feedback=feedback
            )
            failure_reasons = validate_candidate(request, current, candidate)
            after: MQMResult | None = None
            if not failure_reasons:
                after = self.chains.evaluate(request, candidate)
                # LLM의 판단만으로 후보를 채택하지 않고, Python 검사와 MQM을 함께 통과시킨다.
                failure_reasons.extend(validate_spans(after, candidate))
                if critical_count(after) > critical_count(MQMResult(errors=errors)):
                    failure_reasons.append("새로운 Critical 오류가 발생함")
                if category_count(after, plan.strategy) >= category_count(
                    MQMResult(errors=errors), plan.strategy
                ):
                    failure_reasons.append(f"수정 대상 {plan.strategy} 오류가 감소하지 않음")

            accepted = not failure_reasons
            record.attempts.append(
                AttemptRecord(
                    step=len(record.attempts) + 1,
                    category=plan.strategy,
                    attempt=1,
                    input_translation=current,
                    candidate=candidate,
                    selected_errors=selected,
                    accepted=accepted,
                    failure_reasons=failure_reasons,
                    mqm_before=MQMResult(errors=errors),
                    mqm_after=after,
                )
            )
            if accepted and after is not None:
                new_version = TranslationVersion(
                    version=len(record.versions) + 1,
                    translation=candidate,
                    based_on_version=record.current_version.version,
                    mqm=after,
                )
                record.versions.append(new_version)
                current = candidate
                errors = list(after.errors)
                self._emit(
                    progress_callback,
                    f"[Agent][{plan.strategy}] 후보 채택 · v{new_version.version}: {candidate}",
                )
            else:
                self._emit(
                    progress_callback,
                    f"[Agent][{plan.strategy}] 후보 거부: {candidate} "
                    f"(사유: {'; '.join(failure_reasons)})",
                )
            tried.add(plan.strategy)

        record.unresolved_errors = errors
        record.status = (
            AgentStatus.AWAITING_HUMAN_APPROVAL if not errors else AgentStatus.HUMAN_REVIEW_REQUIRED
        )
        return record

    @staticmethod
    def _emit(callback: Callable[[str], None] | None, message: str) -> None:
        if callback is not None:
            callback(message)


class OpenAIAgentMock:
    """OpenAI 에스컬레이션 단계의 대역 - 실제 API는 절대 호출하지 않는다.

    키가 없어도 Workflow -> Qwen Agent -> OpenAI -> HITL로 이어지는 연동
    경로를 끝까지 확인할 수 있게 해준다. 실제 구현은 같은 `.run()` 시그니처만
    맞추면 된다.
    """

    def run(
        self, record: RunRecord, progress_callback: Callable[[str], None] | None = None
    ) -> RunRecord:
        if record.status != AgentStatus.HUMAN_REVIEW_REQUIRED or not record.versions:
            return record
        record.agent_decisions.append(
            "[OpenAI Agent - MOCK, 실제 API 미호출] 연동 인터페이스만 검증됨. "
            "실제 구현 시 이 지점에서 OpenAI 모델이 전략을 재선택합니다."
        )
        QwenAgent._emit(
            progress_callback,
            "[OpenAI Agent] MOCK 실행 - 실제 API 호출 없음, 상태 변경 없음",
        )
        return record
