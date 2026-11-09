"""Build the Wikivoyage KO->EN terminology and DNE resource files.

Two separate reasons justify an entry - conflating them caused a real
mistake worth recording here. "Does chains.translate() get it wrong
without a hint?" is the right bar for a plain vocabulary/idiom gap
("bed and breakfast" - see below). It is the WRONG bar for a proper/brand
name: a name can translate correctly by luck on one deterministic run and
still get silently reworded by a later fluency/style *revision* pass that
has no idea it is a protected name. For names, the bar is "is this a real
proper/brand/service name" - if so it belongs in the glossary (its
target_term also lands in protected_terms via apply_resources(), which is
what actually guards it through revision), regardless of whether the
unaided first pass already happens to be correct.

Checked 2026-09-22 against real Qwen (reasoning=False, num_predict=1536):

    entry                                    | unaided first pass            | why kept
    ------------------------------------------|-------------------------------|----------
    "침대와 아침 식사" -> "bed and breakfast"   | WRONG: "luxury bedding and    | fixes a
                                              | breakfast service"            | real mistranslation
    "메트로플러스" -> "MetroPlus"               | happened to be correct        | real named
                                              | (provenance: source_url is the| service (Cape Town
                                              | Cape Town Wikimania guidebook -| Metrorail's premium
                                              | MetroPlus is Metrorail Western | class) - protect
                                              | Cape's real premium fare class)| from revision drift
    "월트 디즈니 월드" -> "Walt Disney World"   | happened to be correct        | real brand name -
                                              |                                | same reasoning
    "항이" -> "Hangi"                          | happened to be correct        | real named dish/
                                              |                                | practice - same reasoning

"에스키모" -> "Eskimo" stays a candidate regardless of correctness - the
source sentence itself flags the term as context-dependent/pejorative
outside the US, so it is never auto-applied either way.

Usage: python scripts/build_terminology_and_dne.py
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from l10n_quality_agent.config import DNE_DIR, TERMINOLOGY_DIR
from l10n_quality_agent.dne import DneEntry, DoNotEditList, default_dne_path
from l10n_quality_agent.terminology import (
    Terminology,
    TerminologyEntry,
    default_terminology_path,
)

TERMINOLOGY_ENTRIES = [
    TerminologyEntry(
        source_term="침대와 아침 식사",
        target_term="bed and breakfast",
        topic="travel, accomodation",
        context=(
            "숙박 형태를 가리키는 여행 용어. 힌트 없이 chains.translate()를 직접 실행해보니 "
            "'luxury bedding and breakfast service'로 오역됨 - 실제로 필요한 항목."
        ),
        evidence="744",
        approval_status="approved",
    ),
    TerminologyEntry(
        source_term="메트로플러스",
        target_term="MetroPlus",
        topic="travel, commute",
        context=(
            "실제 고유명사(provenance source_url이 Cape Town Wikimania 가이드북 - "
            "MetroPlus는 남아공 Metrorail Western Cape의 실제 프리미엄 등급 서비스명). "
            "첫 번역이 우연히 맞았어도 이후 fluency/style 수정 단계에서 표기가 바뀔 위험이 있어 "
            "protected_terms로 고정."
        ),
        evidence="854",
        approval_status="approved",
    ),
    TerminologyEntry(
        source_term="월트 디즈니 월드",
        target_term="Walt Disney World",
        topic="travel, culture",
        context="실제 브랜드명. 원문에 영문 병기가 있어 첫 번역은 맞지만, 수정 단계 드리프트 방지 목적으로 고정.",
        evidence="664",
        approval_status="approved",
    ),
    TerminologyEntry(
        source_term="항이",
        target_term="Hangi",
        topic="travel, culture",
        context="마오리족 전통 조리법을 가리키는 실제 고유명사. 원문에 영문 병기가 있어 첫 번역은 맞지만, 수정 단계 드리프트 방지 목적으로 고정.",
        evidence="849",
        approval_status="approved",
    ),
    TerminologyEntry(
        source_term="에스키모",
        target_term="Eskimo",
        topic="travel, culture",
        context=(
            "직역 대응은 확인되나, 원문 자체가 '캐나다 등에서는 모욕적으로 받아들여질 수 있음'을 "
            "명시하고 있어 문맥 의존성이 높음 - 자동 승인하지 않고 candidate로 남김"
        ),
        evidence="651",
        approval_status="candidate",
    ),
]

# "메트로플러스"->"MetroPlus", "월트 디즈니 월드"->"Walt Disney World",
# "항이"->"Hangi", DNE "GPS"도 검토했다가 뺐다: chains.translate()가 힌트 없이도
# 이미 올바른 영문 표기를 내놓아서(위 표 참고), 여기 고정해봐야 프롬프트/
# protected_terms만 늘어나고 얻는 게 없다. DNE 목록은 지금은 의도적으로 비워
# 둔다 - 아직 기준을 통과한 항목이 없고, 항목 수를 억지로 채우기보다는
# 실제 데이터를 왜곡하지 않는 쪽을 택했다.
DNE_ENTRIES: list[DneEntry] = []


def main() -> None:
    TERMINOLOGY_DIR.mkdir(parents=True, exist_ok=True)
    DNE_DIR.mkdir(parents=True, exist_ok=True)

    terminology = Terminology(TERMINOLOGY_ENTRIES)
    default_terminology_path().write_text(terminology.to_json(), encoding="utf-8")

    dne = DoNotEditList(DNE_ENTRIES)
    default_dne_path().write_text(dne.to_json(), encoding="utf-8")

    approved = sum(e.approval_status == "approved" for e in TERMINOLOGY_ENTRIES)
    candidate = len(TERMINOLOGY_ENTRIES) - approved
    print(f"용어집: 승인 {approved}개, candidate {candidate}개 -> {default_terminology_path()}")
    print(f"DNE: 승인 {len(DNE_ENTRIES)}개 -> {default_dne_path()}")


if __name__ == "__main__":
    main()
