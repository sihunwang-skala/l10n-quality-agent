"""번역 체인에 넘기기 전에 TranslationRequest에 DNE + 승인된 용어집을 적용한다.

새 프롬프트 변수나 Validator 배관을 추가하는 대신, 이미 있고 validation.py가
끝까지 강제하는 두 필드를 그대로 재사용한다:

- DNE 적중 항목과 승인된 용어집의 *목표* 용어는 둘 다 `protected_terms`에
  합쳐진다 (그래야 나중에 수정 후보가 이걸 조용히 빼먹거나 바꿔치기 못한다 -
  validate_initial/validate_candidate가 이미 검사한다).
- 승인된 용어집은 `additional_instruction`에도 명시적 지시 한 줄을
  붙인다. protected_terms는 목표 문자열이 결과 어딘가에 있는지만 확인할
  뿐, source_term이 정확히 target_term이 되어야 한다는 것까지는 알려주지
  않기 때문이다.

candidate 상태 항목은 절대 자동 적용되지 않는다(Terminology.lookup_applicable
/ DoNotEditList.lookup_applicable 모두 기본값이 approved만 허용).
"""

from __future__ import annotations

from .dne import DoNotEditList
from .schemas import TranslationRequest
from .terminology import Terminology


def apply_resources(
    request: TranslationRequest,
    terminology: Terminology | None,
    dne: DoNotEditList | None,
) -> TranslationRequest:
    dne_hits = dne.lookup_applicable(request.source) if dne else []
    term_hits = terminology.lookup_applicable(request.source) if terminology else []

    protected = list(request.protected_terms)
    for term in dne_hits + [hit.target_term for hit in term_hits]:
        if term not in protected:
            protected.append(term)

    instruction = request.additional_instruction
    if term_hits:
        mapping_lines = "; ".join(
            f"'{hit.source_term}' -> '{hit.target_term}'" for hit in term_hits
        )
        term_instruction = f"다음 용어는 정확히 지정된 표현으로 번역하세요: {mapping_lines}."
        instruction = f"{instruction}\n{term_instruction}".strip()

    return request.model_copy(
        update={"protected_terms": protected, "additional_instruction": instruction}
    )
