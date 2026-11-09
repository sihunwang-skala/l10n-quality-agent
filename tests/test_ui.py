from l10n_quality_agent import ui
from l10n_quality_agent.schemas import (
    AgentStatus,
    RunRecord,
    TranslationRequest,
    TranslationVersion,
)


def test_readable_agent_strategy_has_separate_reason():
    message = "[Agent 1/2] 전략 선택: human_review - 자세한 검토가 필요함"
    assert ui._readable_step(message) == "[Agent 판단 1회차 · 최대 2회] 전략 선택: human_review\n사유: 자세한 검토가 필요함"


def test_choose_results_file_keeps_selected_csv(monkeypatch, tmp_path):
    selected = tmp_path / "선택한_결과.csv"
    selected.write_text("id,한국어,목표국가,목표언어,번역결과,상태,run_id,갱신시각\n", encoding="utf-8")

    class Completed:
        returncode = 0
        stdout = str(selected) + "\n"
        stderr = ""

    monkeypatch.setattr(ui.subprocess, "run", lambda *args, **kwargs: Completed())
    assert ui.choose_results_file("reports/translation_results.csv") == str(selected)


class FakeStore:
    def __init__(self):
        self.records: dict[str, RunRecord] = {}

    def load(self, run_id):
        return self.records[run_id]


class FakeWorkflow:
    def __init__(self):
        self.store = FakeStore()

    def run_via_agent(self, request, agent, progress_callback=None):
        progress_callback("입력 확인 완료")
        progress_callback("[1] 초기 번역 완료: translated")
        progress_callback("[Agent] [조사] MQM 재평가 실행 -> 오류 0개 발견")
        record = RunRecord(
            request=request,
            status=AgentStatus.AWAITING_HUMAN_APPROVAL,
            versions=[TranslationVersion(version=1, translation="translated")],
        )
        self.store.records[record.run_id] = record
        return record


def test_multi_country_ui_streams_and_creates_separate_runs(monkeypatch):
    monkeypatch.setattr(ui, "workflow", FakeWorkflow())
    monkeypatch.setattr(ui, "agent", object())  # run_via_agent is faked; the real agent is unused
    monkeypatch.setattr(ui, "save_result", lambda record, **kwargs: None)
    outputs = list(
        ui.run_translation("원문", ["Japan", "Italy"], "", "", False)
    )
    final_text, run_map, country_update, version_update = outputs[-1]
    assert set(run_map) == {"Japan", "Italy"}
    assert run_map["Japan"] != run_map["Italy"]
    assert "## Japan" in final_text and "## Italy" in final_text
    assert any("[1] 초기 번역 완료" in item[0] for item in outputs)
    assert any("국가 1/2: Japan" in item[0] for item in outputs)
    assert "Italy 완료 (2/2)" in final_text
    assert country_update["value"] == "Italy"
    assert version_update["value"] == "1"
    assert "최종: AWAITING_HUMAN_APPROVAL\nrun_id=" in final_text
    assert "\n\ntranslated\n\n[Italy] 저장했습니다:" in final_text


def test_switching_result_country_refreshes_versions_without_leaking(monkeypatch):
    fake = FakeWorkflow()
    monkeypatch.setattr(ui, "workflow", fake)
    monkeypatch.setattr(ui, "agent", object())
    monkeypatch.setattr(ui, "save_result", lambda record, **kwargs: None)
    outputs = list(ui.run_translation("원문", ["Japan", "Italy"], "", "", False))
    _, run_map, _, _ = outputs[-1]

    # Simulate Japan having gone through an extra revision (2 versions)
    # while Italy still only has its initial version (1).
    japan_record = fake.store.records[run_map["Japan"]]
    japan_record.versions.append(
        TranslationVersion(version=2, translation="translated v2")
    )

    japan_update = ui.refresh_versions(run_map, "Japan")
    assert japan_update["choices"] == ["1", "2"]
    assert japan_update["value"] == "2"

    italy_update = ui.refresh_versions(run_map, "Italy")
    assert italy_update["choices"] == ["1"]
    assert italy_update["value"] == "1"


def test_manual_save_exposes_existing_csv_and_updates_same_sentence(monkeypatch, tmp_path):
    fake = FakeWorkflow()
    monkeypatch.setattr(ui, "workflow", fake)
    request = TranslationRequest(source="원문", target_language="English", target_country="United States")
    record = RunRecord(request=request, versions=[TranslationVersion(version=1, translation="First")])
    fake.store.records[record.run_id] = record
    path = tmp_path / "results.csv"

    message, preview, download, summary = ui.save_selected_result(
        {"United States": record.run_id}, "United States", str(path)
    )
    assert message.startswith("저장했습니다:")
    assert download == str(path)
    assert len(preview) == 1 and preview.iloc[0]["번역결과"] == "First"
    assert "1행" in summary

    record.versions.append(TranslationVersion(version=2, translation="Revised"))
    _, preview, _, _ = ui.save_selected_result(
        {"United States": record.run_id}, "United States", str(path)
    )
    assert len(preview) == 1 and preview.iloc[0]["번역결과"] == "Revised"
