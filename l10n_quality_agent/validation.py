"""수정 후보 번역에 대한 결정적(rule-based) 안전 검사."""

from __future__ import annotations

import re

from .schemas import MQMResult, TranslationRequest

UNIT_ALT = r"(?:°[CF]|kg|g|mg|km|cm|mm|m|L|ml|W|kW|V|Hz)"
NUMBER_UNIT_RE = re.compile(
    r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*"
    rf"(?:%|{UNIT_ALT}(?![A-Za-z]))?",
    re.IGNORECASE,
)
KOREAN_DATE_RE = re.compile(r"(?P<year>\d{2,4})년\s*(?P<month>\d{1,2})월")

# 영어는 단위를 "kilometers"처럼 풀어 쓰고 한국어는 "km"로 줄여 쓴다 -
# 정규화하지 않으면 맞는 번역도 숫자/단위 불일치로 잘못 걸린다.
SPELLED_OUT_UNITS = [
    (r"kilometer(?:s)?|kilometre(?:s)?", "km"),
    (r"centimeter(?:s)?|centimetre(?:s)?", "cm"),
    (r"millimeter(?:s)?|millimetre(?:s)?", "mm"),
    (r"kilogram(?:s)?", "kg"),
    (r"milligram(?:s)?", "mg"),
    (r"gram(?:s)?", "g"),
    (r"milliliter(?:s)?|millilitre(?:s)?", "ml"),
    (r"liter(?:s)?|litre(?:s)?", "L"),
    (r"kilowatt(?:s)?", "kW"),
    (r"watt(?:s)?", "W"),
    (r"volt(?:s)?", "V"),
    (r"hertz", "Hz"),
    (r"meter(?:s)?|metre(?:s)?", "m"),
]

# "2~3km" 같은 범위는 기본적으로 두 번째 숫자에만 단위가 붙는다 - 비교가
# 어긋나지 않도록 양쪽 다 "2km 3km" 형태로 펼쳐준다.
RANGE_PATTERNS = [
    re.compile(rf"(\d+(?:\.\d+)?)\s*~\s*(\d+(?:\.\d+)?)\s*({UNIT_ALT}|%)(?![A-Za-z])", re.IGNORECASE),
    re.compile(rf"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*({UNIT_ALT}|%)(?![A-Za-z])", re.IGNORECASE),
]


def _normalize_units(text: str) -> str:
    normalized = text
    for pattern, abbreviation in SPELLED_OUT_UNITS:
        normalized = re.sub(rf"\b(?:{pattern})\b", abbreviation, normalized, flags=re.IGNORECASE)
    for range_re in RANGE_PATTERNS:
        normalized = range_re.sub(
            lambda m: f"{m.group(1)}{m.group(3)} {m.group(2)}{m.group(3)}", normalized
        )
    return normalized
KOREAN_MANWON_RE = re.compile(r"(?P<amount>\d+(?:\.\d+)?)\s*만원")
ENGLISH_MONTHS = {
    1: "january", 2: "february", 3: "march", 4: "april",
    5: "may", 6: "june", 7: "july", 8: "august",
    9: "september", 10: "october", 11: "november", 12: "december",
}


def extract_number_units(text: str) -> list[str]:
    normalized = _normalize_units(text)
    return [re.sub(r"\s+", "", match) for match in NUMBER_UNIT_RE.findall(normalized)]


def _strip_equivalent_localized_dates(source: str, translation: str) -> tuple[str, str]:
    """한국어 "년/월"과 영어 월/년 표기가 명백히 같은 날짜일 때만 둘 다 제거한다."""
    source_copy = source
    translation_copy = translation
    for match in list(KOREAN_DATE_RE.finditer(source)):
        year = int(match.group("year"))
        full_year = 2000 + year if year < 100 else year
        month = int(match.group("month"))
        month_name = ENGLISH_MONTHS.get(month)
        if not month_name:
            continue
        translated_date = re.search(
            rf"\b{month_name}\b(?:\s+\d{{1,2}},?)?\s+{full_year}\b",
            translation_copy,
            flags=re.IGNORECASE,
        )
        if translated_date:
            source_copy = source_copy.replace(match.group(0), "", 1)
            translation_copy = (
                translation_copy[: translated_date.start()]
                + translation_copy[translated_date.end() :]
            )
    return source_copy, translation_copy


def _strip_equivalent_localized_currency(
    source: str, translation: str
) -> tuple[str, str]:
    """한국어 "만원" 표기와 대응하는 won/KRW 금액을 함께 제거한다."""
    source_copy = source
    translation_copy = translation
    for match in list(KOREAN_MANWON_RE.finditer(source)):
        won = int(float(match.group("amount")) * 10_000)
        formatted = f"{won:,}"
        translated_money = re.search(
            rf"(?:₩\s*|KRW\s*)?{re.escape(formatted)}\s*(?:won|KRW)\b",
            translation_copy,
            flags=re.IGNORECASE,
        )
        if translated_money:
            source_copy = source_copy.replace(match.group(0), "", 1)
            translation_copy = (
                translation_copy[: translated_money.start()]
                + translation_copy[translated_money.end() :]
            )
    return source_copy, translation_copy


def _strip_equivalent_localized_values(
    source: str, translation: str
) -> tuple[str, str]:
    source, translation = _strip_equivalent_localized_dates(source, translation)
    return _strip_equivalent_localized_currency(source, translation)


META_COMMENT_MARKERS = ("※", "注：", "注:", "주:", "참고:", "Note:", "note:")


def detect_meta_commentary_leak(translation: str) -> str | None:
    """원문에 대한 메타 주석이 번역문에 섞여 나왔는지 확인한다.

    thinking 모드를 꺼두면 모델이 원문에 대한 추론을 결과물에 그대로 써버릴
    때가 있는데, 이게 목표 언어로 쓰이기 때문에 잔여 한국어 검사로는 못
    잡는다 - 아래 마커 문자들이 실제로 관찰된 신호다.
    """
    if any(marker in translation for marker in META_COMMENT_MARKERS):
        return "번역문에 원문 관련 메타 주석으로 보이는 표현이 섞여 있음"
    return None


def validate_spans(result: MQMResult, translation: str) -> list[str]:
    warnings = []
    for error in result.errors:
        if error.span and error.span not in translation:
            warnings.append(
                f"MQM span이 번역문에 없음: {error.category} / {error.span!r}"
            )
    return warnings


def validate_candidate(
    request: TranslationRequest,
    current: str,
    candidate: str,
) -> list[str]:
    # 후보를 채택하기 전에 모델과 무관한 조건을 먼저 확인한다.
    reasons: list[str] = []
    if not candidate.strip():
        reasons.append("수정 후보가 비어 있음")
        return reasons
    if candidate.strip() == current.strip():
        reasons.append("수정 후보가 현재 번역과 동일함")

    for term in request.protected_terms:
        if term and term not in candidate:
            reasons.append(f"보호 용어 변경 또는 누락: {term}")

    leak_reason = detect_meta_commentary_leak(candidate)
    if leak_reason:
        reasons.append(leak_reason)

    current_numbers = extract_number_units(current)
    candidate_numbers = extract_number_units(candidate)
    if current_numbers != candidate_numbers:
        reasons.append(
            "숫자 또는 단위가 수정 전후 달라짐: "
            f"{current_numbers} -> {candidate_numbers}"
        )

    comparable_source, comparable_candidate = _strip_equivalent_localized_values(
        request.source, candidate
    )
    source_numbers = extract_number_units(comparable_source)
    comparable_candidate_numbers = extract_number_units(comparable_candidate)
    if source_numbers and comparable_candidate_numbers != source_numbers:
        reasons.append(
            "원문과 후보의 숫자/단위 대응을 자동 확정할 수 없음: "
            f"원문 {source_numbers}, 후보 {comparable_candidate_numbers}"
        )
    return reasons


def validate_initial(request: TranslationRequest, translation: str) -> list[str]:
    """초기/모델 수정 번역에 결정적 검사만 적용한다."""
    reasons: list[str] = []
    for term in request.protected_terms:
        if term and term not in translation:
            reasons.append(f"초기 번역에서 보호 용어 변경 또는 누락: {term}")
    leak_reason = detect_meta_commentary_leak(translation)
    if leak_reason:
        reasons.append(leak_reason)
    comparable_source, comparable_translation = _strip_equivalent_localized_values(
        request.source, translation
    )
    source_numbers = extract_number_units(comparable_source)
    translation_numbers = extract_number_units(comparable_translation)
    if source_numbers and source_numbers != translation_numbers:
        reasons.append(
            "원문과 번역의 숫자/단위 대응을 자동 확정할 수 없음: "
            f"원문 {source_numbers}, 번역 {translation_numbers}"
        )
    return reasons


def critical_count(result: MQMResult) -> int:
    return sum(error.severity == "critical" for error in result.errors)


def category_count(result: MQMResult, category: str) -> int:
    return sum(error.category == category for error in result.errors)
