"""실행 기록과 번역 버전을 JSON으로 저장한다."""

from __future__ import annotations

import json
from pathlib import Path

from .schemas import RunRecord, now_iso


class JsonRunStore:
    def __init__(self, directory: str | Path = "runs") -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def path_for(self, run_id: str) -> Path:
        if not run_id or any(char not in "0123456789abcdef" for char in run_id.lower()):
            raise ValueError("유효하지 않은 실행 ID입니다.")
        return self.directory / f"{run_id}.json"

    def save(self, record: RunRecord) -> Path:
        record.updated_at = now_iso()
        path = self.path_for(record.run_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

    def load(self, run_id: str) -> RunRecord:
        return RunRecord.model_validate_json(
            self.path_for(run_id).read_text(encoding="utf-8")
        )

    def list_records(self) -> list[RunRecord]:
        records = []
        for path in sorted(self.directory.glob("*.json"), reverse=True):
            records.append(RunRecord.model_validate_json(path.read_text(encoding="utf-8")))
        return records

