"""필수 로컬 Qwen 통합 시나리오 2개를 실행한다."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from l10n_quality_agent.chains import OllamaChains
from l10n_quality_agent.schemas import TranslationRequest
from l10n_quality_agent.storage import JsonRunStore
from l10n_quality_agent.workflow import QualityWorkflow


def main() -> None:
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    chains = OllamaChains()
    workflow = QualityWorkflow(chains, JsonRunStore("runs"))
    requests = [
        TranslationRequest(
            source="이 냉장고는 에너지 소비를 20% 줄입니다.",
            target_language="English",
            target_country="Australia",
        ),
        TranslationRequest(
            source="AcmeVision OLED로 생생한 화질을 경험하세요.",
            target_language="English",
            target_country="Australia",
            protected_terms=["AcmeVision OLED"],
        ),
    ]
    records = []
    for index, request in enumerate(requests, 1):
        print(f"[{index}] 실행 시작: {request.source}", flush=True)
        record = workflow.run(request)
        records.append(record.model_dump(mode="json"))
        current = record.current_version.translation if record.versions else "(없음)"
        print(f"[{index}] 상태: {record.status.value}", flush=True)
        print(f"[{index}] 번역: {current}", flush=True)
        print(f"[{index}] 버전/시도: {len(record.versions)}/{len(record.attempts)}", flush=True)
    path = output_dir / "integration_results.json"
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"결과 저장: {path}")


if __name__ == "__main__":
    main()
