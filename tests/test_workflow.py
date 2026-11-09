from __future__ import annotations

from collections import deque

import pytest
from pydantic import ValidationError

from l10n_quality_agent.schemas import (
    AgentStatus,
    MQMError,
    MQMResult,
    TranslationRequest,
)
from l10n_quality_agent.storage import JsonRunStore
from l10n_quality_agent.validation import validate_candidate, validate_initial
from l10n_quality_agent.workflow import QualityWorkflow, select_category


class FakeChains:
    def __init__(self, translations, evaluations, revisions=(), user_revisions=()):
        self.translations = deque(translations)
        self.evaluations = deque(evaluations)
        self.revisions = deque(revisions)
        self.user_revisions = deque(user_revisions)
        self.feedback = []

    def translate(self, request):
        return self.translations.popleft()

    def evaluate(self, request, translation):
        return self.evaluations.popleft()

    def revise(self, request, translation, category, errors, failure_feedback=""):
        self.feedback.append(failure_feedback)
        return self.revisions.popleft()

    def user_revise(self, request, translation):
        return self.user_revisions.popleft()


def request(source="이 냉장고는 에너지 소비를 20% 줄입니다.", terms=None):
    return TranslationRequest(
        source=source,
        target_language="English",
        target_country="Australia",
        protected_terms=terms or [],
    )


def error(category="grammar", span="reduce", severity="major"):
    return MQMError(
        category=category,
        severity=severity,
        span=span,
        explanation="테스트 오류",
        suggested_fix="reduces",
    )


def test_schema_rejects_unknown_mqm_category():
    with pytest.raises(ValidationError):
        MQMError(
            category="dne",
            severity="minor",
            span="",
            explanation="invalid",
        )


def test_priority_selects_accuracy_before_grammar_and_fluency():
    errors = [error("fluency"), error("grammar"), error("accuracy")]
    assert select_category(errors) == "accuracy"


def test_candidate_rejects_number_change_and_protected_term_change():
    req = request("AcmeVision OLED는 에너지를 20% 절감합니다.", ["AcmeVision OLED"])
    reasons = validate_candidate(
        req,
        "AcmeVision OLED saves 20% energy.",
        "OLED TV saves 30% energy.",
    )
    assert any("보호 용어" in reason for reason in reasons)
    assert any("숫자 또는 단위" in reason for reason in reasons)


def test_initial_translation_rejects_missing_protected_term():
    req = request("AcmeVision OLED로 영상을 보세요.", ["AcmeVision OLED"])
    assert validate_initial(req, "Watch vivid images on the OLED TV.")


def test_localized_korean_date_is_not_rejected_as_number_change():
    req = request("기간 한정 세일은 26년 9월까지입니다.")
    assert not validate_initial(req, "The limited sale runs until September 2026.")


def test_localized_manwon_is_equivalent_to_won_amount():
    req = request("가격은 90만원이며 무게는 100g 줄었습니다.")
    assert not validate_initial(
        req, "The price is 900,000 won and the weight decreased by 100g."
    )


def test_critical_error_requires_human_without_revision(tmp_path):
    critical = MQMResult(errors=[error("accuracy", "30%", "critical")])
    fake = FakeChains(["It saves 30%."], [critical])
    record = QualityWorkflow(fake, JsonRunStore(tmp_path)).run(
        request("에너지를 절약합니다.")
    )
    assert record.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert not record.attempts


def test_successful_revision_creates_version_and_waits_for_approval(tmp_path):
    before = MQMResult(errors=[error()])
    after = MQMResult(errors=[])
    fake = FakeChains(
        ["This refrigerator reduce energy consumption by 20%."],
        [before, after],
        ["This refrigerator reduces energy consumption by 20%."],
    )
    workflow = QualityWorkflow(fake, JsonRunStore(tmp_path))
    record = workflow.run(request())
    assert record.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert len(record.versions) == 2
    assert record.attempts[0].accepted is True
    assert "20%" in record.current_version.translation


def test_progress_callback_reports_visible_workflow_stages(tmp_path):
    messages = []
    fake = FakeChains(["A valid translation."], [MQMResult(errors=[])])
    record = QualityWorkflow(fake, JsonRunStore(tmp_path)).run(
        request("올바른 문장입니다."), progress_callback=messages.append
    )
    assert record.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert any(message.startswith("[1]") for message in messages)
    assert any(message.startswith("[2]") for message in messages)
    assert messages[-1] == "자동 검사 통과 · 사람 최종 승인 대기"


def test_retry_includes_failure_feedback_and_stops_after_two(tmp_path):
    before = MQMResult(errors=[error()])
    fake = FakeChains(
        ["This refrigerator reduce energy consumption by 20%."],
        [before],
        [
            "This refrigerator reduces energy consumption by 30%.",
            "This refrigerator reduces energy consumption by 40%.",
        ],
    )
    workflow = QualityWorkflow(fake, JsonRunStore(tmp_path))
    record = workflow.run(request())
    assert record.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert len(record.attempts) == 2
    assert all(not attempt.accepted for attempt in record.attempts)
    assert fake.feedback[0] == ""
    assert "숫자" in fake.feedback[1]
    assert record.current_version.translation.endswith("20%.")


def test_approval_rejection_and_json_reload(tmp_path):
    store = JsonRunStore(tmp_path)
    first = QualityWorkflow(
        FakeChains(["Experience innovation."], [MQMResult(errors=[])]), store
    ).run(request("혁신을 경험하세요."))
    approved = QualityWorkflow(FakeChains([], []), store).approve(first.run_id)
    assert approved.status == AgentStatus.APPROVED
    assert store.load(first.run_id).status == AgentStatus.APPROVED

    second = QualityWorkflow(
        FakeChains(["Another translation."], [MQMResult(errors=[])]), store
    ).run(request("다른 문장입니다."))
    rejected = QualityWorkflow(FakeChains([], []), store).reject(second.run_id)
    assert rejected.status == AgentStatus.REJECTED


def test_revise_from_previous_version_creates_linked_run(tmp_path):
    store = JsonRunStore(tmp_path)
    parent = QualityWorkflow(
        FakeChains(["Experience innovative technology."], [MQMResult(errors=[])]),
        store,
    ).run(request("혁신적인 기술을 경험하세요."))
    fake = FakeChains(
        [],
        [MQMResult(errors=[])],
        user_revisions=["Experience innovation."],
    )
    child = QualityWorkflow(fake, store).revise_from_version(
        parent.run_id, 1, "더 간결하게"
    )
    assert child.parent_run_id == parent.run_id
    assert child.parent_version == 1
    assert child.current_version.translation == "Experience innovation."
    assert child.status == AgentStatus.AWAITING_HUMAN_APPROVAL


def _human_review_parent(store, translation="A rough translation."):
    # Critical severity short-circuits straight to HUMAN_REVIEW_REQUIRED
    # without ever calling chains.revise() - the clean, minimal setup for
    # a record apply_human_edit() can then act on.
    critical = MQMResult(errors=[error("accuracy", translation, "critical")])
    return QualityWorkflow(FakeChains([translation], [critical]), store).run(
        request("이 문장은 자연스럽게 번역되어야 합니다.")
    )


def test_apply_human_edit_accepts_a_clean_edit(tmp_path):
    store = JsonRunStore(tmp_path)
    parent = _human_review_parent(store)
    assert parent.status == AgentStatus.HUMAN_REVIEW_REQUIRED

    fake = FakeChains([], [MQMResult(errors=[])])
    edited = QualityWorkflow(fake, store).apply_human_edit(
        parent.run_id, "A much better hand-edited translation."
    )
    assert edited.current_version.translation == "A much better hand-edited translation."
    assert edited.current_version.instruction == "[사람 직접 수정]"
    assert edited.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert edited.unresolved_errors == []


def test_apply_human_edit_rejects_protected_term_removal(tmp_path):
    store = JsonRunStore(tmp_path)
    req = request("AcmeVision OLED로 영상을 보세요.", terms=["AcmeVision OLED"])
    critical = MQMResult(errors=[error("accuracy", "Watch on AcmeVision OLED.", "critical")])
    parent = QualityWorkflow(FakeChains(["Watch on AcmeVision OLED."], [critical]), store).run(req)

    fake = FakeChains([], [])
    edited = QualityWorkflow(fake, store).apply_human_edit(
        parent.run_id, "Watch on an OLED TV."  # drops the protected term
    )
    assert edited.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert any("보호 용어" in reason for reason in edited.failure_reasons)
    # Guardrail rejection must not even call evaluate() - chains.evaluations
    # deque was left empty on purpose; popping it would raise IndexError.


def test_apply_human_edit_reevaluates_and_can_still_leave_errors(tmp_path):
    store = JsonRunStore(tmp_path)
    parent = _human_review_parent(store)

    fake = FakeChains([], [MQMResult(errors=[error("style", span="")])])
    edited = QualityWorkflow(fake, store).apply_human_edit(
        parent.run_id, "A slightly better but still imperfect translation."
    )
    assert edited.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert len(edited.unresolved_errors) == 1
    assert edited.unresolved_errors[0].category == "style"


def test_run_via_agent_skips_fixed_priority_loop_and_uses_agent_decision(tmp_path):
    from l10n_quality_agent.agent import AgentPlan, QwenAgent

    class OneShotPlanner:
        def __init__(self, plan):
            self._plan = plan

        def plan(self, **_values):
            return self._plan

    store = JsonRunStore(tmp_path)
    fake_chains = FakeChains(
        ["Initial rough translation."],
        [MQMResult(errors=[error("fluency")]), MQMResult(errors=[])],
        revisions=["Improved translation."],
    )
    workflow = QualityWorkflow(fake_chains, store)
    agent = QwenAgent(
        fake_chains, OneShotPlanner(AgentPlan(strategy="fluency", reasoning="바로 수정"))
    )

    record = workflow.run_via_agent(
        request("이 문장은 자연스럽게 번역되어야 합니다."), agent
    )

    assert record.current_version.translation == "Improved translation."
    assert record.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert len(record.versions) == 2  # v1 initial + v2 Agent-accepted candidate
    assert len(record.attempts) == 1  # went through the Agent's loop, not _improve()
    assert any("조사" in d for d in record.agent_decisions)


def test_run_via_agent_uses_tm_hit_and_skips_translate(tmp_path):
    from l10n_quality_agent.agent import AgentPlan, QwenAgent
    from l10n_quality_agent.tm import TmEntry, TranslationMemory

    class ExplodingChains(FakeChains):
        def translate(self, req):
            raise AssertionError("TM 매칭이 있는데도 translate()가 호출됨")

    class NoOpPlanner:
        def plan(self, **_values):
            return AgentPlan(strategy="human_review", reasoning="테스트")

    tm = TranslationMemory(
        [
            TmEntry(
                source_id="1",
                source_text="이 문장은 자연스럽게 번역되어야 합니다.",
                target_text="This sentence must read naturally.",
                target_language="English",
            )
        ]
    )
    store = JsonRunStore(tmp_path)
    fake_chains = ExplodingChains([], [MQMResult(errors=[])])
    workflow = QualityWorkflow(fake_chains, store, tm=tm)
    agent = QwenAgent(fake_chains, NoOpPlanner())

    record = workflow.run_via_agent(
        request("이 문장은 자연스럽게 번역되어야 합니다."), agent
    )

    assert record.tm_hit is True
    assert record.current_version.translation == "This sentence must read naturally."
    assert record.status == AgentStatus.AWAITING_HUMAN_APPROVAL
