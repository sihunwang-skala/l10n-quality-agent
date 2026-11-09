"""최소한의 Translation Memory: 원문 완전 일치만 조회한다.

Embedding도, Vector DB도, 퍼지 매칭도 없다 - 현재 범위 밖이다. 출처는
FLORES+ Dev이고 실무에서 승인된 TM이 아니다: 모든 항목의 `provenance`에
이 사실을 명시해서, 이 시드 TM을 다른 것으로 오해하지 않게 했다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from .config import TM_DIR


class TmEntry(BaseModel):
    source_id: str
    source_text: str
    target_text: str
    source_language: str = "Korean"
    target_language: str
    domain: str = ""
    topic: str = ""
    split: str = ""
    provenance: str = "FLORES+ Dev (seed TM for development only, not an enterprise-approved TM)"


class TranslationMemory:
    """TmEntry 몇 개를 놓고 완전 일치로만 조회한다."""

    def __init__(self, entries: list[TmEntry]):
        self._by_key: dict[tuple[str, str], TmEntry] = {
            (entry.source_text, entry.target_language): entry for entry in entries
        }

    def __len__(self) -> int:
        return len(self._by_key)

    def lookup(self, source_text: str, target_language: str) -> TmEntry | None:
        return self._by_key.get((source_text, target_language))

    def to_json(self) -> str:
        return json.dumps(
            [entry.model_dump() for entry in self._by_key.values()],
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "TranslationMemory":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([TmEntry.model_validate(item) for item in data])


def build_tm_from_seed_csv(
    csv_path: str | Path, target_language: str = "English"
) -> TranslationMemory:
    """select_wikivoyage_30.py가 만든 tm_seed_*.csv로 TM을 구축한다.

    id, split, domain, topic, 한국어, 영어 컬럼을 기대한다 (English 컬럼명도
    flores_data.py와 컬럼 스키마를 맞추려고 한국어로 되어 있다).
    """
    df = pd.read_csv(csv_path)
    target_column = {"English": "영어"}.get(target_language)
    if target_column is None or target_column not in df.columns:
        raise ValueError(f"TM 구축에서 지원하지 않는 target_language: {target_language!r}")
    entries = [
        TmEntry(
            source_id=str(row["id"]),
            source_text=row["한국어"],
            target_text=row[target_column],
            target_language=target_language,
            domain=row.get("domain", ""),
            topic=row.get("topic", ""),
            split=row.get("split", ""),
        )
        for _, row in df.iterrows()
    ]
    return TranslationMemory(entries)


def default_tm_path() -> Path:
    return TM_DIR / "wikivoyage_ko_en_seed_tm.json"
