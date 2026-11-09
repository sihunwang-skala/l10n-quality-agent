"""Wikivoyage/dev 선정 규모를 TM 10 + 평가 20(총 30)에서 최신 결정인
TM 40 + 평가 30(총 70)으로 확장한다.

교체가 아니라 확장이다: 기존 TM 시드 10개, 평가 20개 id는 그대로 둔다
(그래야 이미 구축한 TM과 이미 돌린 Agent 실험이 계속 유효하다) - 나머지
Wikivoyage/dev 풀에서 TM 후보 30개, 평가 후보 10개를 *추가로* 고르되,
select_wikivoyage_30.py의 카테고리 태깅·라운드로빈 선정 로직을 그대로
재사용해서 새 문장도 같은 근거 기반 방식으로 뽑는다.

Usage: python scripts/expand_wikivoyage_selection.py
Writes:
    data/flores_plus/processed/wikivoyage_dev_70.csv
    data/flores_plus/processed/tm_seed_40.csv
    data/flores_plus/processed/evaluation_30.csv
(old wikivoyage_dev_30.csv/tm_seed_10.csv/evaluation_20.csv are left in
place untouched, as the historical record of the first selection round)
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for path in (PROJECT_ROOT, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pandas as pd

from l10n_quality_agent.config import FLORES_PROCESSED_DIR
from l10n_quality_agent.flores_data import load_split_with_provenance
from select_wikivoyage_30 import CATEGORIES, SEED, tag_categories

KEEP_COLS = ["id", "split", "domain", "topic", "source_url", "한국어", "영어", "selected_for"]


def select_n_more(pool: pd.DataFrame, n: int, exclude_ids: set[int]) -> pd.DataFrame:
    remaining = pool[~pool["id"].isin(exclude_ids)].set_index("id")
    picked_ids: list[int] = []
    picked_category: dict[int, str] = {}

    for target_per_category in (2, 1, 1, 1, 1):
        for name, _ in CATEGORIES:
            if len(picked_ids) >= n:
                break
            already = set(picked_ids)
            candidate_pool = remaining[remaining[f"is_{name}"] & ~remaining.index.isin(already)]
            if candidate_pool.empty:
                continue
            take = min(target_per_category, len(candidate_pool), n - len(picked_ids))
            chosen = candidate_pool.sample(n=take, random_state=SEED)
            for sentence_id in chosen.index:
                picked_ids.append(sentence_id)
                picked_category[sentence_id] = name
        if len(picked_ids) >= n:
            break

    if len(picked_ids) < n:
        leftover = remaining[~remaining.index.isin(picked_ids)]
        take = n - len(picked_ids)
        chosen = leftover.sample(n=take, random_state=SEED)
        for sentence_id in chosen.index:
            picked_ids.append(sentence_id)
            picked_category[sentence_id] = "일반여행안내(보충)"

    picked_ids = picked_ids[:n]
    out = remaining.loc[picked_ids].reset_index()
    out["selected_for"] = out["id"].map(picked_category)
    return out


def main() -> None:
    old_tm = pd.read_csv(FLORES_PROCESSED_DIR / "tm_seed_10.csv")
    old_eval = pd.read_csv(FLORES_PROCESSED_DIR / "evaluation_20.csv")
    assert set(old_tm["id"]).isdisjoint(set(old_eval["id"])), "기존 10/20 선택에 이미 겹침 존재"

    dev = load_split_with_provenance("dev")
    wikivoyage = dev[dev["domain"] == "wikivoyage"].reset_index()
    wikivoyage = tag_categories(wikivoyage)

    already_used = set(old_tm["id"]) | set(old_eval["id"])

    new_tm = select_n_more(wikivoyage, n=30, exclude_ids=already_used)
    new_eval = select_n_more(
        wikivoyage, n=10, exclude_ids=already_used | set(new_tm["id"])
    )

    tm_40 = pd.concat([old_tm[KEEP_COLS], new_tm[KEEP_COLS]], ignore_index=True)
    eval_30 = pd.concat([old_eval[KEEP_COLS], new_eval[KEEP_COLS]], ignore_index=True)
    all_70 = pd.concat([tm_40, eval_30], ignore_index=True)

    assert set(tm_40["id"]).isdisjoint(set(eval_30["id"])), "TM/평가 ID 겹침 발생"
    assert len(tm_40) == 40
    assert len(eval_30) == 30
    assert len(all_70) == 70
    assert set(old_tm["id"]) <= set(tm_40["id"]), "기존 TM 10개가 40개 안에 그대로 포함돼야 함"
    assert set(old_eval["id"]) <= set(eval_30["id"]), "기존 평가 20개가 30개 안에 그대로 포함돼야 함"

    all_70.to_csv(FLORES_PROCESSED_DIR / "wikivoyage_dev_70.csv", index=False)
    tm_40.to_csv(FLORES_PROCESSED_DIR / "tm_seed_40.csv", index=False)
    eval_30.to_csv(FLORES_PROCESSED_DIR / "evaluation_30.csv", index=False)

    print(f"TM 40개 (기존 10 + 신규 30), 평가 30개 (기존 20 + 신규 10)")
    print(f"신규 TM 30개 카테고리 분포:\n{new_tm['selected_for'].value_counts()}")
    print(f"신규 평가 10개 카테고리 분포:\n{new_eval['selected_for'].value_counts()}")
    print(f"저장 위치: {FLORES_PROCESSED_DIR}")


if __name__ == "__main__":
    main()
