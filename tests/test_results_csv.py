import csv

from l10n_quality_agent.results_csv import save_result
from l10n_quality_agent.schemas import AgentStatus, RunRecord, TranslationRequest, TranslationVersion


def test_results_upsert_matches_source_and_preserves_other_country(tmp_path):
    source = tmp_path / "evaluation_30.csv"
    source.write_text("id,한국어,영어\n883,원문,reference\n", encoding="utf-8")
    result = tmp_path / "reports" / "translation_results.csv"
    records = []
    for country in ("United States", "Canada"):
        record = RunRecord(request=TranslationRequest(source="원문", target_language="English", target_country=country),
                           versions=[TranslationVersion(version=1, translation="first")])
        save_result(record, source, result)
        records.append(record)
    records[0].versions.append(TranslationVersion(version=2, translation="revised"))
    records[0].status = AgentStatus.APPROVED
    save_result(records[0], source, result)
    newer_run = RunRecord(request=records[0].request,
                          versions=[TranslationVersion(version=1, translation="new run")])
    save_result(newer_run, source, result)
    with result.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["id"] == "883"
    assert next(r for r in rows if r["목표국가"] == "United States")["번역결과"] == "new run"
    assert next(r for r in rows if r["목표국가"] == "Canada")["번역결과"] == "first"
    assert source.read_text(encoding="utf-8") == "id,한국어,영어\n883,원문,reference\n"
