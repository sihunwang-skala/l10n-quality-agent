"""실제 OpenAI 기반 에스컬레이션 단계 + HITL "AI에게 추가 지시" 수정기.

OPENAI_API_KEY가 (.env나 셸 환경에) 실제로 설정된 경우에만 동작한다 - 키가
없으면 호출하는 쪽에서 OpenAIAgentMock으로 대체한다(agent.py 참고). OpenAI가
후보를 만들어도 MQM 판정은 항상 로컬 Qwen 모델(self.chains.evaluate)이
맡아서, 어느 모델이 수정했든 품질은 같은 기준으로 평가된다 - 가드레일
(validate_candidate/validate_spans)도 동일하게 적용된다.

웹 검색이나 Tool 사용은 아직 없다 - 실제 연동의 첫 단계라 단순 생성으로만
범위를 한정했고, OpenAI 자동 단계는 최대 1회만 실행한다.
"""

from __future__ import annotations

import os
from pathlib import Path

from .chains import ChainProvider
from .schemas import AgentStatus, AttemptRecord, MQMResult, RunRecord, TranslationRequest
from .validation import validate_candidate, validate_spans

OPENAI_MODEL_NAME = "gpt-5-mini"


def _load_dotenv_once() -> None:
    """새 의존성 없이 만든 아주 작은 .env 로더 - 환경변수에 이미 있는 값은
    건드리지 않고, 프로젝트 루트의 .env만 읽는다."""
    if getattr(_load_dotenv_once, "_done", False):
        return
    _load_dotenv_once._done = True  # type: ignore[attr-defined]
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


def is_openai_configured() -> bool:
    _load_dotenv_once()
    return bool(os.environ.get("OPENAI_API_KEY"))


def _chat_openai(temperature: float = 0):
    _load_dotenv_once()
    from langchain_openai import ChatOpenAI  # 선택적 의존성이라 지연 import

    return ChatOpenAI(model=OPENAI_MODEL_NAME, temperature=temperature)


class OpenAIAgent:
    """실제 에스컬레이션 단계: Qwen Agent가 못 고친 걸 한 번 더 시도한다.
    같은 가드레일과 MQM 재평가를 그대로 거친다."""

    def __init__(self, chains: ChainProvider, model=None) -> None:
        self.chains = chains
        self.model = model or _chat_openai()

    def run(self, record: RunRecord, progress_callback=None) -> RunRecord:
        if record.status != AgentStatus.HUMAN_REVIEW_REQUIRED or not record.versions:
            return record

        request = record.request
        current = record.current_version.translation
        errors = record.unresolved_errors
        feedback = "; ".join(
            f"{a.category}: {'; '.join(a.failure_reasons)}"
            for a in record.attempts
            if not a.accepted
        )
        error_summary = "; ".join(
            f"{e.category}/{e.severity}: {e.explanation}" for e in errors
        ) or "없음"

        prompt = (
            "당신은 시니어 현지화 검수자입니다. 로컬 모델이 해결하지 못한 번역 오류를 "
            "마지막으로 한 번 더 시도해 수정하세요. 원문의 의미, 숫자, 단위, 보호 용어는 "
            "절대 바꾸지 마세요. 수정된 번역문만 출력하세요.\n\n"
            f"원문: {request.source}\n"
            f"현재 번역: {current}\n"
            f"목표 언어: {request.target_language}\n목표 국가: {request.target_country}\n"
            f"보호 용어: {request.protected_terms}\n"
            f"미해결 오류: {error_summary}\n"
            f"이전 실패 이력: {feedback or '없음'}"
        )
        candidate = self.model.invoke(prompt).content.strip()
        record.agent_decisions.append(f"[OpenAI] 후보 생성: {candidate}")
        if progress_callback:
            progress_callback(f"[OpenAI] 후보 생성: {candidate}")

        failure_reasons = validate_candidate(request, current, candidate)
        after: MQMResult | None = None
        if not failure_reasons:
            after = self.chains.evaluate(request, candidate)  # MQM 판정은 계속 Qwen이 중립적으로
            failure_reasons.extend(validate_spans(after, candidate))

        accepted = not failure_reasons
        record.attempts.append(
            AttemptRecord(
                step=len(record.attempts) + 1,
                category=errors[0].category if errors else "style",
                attempt=1,
                input_translation=current,
                candidate=candidate,
                selected_errors=errors,
                accepted=accepted,
                failure_reasons=failure_reasons,
                mqm_before=MQMResult(errors=errors),
                mqm_after=after,
            )
        )

        if accepted and after is not None:
            from .schemas import TranslationVersion

            new_version = TranslationVersion(
                version=len(record.versions) + 1,
                translation=candidate,
                based_on_version=record.current_version.version,
                mqm=after,
            )
            record.versions.append(new_version)
            record.unresolved_errors = list(after.errors)
            record.status = (
                AgentStatus.AWAITING_HUMAN_APPROVAL if not after.errors else AgentStatus.HUMAN_REVIEW_REQUIRED
            )
            if progress_callback:
                progress_callback(f"[OpenAI] 후보 채택 · v{new_version.version}")
        else:
            if progress_callback:
                progress_callback(f"[OpenAI] 후보 거부: {'; '.join(failure_reasons)}")
        return record


def openai_user_revise(request: TranslationRequest, translation: str, instruction: str, model=None) -> str:
    """HITL 'AI에게 추가 지시' 경로용 chains.user_revise()의 실제 OpenAI
    버전. 호출하는 쪽이 결과를 일반 가드레일/MQM 파이프라인에 그대로 태운다
    (로컬 Qwen 경로와 동일) - 이 함수는 텍스트 제안만 한다."""
    model = model or _chat_openai()
    prompt = (
        "아래 기존 번역을 사용자의 추가 지시에 맞게 다시 수정하세요. "
        "원문의 의미, 숫자, 단위, 보호 용어는 바꾸지 마세요. 수정된 번역문만 출력하세요.\n\n"
        f"원문: {request.source}\n기존 번역: {translation}\n"
        f"목표 언어: {request.target_language}\n목표 국가: {request.target_country}\n"
        f"보호 용어: {request.protected_terms}\n추가 지시: {instruction}"
    )
    return model.invoke(prompt).content.strip()
