from __future__ import annotations

from collections import deque

from l10n_quality_agent.agent import (
    MAX_AGENT_STRATEGIES,
    AgentPlan,
    OpenAIAgentMock,
    QwenAgent,
)
from l10n_quality_agent.schemas import (
    AgentStatus,
    MQMError,
    MQMResult,
    RunRecord,
    TranslationVersion,
)

from test_workflow import request


class FakePlanner:
    def __init__(self, plans: list[AgentPlan]):
        self.plans = deque(plans)
        self.calls = 0

    def plan(self, **_values) -> AgentPlan:
        self.calls += 1
        return self.plans.popleft()


class FakeAgentChains:
    def __init__(self, revisions, evaluations):
        self.model = object()
        self.revisions = deque(revisions)
        self.evaluations = deque(evaluations)
        self.revise_calls: list[str] = []

    def translate(self, req):
        raise AssertionError("Agent는 translate()를 호출하면 안 됨")

    def revise(self, req, translation, category, errors, failure_feedback=""):
        self.revise_calls.append(category)
        return self.revisions.popleft()

    def evaluate(self, req, translation):
        return self.evaluations.popleft()

    def user_revise(self, req, translation):
        raise AssertionError("Agent는 user_revise()를 호출하면 안 됨")


def mqm_error(category="fluency", severity="minor"):
    return MQMError(category=category, severity=severity, span="", explanation="테스트")


def human_review_record_with_errors(errors: list[MQMError]) -> RunRecord:
    # No numbers in the source, so validate_candidate()'s source<->candidate
    # number-matching check never interferes with the acceptance/rejection
    # behavior these tests are actually exercising.
    record = RunRecord(
        request=request("이 문장은 자연스럽게 번역되어야 합니다."),
        status=AgentStatus.HUMAN_REVIEW_REQUIRED,
        versions=[TranslationVersion(version=1, translation="Original translation.")],
        unresolved_errors=errors,
    )
    return record


def test_agent_investigates_via_mqm_when_no_errors_yet_and_finds_none():
    """A validate_initial()/validate_candidate() failure (e.g. number/unit
    mismatch) sends a record to HUMAN_REVIEW_REQUIRED without MQM ever
    running, so unresolved_errors starts empty. The Agent must investigate
    (run MQM itself) rather than silently bail - and if MQM genuinely finds
    nothing wrong, that is a real, logged conclusion, not a silent no-op."""
    record = human_review_record_with_errors([])
    planner = FakePlanner([])
    chains = FakeAgentChains(revisions=[], evaluations=[MQMResult(errors=[])])
    agent = QwenAgent(chains, planner)

    result = agent.run(record)

    assert result.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert planner.calls == 0  # nothing to plan a strategy for
    assert chains.revise_calls == []
    assert any("조사" in d for d in result.agent_decisions)


def test_agent_investigates_via_mqm_when_no_errors_yet_and_finds_some():
    """Same starting point, but this time MQM's investigation turns up a
    real error - the Agent must then proceed through the normal
    strategy loop using that freshly-discovered error."""
    record = human_review_record_with_errors([])
    planner = FakePlanner([AgentPlan(strategy="fluency", reasoning="발견된 오류 수정")])
    chains = FakeAgentChains(
        revisions=["A better translation."],
        evaluations=[MQMResult(errors=[mqm_error("fluency")]), MQMResult(errors=[])],
    )
    agent = QwenAgent(chains, planner)

    progress = []
    result = agent.run(record, progress_callback=progress.append)

    assert result.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert chains.revise_calls == ["fluency"]
    assert any("조사" in d for d in result.agent_decisions)
    assert any("[fluency]" in d for d in result.agent_decisions)
    assert any("오류 1개 발견\n1. [fluency" in line for line in progress)


def test_agent_ignores_records_not_in_human_review():
    record = RunRecord(
        request=request(),
        status=AgentStatus.AWAITING_HUMAN_APPROVAL,
        versions=[TranslationVersion(version=1, translation="Fine.")],
    )
    planner = FakePlanner([])
    agent = QwenAgent(FakeAgentChains([], []), planner)

    result = agent.run(record)

    assert result.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert planner.calls == 0


def test_agent_stops_immediately_when_planner_picks_human_review():
    record = human_review_record_with_errors([mqm_error()])
    planner = FakePlanner([AgentPlan(strategy="human_review", reasoning="가망 없음")])
    chains = FakeAgentChains(revisions=[], evaluations=[])
    agent = QwenAgent(chains, planner)

    result = agent.run(record)

    assert result.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert chains.revise_calls == []
    assert any("human_review" in d for d in result.agent_decisions)


def test_agent_accepts_candidate_and_reaches_approval():
    record = human_review_record_with_errors([mqm_error("fluency")])
    planner = FakePlanner(
        [AgentPlan(strategy="fluency", reasoning="fluency 재시도")]
    )
    chains = FakeAgentChains(
        revisions=["A much better translation."],
        evaluations=[MQMResult(errors=[])],
    )
    agent = QwenAgent(chains, planner)

    result = agent.run(record)

    assert result.status == AgentStatus.AWAITING_HUMAN_APPROVAL
    assert result.current_version.translation == "A much better translation."
    assert chains.revise_calls == ["fluency"]
    assert len(result.attempts) == 1
    assert result.attempts[0].accepted is True


def test_agent_respects_max_strategy_budget():
    record = human_review_record_with_errors([mqm_error("fluency")])
    # Planner keeps proposing "fluency" but the candidate is always rejected
    # (no improvement) - must stop after MAX_AGENT_STRATEGIES, not loop forever.
    planner = FakePlanner(
        [AgentPlan(strategy="fluency", reasoning=f"시도 {i}") for i in range(5)]
    )
    chains = FakeAgentChains(
        revisions=["Still not better." for _ in range(5)],
        evaluations=[MQMResult(errors=[mqm_error("fluency")]) for _ in range(5)],
    )
    agent = QwenAgent(chains, planner)

    result = agent.run(record)

    assert result.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert planner.calls == MAX_AGENT_STRATEGIES
    assert len(chains.revise_calls) == MAX_AGENT_STRATEGIES


def test_openai_mock_never_changes_status_but_logs_a_decision():
    record = human_review_record_with_errors([mqm_error()])
    messages = []

    result = OpenAIAgentMock().run(record, progress_callback=messages.append)

    assert result.status == AgentStatus.HUMAN_REVIEW_REQUIRED
    assert any("MOCK" in d for d in result.agent_decisions)
    assert any("MOCK" in m for m in messages)


def test_openai_mock_ignores_records_not_in_human_review():
    record = RunRecord(
        request=request(),
        status=AgentStatus.AWAITING_HUMAN_APPROVAL,
        versions=[TranslationVersion(version=1, translation="Fine.")],
    )
    result = OpenAIAgentMock().run(record)
    assert result.agent_decisions == []
