"""LCEL 체인과 파이썬 제어 흐름으로 만든 적응형 번역 품질 Workflow."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from .chains import ChainProvider, OllamaChains
from .config import (
    MAX_ATTEMPTS_PER_CATEGORY,
    MAX_TOTAL_ATTEMPTS,
    PRIORITY,
    PROMPT_VERSIONS,
)
from .schemas import (
    AgentStatus,
    AttemptRecord,
    MQMError,
    MQMResult,
    RunRecord,
    TranslationRequest,
    TranslationVersion,
)
from .storage import JsonRunStore
from .tm import TranslationMemory
from .validation import (
    category_count,
    critical_count,
    validate_candidate,
    validate_initial,
    validate_spans,
)


def select_category(errors: list[MQMError]) -> str | None:
    if not errors:
        return None
    return min(errors, key=lambda error: PRIORITY[error.category]).category


class QualityWorkflow:
    def __init__(
        self,
        chains: ChainProvider | None = None,
        store: JsonRunStore | None = None,
        tm: TranslationMemory | None = None,
    ) -> None:
        self.chains = chains or OllamaChains()
        self.store = store or JsonRunStore()
        # 없어도 동작은 동일 - TM 히트 시 번역 호출 자체를 대체할 뿐이다.
        self.tm = tm

    def run(
        self,
        request: TranslationRequest,
        *,
        starting_translation: str | None = None,
        parent_run_id: str | None = None,
        parent_version: int | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> RunRecord:
        # 기본 진입점: TM 조회 → 초기 번역 → 결정적 검사 → MQM 평가 순서다.
        record = RunRecord(
            request=request,
            status=AgentStatus.EVALUATING,
            prompt_versions=PROMPT_VERSIONS.copy(),
            parent_run_id=parent_run_id,
            parent_version=parent_version,
        )
        try:
            self._emit(progress_callback, "입력 확인 완료")
            tm_match = None
            if starting_translation is None and self.tm is not None:
                tm_match = self.tm.lookup(request.source, request.target_language)
            if tm_match is not None:
                translation = tm_match.target_text
                record.tm_hit = True
                record.tm_source_id = tm_match.source_id
                self._emit(
                    progress_callback,
                    f"[TM] 정확 매칭 발견(source_id={tm_match.source_id}) · 신규 번역 생략",
                )
            else:
                translation = starting_translation or self.chains.translate(request)
            self._emit(progress_callback, f"[1] 초기 번역 완료: {translation}")
            initial = TranslationVersion(
                version=1,
                translation=translation,
                based_on_version=parent_version,
                instruction=request.additional_instruction,
            )
            record.versions.append(initial)
            initial_failures = validate_initial(request, translation)
            if initial_failures:
                # 숫자·단위·보호 용어 문제는 자동 수정하지 않고 사람 검토로 보낸다.
                record.status = AgentStatus.HUMAN_REVIEW_REQUIRED
                record.failure_reasons.extend(initial_failures)
                self.store.save(record)
                self._emit(
                    progress_callback,
                    f"안전 검증 실패 · Rollback: {'; '.join(initial_failures)}",
                )
                return record
            self.store.save(record)
            return self._improve(record, progress_callback)
        except Exception as exc:
            record.status = AgentStatus.HUMAN_REVIEW_REQUIRED
            record.failure_reasons.append(f"Workflow 예외: {type(exc).__name__}: {exc}")
            self.store.save(record)
            self._emit(progress_callback, record.failure_reasons[-1])
            return record

    def _improve(
        self,
        record: RunRecord,
        progress_callback: Callable[[str], None] | None = None,
    ) -> RunRecord:
        # 고정 우선순위 수정 루프. UI의 Agent-first 경로는 run_via_agent()를 사용한다.
        request = record.request
        current = record.current_version.translation
        evaluation = self.chains.evaluate(request, current)
        self._emit(
            progress_callback,
            f"[2] MQM 평가 완료: 오류 {len(evaluation.errors)}개",
        )
        record.current_version.mqm = evaluation
        span_warnings = validate_spans(evaluation, current)
        record.failure_reasons.extend(span_warnings)
        self.store.save(record)

        if critical_count(evaluation):
            return self._require_human(
                record, evaluation, "Critical 오류는 자동 수정하지 않고 사람 검토로 전환"
            )

        attempts_by_category: dict[str, int] = defaultdict(int)
        while evaluation.errors:
            if len(record.attempts) >= MAX_TOTAL_ATTEMPTS:
                return self._require_human(
                    record, evaluation, f"전체 수정 상한 {MAX_TOTAL_ATTEMPTS}회 도달"
                )

            category = select_category(evaluation.errors)
            if category is None:
                break
            selected = [e for e in evaluation.errors if e.category == category]
            self._emit(
                progress_callback,
                f"[3] 수정 대상 선택: {category} ({len(selected)}개)",
            )
            if attempts_by_category[category] >= MAX_ATTEMPTS_PER_CATEGORY:
                return self._require_human(
                    record,
                    evaluation,
                    f"{category} 영역 수정 {MAX_ATTEMPTS_PER_CATEGORY}회 실패",
                )

            feedback = "\n".join(
                reason
                for attempt in record.attempts
                if attempt.category == category and not attempt.accepted
                for reason in attempt.failure_reasons
            )
            attempts_by_category[category] += 1
            record.status = AgentStatus.REVISING
            candidate = self.chains.revise(
                request,
                current,
                category,
                selected,
                failure_feedback=feedback,
            )
            self._emit(
                progress_callback,
                f"[4] {category} 수정 후보 생성 ({attempts_by_category[category]}/"
                f"{MAX_ATTEMPTS_PER_CATEGORY}): {candidate}",
            )
            failure_reasons = validate_candidate(request, current, candidate)
            after: MQMResult | None = None

            if not failure_reasons:
                after = self.chains.evaluate(request, candidate)
                failure_reasons.extend(validate_spans(after, candidate))
                if critical_count(after) > critical_count(evaluation):
                    failure_reasons.append("새로운 Critical 오류가 발생함")
                if category_count(after, category) >= category_count(evaluation, category):
                    failure_reasons.append(f"수정 대상 {category} 오류가 감소하지 않음")

            accepted = not failure_reasons
            attempt = AttemptRecord(
                step=len(record.attempts) + 1,
                category=category,
                attempt=attempts_by_category[category],
                input_translation=current,
                candidate=candidate,
                selected_errors=selected,
                accepted=accepted,
                failure_reasons=failure_reasons,
                mqm_before=evaluation,
                mqm_after=after,
            )
            record.attempts.append(attempt)

            if accepted and after is not None:
                new_version = TranslationVersion(
                    version=len(record.versions) + 1,
                    translation=candidate,
                    based_on_version=record.current_version.version,
                    mqm=after,
                )
                record.versions.append(new_version)
                current = candidate
                evaluation = after
                record.status = AgentStatus.EVALUATING
                self._emit(progress_callback, f"[4] 수정 후보 채택 · v{new_version.version}")
                self._emit(
                    progress_callback,
                    f"[5] 전체 MQM 재평가 완료: 오류 {len(after.errors)}개",
                )
            elif attempts_by_category[category] >= MAX_ATTEMPTS_PER_CATEGORY:
                self._emit(
                    progress_callback,
                    f"[4] 후보 거부 · 이전 번역으로 Rollback: {'; '.join(failure_reasons)}",
                )
                self.store.save(record)
                return self._require_human(
                    record,
                    evaluation,
                    f"{category} 영역 수정 {MAX_ATTEMPTS_PER_CATEGORY}회 실패",
                )
            else:
                self._emit(
                    progress_callback,
                    f"[4] 후보 거부 · 이전 번역으로 Rollback: {'; '.join(failure_reasons)}",
                )
            self.store.save(record)

        record.unresolved_errors = []
        record.status = AgentStatus.AWAITING_HUMAN_APPROVAL
        self.store.save(record)
        self._emit(progress_callback, "자동 검사 통과 · 사람 최종 승인 대기")
        return record

    def run_via_agent(
        self,
        request: TranslationRequest,
        agent,
        *,
        progress_callback: Callable[[str], None] | None = None,
    ) -> RunRecord:
        """번역 한 번 하고 수정 판단은 전부 Agent에게 넘긴다 - 고정 우선순위
        `_improve()` 루프는 아예 타지 않는다. TM 조회는 그대로 적용된다.
        """
        record = RunRecord(
            request=request,
            status=AgentStatus.HUMAN_REVIEW_REQUIRED,  # 바로 아래 Agent로 넘어간다
            prompt_versions=PROMPT_VERSIONS.copy(),
        )
        try:
            self._emit(progress_callback, "입력 확인 완료")
            tm_match = self.tm.lookup(request.source, request.target_language) if self.tm else None
            if tm_match is not None:
                translation = tm_match.target_text
                record.tm_hit = True
                record.tm_source_id = tm_match.source_id
                self._emit(
                    progress_callback,
                    f"[TM] 정확 매칭 발견(source_id={tm_match.source_id}) · 신규 번역 생략",
                )
            else:
                translation = self.chains.translate(request)
            record.versions.append(TranslationVersion(version=1, translation=translation))
            self._emit(progress_callback, f"[1] 초기 번역 완료: {translation}")

            initial_failures = validate_initial(request, translation)
            if initial_failures:
                record.failure_reasons.extend(initial_failures)
                self._emit(
                    progress_callback,
                    f"초기 안전 검증 경고(Agent가 이어서 조사): {'; '.join(initial_failures)}",
                )
            self.store.save(record)

            record = agent.run(record, progress_callback=progress_callback)
            self.store.save(record)
            return record
        except Exception as exc:
            record.status = AgentStatus.HUMAN_REVIEW_REQUIRED
            record.failure_reasons.append(f"Workflow 예외: {type(exc).__name__}: {exc}")
            self.store.save(record)
            self._emit(progress_callback, record.failure_reasons[-1])
            return record

    def approve(self, run_id: str) -> RunRecord:
        record = self.store.load(run_id)
        if record.status != AgentStatus.AWAITING_HUMAN_APPROVAL:
            raise ValueError("승인 대기 상태의 실행만 승인할 수 있습니다.")
        record.status = AgentStatus.APPROVED
        self.store.save(record)
        return record

    def reject(self, run_id: str) -> RunRecord:
        record = self.store.load(run_id)
        record.status = AgentStatus.REJECTED
        self.store.save(record)
        return record

    def apply_human_edit(
        self,
        run_id: str,
        new_translation: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> RunRecord:
        """HITL 직접 수정 - 사람이 번역문을 손으로 다시 쓴다.

        다른 후보와 똑같은 가드레일을 거치므로 자동 승인되지 않는다. 호출당
        수정 1회이며, 다시 고칠지는 호출하는 쪽이 판단한다.
        """
        record = self.store.load(run_id)
        current = record.current_version.translation
        failure_reasons = validate_candidate(record.request, current, new_translation)
        evaluation: MQMResult | None = None
        if not failure_reasons:
            evaluation = self.chains.evaluate(record.request, new_translation)
            failure_reasons.extend(validate_spans(evaluation, new_translation))

        new_version = TranslationVersion(
            version=len(record.versions) + 1,
            translation=new_translation,
            based_on_version=record.current_version.version,
            instruction="[사람 직접 수정]",
            mqm=evaluation,
        )
        record.versions.append(new_version)

        if failure_reasons:
            record.status = AgentStatus.HUMAN_REVIEW_REQUIRED
            record.failure_reasons.extend(failure_reasons)
            self._emit(progress_callback, f"직접 수정 검증 실패: {'; '.join(failure_reasons)}")
        elif evaluation is not None and evaluation.errors:
            record.unresolved_errors = evaluation.errors
            record.status = AgentStatus.HUMAN_REVIEW_REQUIRED
            self._emit(progress_callback, f"직접 수정 후 재평가: 오류 {len(evaluation.errors)}개 남음")
        else:
            record.unresolved_errors = []
            record.status = AgentStatus.AWAITING_HUMAN_APPROVAL
            self._emit(progress_callback, "직접 수정 검증 통과 · 사람 최종 승인 대기")

        self.store.save(record)
        return record

    def revise_from_version(
        self,
        run_id: str,
        version: int,
        additional_instruction: str,
        progress_callback: Callable[[str], None] | None = None,
        reviser: Callable[[TranslationRequest, str], str] | None = None,
    ) -> RunRecord:
        """`reviser`는 기본값이 self.chains.user_revise(로컬 Qwen)이다. 이 한
        단계(수정 문안 생성)만 다른 모델을 쓰고 싶으면 예컨대
        openai_agent.openai_user_revise를 넘기면 된다 - 그 뒤 가드레일/MQM
        파이프라인은 어느 쪽이든 동일하다."""
        parent = self.store.load(run_id)
        selected = next((v for v in parent.versions if v.version == version), None)
        if selected is None:
            raise ValueError(f"v{version}을 찾을 수 없습니다.")
        request = parent.request.model_copy(
            update={"additional_instruction": additional_instruction}
        )
        self._emit(progress_callback, f"v{version} 로드 · 추가 지시 적용 시작")
        reviser = reviser or self.chains.user_revise
        revised = reviser(request, selected.translation)
        self._emit(progress_callback, f"[1] 추가 지시 수정 완료: {revised}")
        return self.run(
            request,
            starting_translation=revised,
            parent_run_id=run_id,
            parent_version=version,
            progress_callback=progress_callback,
        )

    def _require_human(
        self, record: RunRecord, evaluation: MQMResult, reason: str
    ) -> RunRecord:
        record.status = AgentStatus.HUMAN_REVIEW_REQUIRED
        record.unresolved_errors = evaluation.errors
        record.failure_reasons.append(reason)
        self.store.save(record)
        return record

    @staticmethod
    def _emit(callback: Callable[[str], None] | None, message: str) -> None:
        if callback is not None:
            callback(message)
