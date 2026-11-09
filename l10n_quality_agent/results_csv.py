"""원문과 정렬된 별도 CSV로 UI 번역 결과의 최신 상태를 보여준다."""

from __future__ import annotations

import csv
from pathlib import Path

from .config import FLORES_PROCESSED_DIR
from .schemas import RunRecord, now_iso

SOURCE_CSV = FLORES_PROCESSED_DIR / "evaluation_30.csv"
RESULTS_CSV = Path("reports/translation_results.csv")
FIELDS = ["id", "한국어", "목표국가", "목표언어", "번역결과", "상태", "run_id", "갱신시각"]


def save_result(record: RunRecord, source_csv: Path = SOURCE_CSV, results_csv: Path = RESULTS_CSV) -> Path:
    """실행 하나를 upsert한다. 다른 국가·무관한 결과 행은 그대로 둔다."""
    # 원본 CSV는 읽기 전용으로 취급하고 결과 CSV만 갱신한다.
    source = record.request.source.strip()
    source_id = ""
    if source_csv.exists():
        with source_csv.open(encoding="utf-8-sig", newline="") as handle:
            matches = [row for row in csv.DictReader(handle) if row.get("한국어", "").strip() == source]
        if len(matches) == 1:
            source_id = matches[0]["id"]

    rows = []
    if results_csv.exists():
        with results_csv.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not set(FIELDS).issubset(reader.fieldnames or []):
                raise ValueError("선택한 CSV에는 번역 결과 열이 없습니다.")
            rows = list(reader)

    updated = {
        "id": source_id,
        "한국어": source,
        "목표국가": record.request.target_country,
        "목표언어": record.request.target_language,
        "번역결과": record.current_version.translation,
        "상태": record.status.value,
        "run_id": record.run_id,
        "갱신시각": now_iso(),
    }
    def same_sentence(row):
        same_source = (
            row.get("id") == source_id if source_id else row.get("한국어", "").strip() == source
        )
        return same_source and row.get("목표국가") == record.request.target_country

    rows = [row for row in rows if not same_sentence(row) and row.get("run_id") != record.run_id]
    rows.append(updated)
    unique = {}
    for row in rows:
        key = (row.get("id") or row.get("한국어", "").strip(), row.get("목표국가"))
        unique.pop(key, None)
        unique[key] = row
    rows = list(unique.values())

    results_csv.parent.mkdir(parents=True, exist_ok=True)
    # 임시 파일에 쓴 뒤 교체해 저장 중 중단으로 원본이 깨지지 않게 한다.
    temporary = results_csv.with_suffix(results_csv.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(results_csv)
    return results_csv
