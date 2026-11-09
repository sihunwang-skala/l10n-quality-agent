"""Wikivoyage KO->EN 용어집: 원문 표현 -> 승인된 목표 표현.

문장 단위로 대응이 확인된(TM 시드 문장 10개 중 하나의 `evidence` id가 있는)
항목만 여기 존재한다. 애매하거나 민감한 매핑은 `approval_status="candidate"`
상태로 남겨둔다 - candidate는 승인된 항목과 똑같이 적용하면 안 된다
(`Terminology.lookup_applicable` 참고).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .config import TERMINOLOGY_DIR

ApprovalStatus = Literal["approved", "candidate"]


class TerminologyEntry(BaseModel):
    source_term: str
    target_term: str
    source_language: str = "Korean"
    target_language: str = "English"
    domain: str = "wikivoyage"
    topic: str = ""
    context: str = ""
    evidence: str  # 이 매핑을 확인한 근거가 된 FLORES+ dev 문장 id
    approval_status: ApprovalStatus = "candidate"


class Terminology:
    def __init__(self, entries: list[TerminologyEntry]):
        self.entries = entries

    def lookup_applicable(
        self, source_text: str, *, include_candidates: bool = False
    ) -> list[TerminologyEntry]:
        """source_term이 source_text에 그대로 등장하는 항목들."""
        allowed = {"approved"} | ({"candidate"} if include_candidates else set())
        return [
            entry
            for entry in self.entries
            if entry.approval_status in allowed and entry.source_term in source_text
        ]

    @classmethod
    def from_json_file(cls, path: str | Path) -> "Terminology":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([TerminologyEntry.model_validate(item) for item in data])

    def to_json(self) -> str:
        return json.dumps(
            [entry.model_dump() for entry in self.entries], ensure_ascii=False, indent=2
        )


def default_terminology_path() -> Path:
    return TERMINOLOGY_DIR / "wikivoyage_ko_en_terminology.json"
