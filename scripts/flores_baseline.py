"""FLORES+ Baseline A(단순 번역)와 Baseline B(전체 QualityWorkflow Agent) 비교.

FLORES+ 참조 번역은 여기서 사후 chrF 채점용으로만 쓰고, `translate()`/
`workflow.run()`에는 절대 넣지 않는다. 이 스크립트가 읽는 dev/devtest 분할과
문장 id 어댑터는 `l10n_quality_agent/flores_data.py` 참고.

사용법:
    python scripts/flores_baseline.py --limit 3
    python scripts/flores_baseline.py --limit 20 --languages Japanese German
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sacrebleu

from l10n_quality_agent.chains import OllamaChains
from l10n_quality_agent.config import COUNTRY_LANGUAGE
from l10n_quality_agent.flores_data import iter_pairs
from l10n_quality_agent.schemas import TranslationRequest
from l10n_quality_agent.storage import JsonRunStore
from l10n_quality_agent.workflow import QualityWorkflow


def chrf(hypothesis: str, reference: str) -> float:
    return sacrebleu.sentence_chrf(hypothesis, [reference]).score


def run(languages, limit, split, seed, runs_dir):
    chains = OllamaChains()
    workflow = QualityWorkflow(chains, JsonRunStore(runs_dir))
    results = []
    for language in languages:
        for pair in iter_pairs(split, language, limit=limit, seed=seed):
            request = TranslationRequest(
                source=pair.source,
                target_language=pair.target_language,
                target_country=pair.target_country,
            )

            t0 = time.monotonic()
            baseline_a = chains.translate(request)
            time_a = time.monotonic() - t0

            t0 = time.monotonic()
            record_b = workflow.run(request)
            time_b = time.monotonic() - t0
            baseline_b = record_b.current_version.translation if record_b.versions else ""

            chrf_a = chrf(baseline_a, pair.reference)
            chrf_b = chrf(baseline_b, pair.reference) if baseline_b else None

            entry = {
                "split": pair.split,
                "id": pair.id,
                "target_language": language,
                "source": pair.source,
                "reference": pair.reference,
                "baseline_a": {
                    "translation": baseline_a,
                    "chrf": chrf_a,
                    "seconds": round(time_a, 2),
                },
                "baseline_b": {
                    "translation": baseline_b,
                    "chrf": chrf_b,
                    "seconds": round(time_b, 2),
                    "status": record_b.status.value,
                    "versions": len(record_b.versions),
                    "attempts": len(record_b.attempts),
                    "accepted_attempts": sum(1 for a in record_b.attempts if a.accepted),
                    "rejected_attempts": sum(1 for a in record_b.attempts if not a.accepted),
                    "run_id": record_b.run_id,
                },
            }
            results.append(entry)
            chrf_b_display = f"{chrf_b:.1f}" if chrf_b is not None else "NA"
            print(
                f"[{language}#{pair.id}] A={chrf_a:.1f} B={chrf_b_display} "
                f"status={record_b.status.value} attempts={len(record_b.attempts)}",
                flush=True,
            )
    return results


def summarize(results):
    summary: dict[str, dict] = {}
    for entry in results:
        lang = entry["target_language"]
        bucket = summary.setdefault(
            lang,
            {"a_chrf": [], "b_chrf": [], "a_sec": [], "b_sec": [], "attempts": [], "statuses": {}},
        )
        bucket["a_chrf"].append(entry["baseline_a"]["chrf"])
        if entry["baseline_b"]["chrf"] is not None:
            bucket["b_chrf"].append(entry["baseline_b"]["chrf"])
        bucket["a_sec"].append(entry["baseline_a"]["seconds"])
        bucket["b_sec"].append(entry["baseline_b"]["seconds"])
        bucket["attempts"].append(entry["baseline_b"]["attempts"])
        status = entry["baseline_b"]["status"]
        bucket["statuses"][status] = bucket["statuses"].get(status, 0) + 1

    out = {}
    for lang, b in summary.items():
        n = len(b["a_chrf"])
        out[lang] = {
            "n": n,
            "mean_chrf_a": round(sum(b["a_chrf"]) / n, 2) if n else None,
            "mean_chrf_b": round(sum(b["b_chrf"]) / len(b["b_chrf"]), 2) if b["b_chrf"] else None,
            "mean_seconds_a": round(sum(b["a_sec"]) / n, 2) if n else None,
            "mean_seconds_b": round(sum(b["b_sec"]) / n, 2) if n else None,
            "mean_attempts_b": round(sum(b["attempts"]) / n, 2) if n else None,
            "status_counts_b": b["statuses"],
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="FLORES+ Baseline A vs B")
    parser.add_argument("--languages", nargs="+", default=list(COUNTRY_LANGUAGE.values()))
    parser.add_argument("--limit", type=int, default=3, help="언어당 표본 문장 수")
    parser.add_argument("--split", default="dev", choices=["dev", "devtest"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--out", default="reports/flores_baseline_a_vs_b.json")
    args = parser.parse_args()

    results = run(args.languages, args.limit, args.split, args.seed, args.runs_dir)
    summary = summarize(results)

    out_path = PROJECT_ROOT / args.out
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n=== 요약 (언어별 평균 chrF; A=단순 번역, B=Agent 최종본) ===")
    for lang, s in summary.items():
        print(
            f"{lang}: n={s['n']} chrF A={s['mean_chrf_a']} B={s['mean_chrf_b']} | "
            f"시간 A={s['mean_seconds_a']}s B={s['mean_seconds_b']}s | "
            f"평균 시도={s['mean_attempts_b']} | 상태분포={s['status_counts_b']}"
        )
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
