"""선택한 문장 집합에 대해 Wikivoyage KO->EN 전체 파이프라인(TM -> 고정
Workflow -> Qwen Agent -> OpenAI Agent[Mock만])을 돌리고, 사람이 읽기 좋은
TXT 로그와 CSV 비교 리포트를 남긴다.

TXT 로그: reports/test_logs/test_YYYYMMDD_HHMMSS.txt (실행마다 새 파일,
덮어쓰지 않음 - l10n_quality_agent/run_logging.py 참고).
CSV 리포트: reports/wikivoyage_comparison_YYYYMMDD_HHMMSS.csv, 문장마다 한
행이며 참조 영어 텍스트는 사후 chrF 채점에만 쓰고 translate()/revise()에는
절대 넣지 않는다(flores_data.py 참고).
기존 JSON 실행 기록(runs/*.json)은 둘 다 건드리지 않는다.

Usage:
    python scripts/run_wikivoyage_pipeline.py --set tm --limit 3
    python scripts/run_wikivoyage_pipeline.py --set eval --limit 2 --agent
    python scripts/run_wikivoyage_pipeline.py --set eval --agent --openai-mock --verbose
"""

from __future__ import annotations

import argparse
import csv
import time
import traceback
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import sacrebleu

from l10n_quality_agent import config
from l10n_quality_agent.agent import OpenAIAgentMock, QwenAgent
from l10n_quality_agent.chains import OllamaChains
from l10n_quality_agent.config import FLORES_PROCESSED_DIR
from l10n_quality_agent.dne import DoNotEditList, default_dne_path
from l10n_quality_agent.resources import apply_resources
from l10n_quality_agent.run_logging import setup_run_logger
from l10n_quality_agent.schemas import AgentStatus, TranslationRequest
from l10n_quality_agent.storage import JsonRunStore
from l10n_quality_agent.terminology import Terminology, default_terminology_path
from l10n_quality_agent.tm import TranslationMemory, default_tm_path
from l10n_quality_agent.workflow import QualityWorkflow


class LoggingChains:
    """실제 OllamaChains에 위임하면서 모든 호출을 로그로 남기고 카운트한다.

    chains.py/workflow.py 밖에 일부러 뒀다 - 이건 실험용 관심사지, 핵심
    Agent가 필요로 하는 게 아니다.
    """

    def __init__(self, inner: OllamaChains, logger, verbose: bool) -> None:
        self.inner = inner
        self.model = inner.model  # QwenAgentPlanner가 이걸 재사용한다
        self.logger = logger
        self.verbose = verbose
        self.call_count = 0

    # translate()/revise() 결과·후보 텍스트는 여기서 일부러 로그로 안 남긴다 -
    # workflow.py/agent.py의 진행 메시지에 이미 같은 텍스트가 실려서
    # 여기서 또 찍으면 중복일 뿐이다.

    def translate(self, request):
        self.call_count += 1
        t0 = time.monotonic()
        result = self.inner.translate(request)
        dt = time.monotonic() - t0
        self.logger.info(f"  [Ollama #{self.call_count} · 번역 Tool] {dt:.2f}s")
        return result

    def evaluate(self, request, translation):
        self.call_count += 1
        t0 = time.monotonic()
        result = self.inner.evaluate(request, translation)
        dt = time.monotonic() - t0
        summary = ", ".join(f"{e.category}/{e.severity}" for e in result.errors) or "없음"
        self.logger.info(
            f"  [Ollama #{self.call_count} · MQM 평가 Tool] {dt:.2f}s · 오류: {summary}"
        )
        if self.verbose:
            for e in result.errors:
                self.logger.debug(f"    [verbose] {e.category}/{e.severity}: {e.explanation}")
        return result

    def revise(self, request, translation, category, errors, failure_feedback=""):
        self.call_count += 1
        t0 = time.monotonic()
        result = self.inner.revise(request, translation, category, errors, failure_feedback)
        dt = time.monotonic() - t0
        self.logger.info(f"  [Ollama #{self.call_count} · {category} 수정 Tool] {dt:.2f}s")
        return result

    def user_revise(self, request, translation):
        self.call_count += 1
        t0 = time.monotonic()
        result = self.inner.user_revise(request, translation)
        dt = time.monotonic() - t0
        self.logger.info(f"  [Ollama #{self.call_count} · 사용자 지시 반영 Tool] {dt:.2f}s")
        return result


def load_sentences(which: str, limit: int) -> pd.DataFrame:
    filename = "tm_seed_40.csv" if which == "tm" else "evaluation_30.csv"
    df = pd.read_csv(FLORES_PROCESSED_DIR / filename)
    return df.head(limit) if limit else df


def chrf(hypothesis: str, reference: str) -> float | None:
    if not hypothesis or not reference:
        return None
    return round(sacrebleu.sentence_chrf(hypothesis, [reference]).score, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wikivoyage KO->EN pipeline runner with TXT logging")
    parser.add_argument("--set", choices=["tm", "eval"], default="eval")
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--agent", action="store_true", help="HUMAN_REVIEW_REQUIRED 시 Qwen Agent 개입")
    parser.add_argument(
        "--agent-first", action="store_true",
        help="고정 우선순위 Workflow(_improve())를 건너뛰고 번역 직후 바로 Agent에게 넘김",
    )
    parser.add_argument(
        "--openai-mock", action="store_true",
        help="Qwen Agent도 실패하면 OpenAI Agent(Mock, 실제 API 미호출) 개입",
    )
    parser.add_argument("--use-tm", action="store_true", default=True)
    parser.add_argument("--verbose", action="store_true", help="프롬프트/오류 전문까지 DEBUG로 기록")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--csv-out", default=None, help="미지정 시 reports/wikivoyage_comparison_<시각>.csv")
    args = parser.parse_args()

    logger, log_path = setup_run_logger(verbose=args.verbose)

    logger.info("=" * 70)
    mode = "agent-first" if args.agent_first else ("agent-fallback" if args.agent else "fixed-only")
    logger.info(f"Wikivoyage KO->EN 파이프라인 실행 시작 (set={args.set}, limit={args.limit}, mode={mode})")
    logger.info(
        f"모델 설정: model={config.MODEL_NAME} temperature={config.TEMPERATURE} seed={config.SEED} "
        f"reasoning={config.REASONING} num_predict={config.NUM_PREDICT} keep_alive={config.KEEP_ALIVE}"
    )

    tm = TranslationMemory.from_json_file(default_tm_path()) if args.use_tm else None
    terminology = Terminology.from_json_file(default_terminology_path())
    dne = DoNotEditList.from_json_file(default_dne_path())
    logger.info(
        f"리소스 로드: TM {len(tm) if tm else 0}건, 용어집 {len(terminology.entries)}건"
        f"(승인 {sum(e.approval_status=='approved' for e in terminology.entries)}), "
        f"DNE {len(dne.entries)}건(승인 {sum(e.approval_status=='approved' for e in dne.entries)})"
    )

    base_chains = OllamaChains()
    chains = LoggingChains(base_chains, logger, args.verbose)
    workflow = QualityWorkflow(chains, JsonRunStore(args.runs_dir), tm=tm)
    agent = QwenAgent(chains) if (args.agent or args.agent_first) else None
    openai_mock = OpenAIAgentMock() if args.openai_mock else None

    sentences = load_sentences(args.set, args.limit)
    logger.info(f"대상 문장 {len(sentences)}개 (source: {args.set})")

    results = []
    overall_t0 = time.monotonic()
    for row_position, (_, row) in enumerate(sentences.iterrows(), 1):
        sentence_id = row["id"]
        source = row["한국어"]
        reference = row.get("영어", "")  # scoring only - never fed to the model
        logger.info("-" * 70)
        logger.info(f"[{row_position}/{len(sentences)}] 문장 id={sentence_id} | topic={row.get('topic', '')}")
        logger.info(f"원문: {source}")
        entry = {
            "id": sentence_id,
            "source": source,
            "status": None,
            "tm_hit": None,
            "agent_used": False,
            "openai_used": False,
            "initial_translation": None,
            "final_translation": None,
            "mqm_errors_initial": None,
            "mqm_errors_final": None,
            "attempts": None,
            "calls": None,
            "seconds": None,
            "chrf": None,
            "run_id": None,
        }
        try:
            request = TranslationRequest(
                source=source, target_language="English", target_country="United States"
            )
            request = apply_resources(request, terminology, dne)
            if request.protected_terms:
                logger.info(f"적용된 DNE/용어집(protected_terms): {request.protected_terms}")
            if request.additional_instruction:
                logger.info(f"적용된 용어 지시: {request.additional_instruction}")

            calls_before = chains.call_count
            sentence_t0 = time.monotonic()

            if args.agent_first:
                entry["agent_used"] = True
                record = workflow.run_via_agent(
                    request, agent, progress_callback=lambda msg: logger.info(f"  {msg}")
                )
                entry["initial_translation"] = (
                    record.versions[0].translation if record.versions else ""
                )
                logger.info(
                    f"[Agent-first] 최종 상태={record.status.value} "
                    f"소요={time.monotonic()-sentence_t0:.2f}s 버전={len(record.versions)} "
                    f"시도={len(record.attempts)}"
                )
            else:
                record = workflow.run(
                    request, progress_callback=lambda msg: logger.info(f"  {msg}")
                )
                fixed_dt = time.monotonic() - sentence_t0
                entry["initial_translation"] = (
                    record.versions[0].translation if record.versions else ""
                )
                entry["mqm_errors_initial"] = (
                    len(record.versions[0].mqm.errors)
                    if record.versions and record.versions[0].mqm
                    else None
                )
                logger.info(f"[고정 Workflow] 상태={record.status.value} 소요={fixed_dt:.2f}s "
                            f"버전={len(record.versions)} 시도={len(record.attempts)}")

                if agent is not None and record.status == AgentStatus.HUMAN_REVIEW_REQUIRED:
                    entry["agent_used"] = True
                    t0 = time.monotonic()
                    # agent_decisions는 위 progress_callback으로 이미 실시간
                    # 출력됐다 - 여기서 목록을 또 찍으면 모든 결정이 중복 출력된다.
                    record = agent.run(record, progress_callback=lambda msg: logger.info(f"  {msg}"))
                    workflow.store.save(record)
                    logger.info(
                        f"[Qwen Agent] 최종 상태={record.status.value} 소요={time.monotonic()-t0:.2f}s"
                    )

            if openai_mock is not None and record.status == AgentStatus.HUMAN_REVIEW_REQUIRED:
                entry["openai_used"] = True
                record = openai_mock.run(record, progress_callback=lambda msg: logger.info(f"  {msg}"))
                workflow.store.save(record)

            total_dt = time.monotonic() - sentence_t0
            calls_used = chains.call_count - calls_before

            entry.update(
                {
                    "status": record.status.value,
                    "tm_hit": record.tm_hit,
                    "final_translation": record.current_version.translation if record.versions else "",
                    "mqm_errors_final": len(record.unresolved_errors),
                    "attempts": len(record.attempts),
                    "calls": calls_used,
                    "seconds": round(total_dt, 2),
                    "chrf": chrf(
                        record.current_version.translation if record.versions else "", reference
                    ),
                    "run_id": record.run_id,
                }
            )
            hitl = record.status == AgentStatus.HUMAN_REVIEW_REQUIRED
            logger.info(
                f"[문장 결과] id={sentence_id} 최종상태={record.status.value} "
                f"tm_hit={record.tm_hit} agent개입={entry['agent_used']} openai개입={entry['openai_used']} "
                f"HITL대상={hitl} 모델호출={calls_used}회 총소요={total_dt:.2f}s chrF={entry['chrf']}"
            )
        except Exception:
            entry["status"] = "EXCEPTION"
            logger.error(f"[예외] 문장 id={sentence_id} 처리 중 실패:\n{traceback.format_exc()}")
        results.append(entry)

    overall_dt = time.monotonic() - overall_t0
    logger.info("=" * 70)
    logger.info("전체 요약")
    for r in results:
        logger.info(f"  id={r['id']}: status={r['status']} tm_hit={r['tm_hit']} "
                    f"agent={r['agent_used']} openai={r['openai_used']} chrf={r['chrf']} "
                    f"calls={r['calls']} seconds={r['seconds']}")
    status_counts: dict[str, int] = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    logger.info(f"상태 분포: {status_counts}")
    logger.info(f"총 소요 시간: {overall_dt:.2f}s | 총 Ollama 호출: {chains.call_count}회")

    csv_path = Path(args.csv_out) if args.csv_out else Path(
        f"reports/wikivoyage_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(results[0].keys()) if results else []
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    logger.info(f"CSV 비교 리포트 저장: {csv_path}")
    logger.info(f"실행 종료. 로그 파일: {log_path}")

    print(f"\nTXT 로그 저장 경로: {log_path}")
    print(f"CSV 비교 리포트 저장 경로: {csv_path}")


if __name__ == "__main__":
    main()
