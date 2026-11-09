from l10n_quality_agent.schemas import TranslationRequest
from l10n_quality_agent.validation import extract_number_units, validate_initial


def test_korean_tilde_range_matches_english_to_range():
    """Regression for the id=889 false positive found while running the
    real Wikivoyage pipeline: '2~3km' vs '2 to 3 kilometers' is a correct
    translation but extract_number_units used to only attach the unit to
    the second number, comparing ['2','3km'] against ['2','3']."""
    source = "남극 내륙은 2~3km의 얼음으로 뒤덮인 황량한 고원입니다."
    translation = (
        "The interior of Antarctica is a desolate plateau covered by ice "
        "2 to 3 kilometers thick."
    )
    assert extract_number_units(source) == extract_number_units(translation)


def test_hyphen_range_with_unit_is_recognized():
    assert extract_number_units("5-10kg 사이") == extract_number_units("between 5-10 kilograms")


def test_percent_range_still_works():
    assert extract_number_units("10~20%의 확률") == extract_number_units(
        "a probability of 10 to 20%"
    )


def test_spelled_out_units_normalize_to_abbreviations():
    assert extract_number_units("무게는 100g 입니다") == extract_number_units(
        "It weighs 100 grams"
    )


def test_plain_hyphenated_date_is_not_treated_as_a_range():
    # No trailing unit -> must not be merged/altered by the range patterns.
    assert extract_number_units("2020-09-22에 만났다") == ["2020", "09", "22"]


def test_validate_initial_accepts_the_previously_false_flagged_sentence():
    request = TranslationRequest(
        source="남극 내륙은 2~3km의 얼음으로 뒤덮인 황량한 고원입니다.",
        target_language="English",
        target_country="United States",
    )
    translation = (
        "The interior of Antarctica is a desolate plateau covered by ice "
        "2 to 3 kilometers thick."
    )
    assert validate_initial(request, translation) == []
