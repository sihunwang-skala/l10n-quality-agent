"""로컬 Ollama 모델 하나를 재사용하는 LangChain LCEL 체인 모음."""

from __future__ import annotations

import json
from typing import Protocol

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from .config import KEEP_ALIVE, MODEL_NAME, NUM_PREDICT, REASONING, SEED, TEMPERATURE
from .schemas import MQMError, MQMResult, TranslationRequest


class ChainProvider(Protocol):
    def translate(self, request: TranslationRequest) -> str: ...
    def evaluate(self, request: TranslationRequest, translation: str) -> MQMResult: ...
    def revise(
        self,
        request: TranslationRequest,
        translation: str,
        category: str,
        errors: list[MQMError],
        failure_feedback: str = "",
    ) -> str: ...
    def user_revise(self, request: TranslationRequest, translation: str) -> str: ...


# 프롬프트의 역할과 모델 입력은 여기서 한 곳에서 관리한다.
# 번역용 프롬프트에 정답 문장을 넣지 않는 것이 중요하다.
TRANSLATION_SYSTEM = """당신은 기업 제품 소개 문장의 전문 현지화 번역가입니다.
한국어 원문의 의미, 숫자, 단위, 브랜드명과 보호 용어를 보존하면서 목표 언어와 국가에 자연스럽게 번역하세요.
근거 없는 기능이나 공식 용어를 만들지 마세요.
원문이 어색하거나 모호해 보여도 그 사실에 대한 설명, 주석, 참고사항을 절대 덧붙이지 마세요.
출력은 오직 목표 언어로 된 번역문 한 줄뿐이어야 하며, 괄호로 원문을 해설하거나 한국어 문장을 섞지 마세요."""

MQM_SYSTEM = """당신은 보수적인 MQM 번역 품질 평가자입니다.
한국어 원문과 번역문을 함께 비교하여 근거가 명확한 오류만 보고하세요.
평가 영역은 accuracy(오역·누락·추가), terminology, spelling, grammar, style, fluency입니다.
공식 용어집이 제공되지 않았다면 특정 표현을 공식 용어라고 주장하지 마세요.
오류가 없으면 errors를 빈 목록으로 반환하세요. 평가 결과는 보조 판단이며 절대적 정답이 아닙니다."""

REVISION_ROLES = {
    "accuracy": "오역, 누락, 추가만 바로잡는 정확성 전문 번역가",
    "terminology": "제공된 근거 안에서 용어 오류만 수정하는 용어 전문가",
    "spelling": "철자 오류만 수정하는 교정 전문가",
    "grammar": "문법 오류만 수정하는 문법 교정 전문가",
    "style": "지정된 문체 오류만 수정하는 현지화 스타일 전문가",
    "fluency": "정확성과 용어를 보존하며 유창성 오류만 수정하는 전문가",
}


class OllamaChains:
    """모든 체인을 한 번만 만들어서 ChatOllama 인스턴스 하나를 공유한다."""

    def __init__(self, model: ChatOllama | None = None) -> None:
        # 모든 체인이 같은 로컬 모델 인스턴스를 공유한다.
        self.model = model or ChatOllama(
            model=MODEL_NAME,
            temperature=TEMPERATURE,
            seed=SEED,
            num_predict=NUM_PREDICT,
            keep_alive=KEEP_ALIVE,
            reasoning=REASONING,
        )
        self.translation_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TRANSLATION_SYSTEM),
                (
                    "human",
                    "원문: {source}\n목표 언어: {target_language}\n"
                    "목표 국가: {target_country}\n보호 용어: {protected_terms}\n"
                    "추가 지시: {additional_instruction}",
                ),
            ]
        )
        self.translation_chain = self.translation_prompt | self.model | StrOutputParser()

        # MQM과 Planner는 후속 Python 로직에서 쓰므로 구조화된 결과를 받는다.
        self.mqm_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", MQM_SYSTEM),
                (
                    "human",
                    "원문: {source}\n번역문: {translation}\n"
                    "목표 언어: {target_language}\n목표 국가: {target_country}\n"
                    "보호 용어: {protected_terms}",
                ),
            ]
        )
        self.structured_model = self.model.with_structured_output(
            MQMResult, method="json_schema"
        )
        self.mqm_chain = self.mqm_prompt | self.structured_model

        self.revision_chains = {
            category: self._build_revision_chain(category, role)
            for category, role in REVISION_ROLES.items()
        }
        self.user_revision_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", TRANSLATION_SYSTEM),
                (
                    "human",
                    "아래 기존 번역을 사용자의 추가 지시에 맞게 다시 수정하세요.\n"
                    "원문: {source}\n기존 번역: {translation}\n"
                    "목표 언어: {target_language}\n목표 국가: {target_country}\n"
                    "보호 용어: {protected_terms}\n추가 지시: {additional_instruction}",
                ),
            ]
        )
        self.user_revision_chain = (
            self.user_revision_prompt | self.model | StrOutputParser()
        )

    def _build_revision_chain(self, category: str, role: str):
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    f"당신은 {role}입니다. 선택된 {category} 오류만 수정하세요. "
                    "원문의 의미, 숫자, 단위, 보호 용어와 다른 품질 영역은 바꾸지 마세요. "
                    "수정된 번역문만 출력하세요.",
                ),
                (
                    "human",
                    "원문: {source}\n현재 번역: {translation}\n"
                    "목표 언어: {target_language}\n목표 국가: {target_country}\n"
                    "보호 용어: {protected_terms}\n선택 오류: {selected_errors}\n"
                    "이전 실패 피드백: {failure_feedback}",
                ),
            ]
        )
        return prompt | self.model | StrOutputParser()

    @staticmethod
    def _request_values(request: TranslationRequest) -> dict[str, str]:
        return {
            "source": request.source,
            "target_language": request.target_language,
            "target_country": request.target_country,
            "additional_instruction": request.additional_instruction or "없음",
            "protected_terms": json.dumps(request.protected_terms, ensure_ascii=False),
        }

    def translate(self, request: TranslationRequest) -> str:
        return self.translation_chain.invoke(self._request_values(request)).strip()

    def evaluate(self, request: TranslationRequest, translation: str) -> MQMResult:
        values = self._request_values(request) | {"translation": translation}
        result = self.mqm_chain.invoke(values)
        if isinstance(result, MQMResult):
            return result
        try:
            return MQMResult.model_validate(result)
        except ValidationError as exc:
            raise RuntimeError(f"MQM 구조화 출력 검증 실패: {exc}") from exc

    def revise(
        self,
        request: TranslationRequest,
        translation: str,
        category: str,
        errors: list[MQMError],
        failure_feedback: str = "",
    ) -> str:
        values = self._request_values(request) | {
            "translation": translation,
            "selected_errors": json.dumps(
                [error.model_dump() for error in errors], ensure_ascii=False
            ),
            "failure_feedback": failure_feedback or "없음",
        }
        return self.revision_chains[category].invoke(values).strip()

    def user_revise(self, request: TranslationRequest, translation: str) -> str:
        values = self._request_values(request) | {"translation": translation}
        return self.user_revision_chain.invoke(values).strip()
