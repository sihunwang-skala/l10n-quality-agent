from l10n_quality_agent.dne import DneEntry, DoNotEditList
from l10n_quality_agent.resources import apply_resources
from l10n_quality_agent.schemas import TranslationRequest
from l10n_quality_agent.terminology import Terminology, TerminologyEntry


def make_request(source: str) -> TranslationRequest:
    return TranslationRequest(source=source, target_language="English", target_country="United States")


def test_candidate_terminology_is_never_applied():
    terminology = Terminology(
        [
            TerminologyEntry(
                source_term="에스키모",
                target_term="Eskimo",
                evidence="651",
                approval_status="candidate",
            )
        ]
    )
    result = apply_resources(make_request("에스키모라는 단어"), terminology, dne=None)
    assert "Eskimo" not in result.protected_terms
    assert "candidate" not in result.additional_instruction  # no leaked instruction either


def test_approved_terminology_adds_instruction_and_protects_target_term():
    terminology = Terminology(
        [
            TerminologyEntry(
                source_term="메트로플러스",
                target_term="MetroPlus",
                evidence="854",
                approval_status="approved",
            )
        ]
    )
    result = apply_resources(make_request("메트로플러스는 편리합니다."), terminology, dne=None)
    assert "MetroPlus" in result.protected_terms
    assert "메트로플러스" in result.additional_instruction
    assert "MetroPlus" in result.additional_instruction


def test_terminology_not_matching_source_is_not_applied():
    terminology = Terminology(
        [
            TerminologyEntry(
                source_term="메트로플러스",
                target_term="MetroPlus",
                evidence="854",
                approval_status="approved",
            )
        ]
    )
    result = apply_resources(make_request("오늘 날씨가 좋습니다."), terminology, dne=None)
    assert result.protected_terms == []
    assert result.additional_instruction == ""


def test_approved_dne_term_is_protected():
    dne = DoNotEditList(
        [DneEntry(term="GPS", category="acronym", evidence="919", approval_status="approved")]
    )
    result = apply_resources(make_request("GPS 장치를 빌리세요."), terminology=None, dne=dne)
    assert "GPS" in result.protected_terms


def test_candidate_dne_term_is_not_applied():
    dne = DoNotEditList(
        [DneEntry(term="GPS", category="acronym", evidence="919", approval_status="candidate")]
    )
    result = apply_resources(make_request("GPS 장치를 빌리세요."), terminology=None, dne=dne)
    assert "GPS" not in result.protected_terms


def test_existing_protected_terms_are_preserved_alongside_new_ones():
    dne = DoNotEditList(
        [DneEntry(term="GPS", category="acronym", evidence="919", approval_status="approved")]
    )
    request = make_request("GPS 장치를 빌리세요.").model_copy(
        update={"protected_terms": ["AcmeVision OLED"]}
    )
    result = apply_resources(request, terminology=None, dne=dne)
    assert set(result.protected_terms) == {"AcmeVision OLED", "GPS"}
