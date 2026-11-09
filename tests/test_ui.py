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
    final_text, run_map, country_update, version_update, dashboard = outputs[-1]
    assert set(run_map) == {"Japan", "Italy"}
    assert run_map["Japan"] != run_map["Italy"]
    assert "## Japan" in final_text and "## Italy" in final_text
    assert any("[1] 초기 번역 완료" in item[0] for item in outputs)
    assert any("국가 1/2: Japan" in item[0] for item in outputs)
    assert "Italy 완료 (2/2)" in final_text
    assert country_update["value"] == "Italy"
    assert version_update["value"] == "1"
    assert "Japan" in dashboard and "Italy" in dashboard and "승인 대기" in dashboard
    assert "최종: AWAITING_HUMAN_APPROVAL\nrun_id=" in final_text
    assert "\n\ntranslated\n\n[Italy] 저장했습니다:" in final_text


def test_switching_result_country_refreshes_versions_without_leaking(monkeypatch):
    fake = FakeWorkflow()
    monkeypatch.setattr(ui, "workflow", fake)
    monkeypatch.setattr(ui, "agent", object())
    monkeypatch.setattr(ui, "save_result", lambda record, **kwargs: None)
    outputs = list(ui.run_translation("원문", ["Japan", "Italy"], "", "", False))
    _, run_map, _, _, _ = outputs[-1]

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


def test_render_run_card_escapes_html_and_shows_status():
    from l10n_quality_agent.schemas import MQMError, MQMResult
    from l10n_quality_agent.ui_render import render_diff, render_run_card

    request = TranslationRequest(source="<b>원문</b>", target_language="Japanese", target_country="Japan")
    record = RunRecord(
        request=request,
        status=AgentStatus.HUMAN_REVIEW_REQUIRED,
        versions=[TranslationVersion(version=1, translation="<script>x</script>")],
        unresolved_errors=[MQMError(category="fluency", severity="minor", span="", explanation="어색함")],
    )
    html = render_run_card(record, "Japan")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "사람 검토 필요" in html and "fluency" in html and "남은 오류" in html
    assert "<ins>" in render_diff("abc", "abd") and "<del>" in render_diff("abc", "abd")


def test_show_run_returns_card_diff_and_edit_value(monkeypatch):
    fake = FakeWorkflow()
    monkeypatch.setattr(ui, "workflow", fake)
    request = TranslationRequest(source="원문", target_language="English", target_country="United States")
    record = RunRecord(
        request=request,
        versions=[
            TranslationVersion(version=1, translation="First"),
            TranslationVersion(version=2, translation="Second"),
        ],
    )
    fake.store.records[record.run_id] = record
    card, diff, edit = ui.show_run({"United States": record.run_id}, "United States", "1")
    assert "Second" in card and "<del>" in diff and edit["value"] == "Second"
    assert "아직 실행 결과가 없습니다" in ui.show_run({}, None)[0]


def test_run_translation_accepts_none_for_collapsed_optional_inputs(monkeypatch):
    monkeypatch.setattr(ui, "workflow", FakeWorkflow())
    monkeypatch.setattr(ui, "agent", object())
    monkeypatch.setattr(ui, "save_result", lambda record, **kwargs: None)
    outputs = list(ui.run_translation("원문", ["Japan"], None, None, False))
    assert set(outputs[-1][1]) == {"Japan"}


def _write_csv(tmp_path, text):
    path = tmp_path / "in.csv"
    path.write_text(text, encoding="utf-8-sig")
    return str(path)


def test_parse_batch_csv_reads_rows_defaults_and_overrides(tmp_path):
    path = _write_csv(tmp_path, "id,한국어,목표국가,보호용어,추가지시\n7,문장1,Japan|Italy,Foo,\n,문장2,,,격식\n,,,,\n")
    rows, errors = ui.parse_batch_csv(path, ["United States"])
    assert errors == []
    assert [r["label"] for r in rows] == ["7", "#2"]
    assert rows[0]["countries"] == ["Japan", "Italy"] and rows[0]["terms"] == "Foo"
    assert rows[1]["countries"] == ["United States"] and rows[1]["instruction"] == "격식"


def test_parse_batch_csv_reports_problems(tmp_path):
    assert "한국어" in ui.parse_batch_csv(_write_csv(tmp_path, "text\nhi\n"), ["Japan"])[1][0]
    assert ui.parse_batch_csv(_write_csv(tmp_path, "한국어,목표국가\nx,Atlantis\n"), ["Japan"])[1]
    assert ui.parse_batch_csv(_write_csv(tmp_path, "한국어\nx\n"), [])[1]  # 국가 없음
    many = "한국어\n" + "\n".join(f"s{i}" for i in range(ui.BATCH_MAX_ROWS + 1)) + "\n"
    assert any("최대" in e for e in ui.parse_batch_csv(_write_csv(tmp_path, many), ["Japan"])[1])
    assert ui.parse_batch_csv(None, ["Japan"])[1]


def test_batch_template_is_valid():
    rows, errors = ui.parse_batch_csv(ui.BATCH_TEMPLATE, ["Japan"])
    assert errors == [] and len(rows) == 3


def test_run_batch_runs_every_row_and_keeps_going_after_failure(monkeypatch, tmp_path):
    fake = FakeWorkflow()
    calls = []
    original = fake.run_via_agent

    def flaky(request, agent, progress_callback=None):
        calls.append(request.source)
        if request.source == "문장2":
            raise RuntimeError("model down")
        return original(request, agent, progress_callback)

    fake.run_via_agent = flaky
    monkeypatch.setattr(ui, "workflow", fake)
    monkeypatch.setattr(ui, "agent", object())
    monkeypatch.setattr(ui, "save_result", lambda record, **kwargs: None)
    path = _write_csv(tmp_path, "id,한국어,목표국가\na,문장1,Japan|Italy\nb,문장2,Japan\nc,문장3,Japan\n")
    outputs = list(ui.run_batch(path, ["Japan"], False))
    log, run_map, country_update, _, dashboard = outputs[-1]
    assert calls == ["문장1", "문장1", "문장2", "문장3"]
    assert set(run_map) == {"a · Japan", "a · Italy", "c · Japan"}
    assert "실행 실패" in dashboard and "model down" in log
    assert "3/4" in dashboard or "4/4" in dashboard
    assert country_update["value"] == "c · Japan"


def test_run_selected_mode_dispatch(monkeypatch):
    monkeypatch.setattr(ui, "workflow", FakeWorkflow())
    monkeypatch.setattr(ui, "agent", object())
    monkeypatch.setattr(ui, "save_result", lambda record, **kwargs: None)
    import pytest, gradio as gr
    with pytest.raises(gr.Error):
        list(ui.run_selected_mode(ui.MODE_POC, None, "", None, ["Japan"], "", "", False))
    out = list(ui.run_selected_mode(ui.MODE_POC, "889: 샘플 문장", "무시됨", None, ["Japan"], None, None, False))
    assert set(out[-1][1]) == {"Japan"}
    out = list(ui.run_selected_mode(ui.MODE_DIRECT, None, "직접", None, ["Italy"], "", "", False))
    assert set(out[-1][1]) == {"Italy"}


def test_mode_guide_states_input_and_intent():
    from l10n_quality_agent.ui_render import render_mode_guide
    for mode, needle in ((ui.MODE_POC, "테스트"), (ui.MODE_DIRECT, "타이핑"), (ui.MODE_CSV, "자동")):
        html = render_mode_guide(mode)
        assert needle in html and "입력할 것" in html and "이럴 때" in html


def test_hero_openai_badge_says_key_state_not_that_openai_ran():
    from l10n_quality_agent.ui_render import render_hero
    assert "Mock (키 없음)" in render_hero("Mock, 키 없음", [])
    assert "API 키 설정됨" in render_hero("실제 실행", []) and "실제 실행" not in render_hero("실제 실행", [])
