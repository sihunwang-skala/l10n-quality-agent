"""대화형 CLI. 핵심 Workflow 코드에는 input()이 전혀 섞이지 않는다."""

from __future__ import annotations

import argparse

from .presentation import format_record
from .schemas import TranslationRequest
from .workflow import QualityWorkflow


def ask_request() -> TranslationRequest:
    print("한국어 원문을 입력하세요:")
    source = input("> ").strip()
    print("목표 언어:")
    target_language = input("> ").strip()
    print("목표 국가:")
    target_country = input("> ").strip()
    print("추가 지시(없으면 Enter):")
    instruction = input("> ").strip()
    print("보호 용어(쉼표 구분, 없으면 Enter):")
    protected = [term.strip() for term in input("> ").split(",") if term.strip()]
    return TranslationRequest(
        source=source,
        target_language=target_language,
        target_country=target_country,
        additional_instruction=instruction,
        protected_terms=protected,
    )


def interactive() -> None:
    workflow = QualityWorkflow()
    record = workflow.run(ask_request())
    print(format_record(record))
    if record.status.value == "AWAITING_HUMAN_APPROVAL":
        print("선택: [a] 승인 [r] 거부 [v] 이전 버전 재수정 [q] 종료")
        choice = input("> ").strip().lower()
        if choice == "a":
            record = workflow.approve(record.run_id)
        elif choice == "r":
            record = workflow.reject(record.run_id)
        elif choice == "v":
            print("버전 번호:")
            version = int(input("> v").strip())
            print("추가 수정 지시:")
            instruction = input("> ").strip()
            record = workflow.revise_from_version(record.run_id, version, instruction)
        print(format_record(record))


def main() -> None:
    parser = argparse.ArgumentParser(description="L10n Quality Agent CLI")
    parser.add_argument("--list", action="store_true", help="저장된 실행 목록 출력")
    args = parser.parse_args()
    if args.list:
        workflow = QualityWorkflow()
        for record in workflow.store.list_records():
            print(record.run_id, record.status.value, record.request.source)
        return
    interactive()


if __name__ == "__main__":
    main()

