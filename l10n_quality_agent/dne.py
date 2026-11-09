"""DNE(Do Not Edit): 번역 과정에서 한 글자도 바뀌면 안 되는 문자열.

모든 고유명사가 DNE인 건 아니다 - 원문 표현을 승인된 목표 표현으로 바꿔야
하는 경우(예: 정식 영문 표기로 바뀌어야 할 한국어 음역)는 terminology.py를
쓴다. DNE는 이미 그대로가 맞고 손대면 안 되는 문자열(약어, 식별자, "번역
금지" 근거가 확인된 브랜드명)을 위한 것이다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .config import DNE_DIR

ApprovalStatus = Literal["approved", "candidate"]


class DneEntry(BaseModel):
    term: str
    category: str  # 예: "acronym", "identifier", "brand"
    domain: str = "wikivoyage"
    evidence: str  # 이 항목을 확인한 근거가 된 FLORES+ dev 문장 id
    approval_status: ApprovalStatus = "candidate"


class DoNotEditList:
    def __init__(self, entries: list[DneEntry]):
        self.entries = entries

    def lookup_applicable(self, source_text: str) -> list[str]:
        """승인된 DNE 용어 중 source_text에 그대로 등장하는 것들."""
        return [
            entry.term
            for entry in self.entries
            if entry.approval_status == "approved" and entry.term in source_text
        ]

    @classmethod
    def from_json_file(cls, path: str | Path) -> "DoNotEditList":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([DneEntry.model_validate(item) for item in data])

    def to_json(self) -> str:
        return json.dumps(
            [entry.model_dump() for entry in self.entries], ensure_ascii=False, indent=2
        )


def default_dne_path() -> Path:
    return DNE_DIR / "wikivoyage_ko_en_dne.json"
