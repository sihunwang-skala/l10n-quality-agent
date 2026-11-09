from __future__ import annotations

from l10n_quality_agent.schemas import MQMResult, TranslationRequest
from l10n_quality_agent.storage import JsonRunStore
from l10n_quality_agent.tm import TmEntry, TranslationMemory
from l10n_quality_agent.workflow import QualityWorkflow

from test_workflow import FakeChains, request


class ExplodingChains(FakeChains):
    """translate() must never be called on a TM hit - explode if it is."""

    def translate(self, req):
        raise AssertionError("TM 매칭이 있는데도 chains.translate()가 호출됨")


def make_tm(source_text="여행 안전 문장", target_text="A travel safety sentence."):
    return TranslationMemory(
        [
            TmEntry(
                source_id="123",
                source_text=source_text,
                target_text=target_text,
                target_language="English",
                domain="wikivoyage",
                topic="travel, safety",
                split="dev",
            )
        ]
    )


def test_tm_hit_skips_new_translation_and_still_runs_mqm(tmp_path):
    tm = make_tm()
    chains = ExplodingChains([], [MQMResult(errors=[])])
    workflow = QualityWorkflow(chains, JsonRunStore(tmp_path), tm=tm)

    record = workflow.run(request("여행 안전 문장"))

    assert record.tm_hit is True
    assert record.tm_source_id == "123"
    assert record.current_version.translation == "A travel safety sentence."
    # TM hit still goes through the normal MQM gate - not auto-approved.
    from l10n_quality_agent.schemas import AgentStatus

    assert record.status == AgentStatus.AWAITING_HUMAN_APPROVAL


def test_tm_miss_falls_back_to_new_translation(tmp_path):
    tm = make_tm(source_text="다른 문장")  # won't match the request below
    chains = FakeChains(["A brand new translation."], [MQMResult(errors=[])])
    workflow = QualityWorkflow(chains, JsonRunStore(tmp_path), tm=tm)

    record = workflow.run(request("여행 안전 문장"))

    assert record.tm_hit is False
    assert record.tm_source_id is None
    assert record.current_version.translation == "A brand new translation."


def test_no_tm_configured_behaves_exactly_like_before(tmp_path):
    chains = FakeChains(["A brand new translation."], [MQMResult(errors=[])])
    workflow = QualityWorkflow(chains, JsonRunStore(tmp_path))  # tm=None (default)

    record = workflow.run(request("여행 안전 문장"))

    assert record.tm_hit is False
    assert record.current_version.translation == "A brand new translation."


def test_evaluation_sentences_are_not_in_the_tm_seed(tmp_path):
    """Regression guard for the anti-leakage rule: TM built from the 10
    tm-seed sentences must never contain an evaluation-set sentence id."""
    import pandas as pd

    from l10n_quality_agent.config import FLORES_PROCESSED_DIR

    tm_csv = FLORES_PROCESSED_DIR / "tm_seed_40.csv"
    eval_csv = FLORES_PROCESSED_DIR / "evaluation_30.csv"
    if not (tm_csv.exists() and eval_csv.exists()):
        return  # selection not generated yet in this environment
    tm_ids = set(pd.read_csv(tm_csv)["id"])
    eval_ids = set(pd.read_csv(eval_csv)["id"])
    assert tm_ids.isdisjoint(eval_ids)
