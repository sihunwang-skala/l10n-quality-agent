"""로컬 Qwen으로 평가 -> 문법 수정 -> 재평가 흐름을 실제로 돌려본다."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from l10n_quality_agent.schemas import TranslationRequest
from l10n_quality_agent.workflow import QualityWorkflow


def main() -> None:
    request = TranslationRequest(
        source="이 냉장고는 에너지 소비를 20% 줄입니다.",
        target_language="English",
        target_country="Australia",
    )
    workflow = QualityWorkflow()
    record = workflow.run(
        request,
        starting_translation="This refrigerator reduce energy consumption by 20%.",
    )
    Path("reports").mkdir(exist_ok=True)
    path = Path("reports/revision_integration_result.json")
    path.write_text(
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("상태:", record.status.value)
    print("버전:", [item.translation for item in record.versions])
    print("시도:", len(record.attempts))
    for attempt in record.attempts:
        print(attempt.category, attempt.accepted, attempt.failure_reasons)
    print("결과 저장:", path)


if __name__ == "__main__":
    main()

