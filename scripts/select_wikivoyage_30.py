"""FLORES+ dev/Wikivoyage 문장을 정확히 30개 선정한다: TM/리소스 구축용 10개,
평가용 20개(id 겹침 없음). 카테고리는 데이터에 실제 있는 값(topic 필드 +
간단한 내용 휴리스틱)만으로 태깅한다 - 지어내지 않는다. 선정은 결정적(고정
시드)이고, 근거(category, topic, domain, split, sentence id)를 출력 CSV에
그대로 남겨서 나중에 검토할 수 있게 했다.

Usage: python scripts/select_wikivoyage_30.py
Writes:
    data/flores_plus/processed/wikivoyage_dev_30.csv
    data/flores_plus/processed/tm_seed_10.csv
    data/flores_plus/processed/evaluation_20.csv
"""

from __future__ import annotations

import re
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from l10n_quality_agent.config import FLORES_PROCESSED_DIR
from l10n_quality_agent.flores_data import load_split_with_provenance

SEED = 42
LATIN_PROPER_RE = re.compile(r"[A-Z][a-zA-Z]{2,}")
NUMBER_RE = re.compile(r"\d")
LONG_THRESHOLD = 80  # 글자 수 기준, wikivoyage dev 문장 길이 상위 25% 정도

# 카테고리 -> (행 조건 함수, 사람이 읽는 라벨). 순서가 중요하다 - 이 순서대로
# 카테고리를 먼저 채운다.
CATEGORIES = [
    ("안전", lambda r: "safety" in r["topic"].lower()),
    ("숙박", lambda r: "accomodation" in r["topic"].lower()),
    ("관광", lambda r: "tourism" in r["topic"].lower() or "culture" in r["topic"].lower()),
    ("교통", lambda r: "commute" in r["topic"].lower() or "sailing" in r["topic"].lower()),
    ("고유명사", lambda r: bool(LATIN_PROPER_RE.search(r["한국어"]))),
    ("숫자단위", lambda r: bool(NUMBER_RE.search(r["한국어"]))),
    ("긴문장", lambda r: len(r["한국어"]) >= LONG_THRESHOLD),
    ("일반여행안내", lambda r: r["topic"].lower() in {"travel", "traveling"}),
]


def tag_categories(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for name, predicate in CATEGORIES:
        df[f"is_{name}"] = df.apply(predicate, axis=1)
    return df


def select_30(df: pd.DataFrame) -> pd.DataFrame:
    """CATEGORIES에 적은 순서대로 카테고리를 돌면서 아직 안 뽑힌 문장을
    골라 30개를 채운다. 여러 카테고리에 해당해도 뽑힐 당시의 카테고리
    하나만 `selected_for`에 남긴다 - 전체 라벨이 아니라 선정 순서 기록이다.
    """
    remaining = df.set_index("id")
    picked_ids: list[int] = []
    picked_category: dict[int, str] = {}

    # 두 단계로 진행: 1차는 카테고리마다 2개 이상 확보(커버리지), 2차는
    # 남은 자리를 전체 풀에서 채운다.
    for target_per_category in (2, 1, 1):
        for name, _ in CATEGORIES:
            if len(picked_ids) >= 30:
                break
            pool = remaining[remaining[f"is_{name}"] & ~remaining.index.isin(picked_ids)]
            if pool.empty:
                continue
            n = min(target_per_category, len(pool), 30 - len(picked_ids))
            chosen = pool.sample(n=n, random_state=SEED)
            for sentence_id in chosen.index:
                picked_ids.append(sentence_id)
                picked_category[sentence_id] = name
        if len(picked_ids) >= 30:
            break

    if len(picked_ids) < 30:
        # 그래도 30개가 안 되면: 남은 문장 아무거나로 채운다.
        pool = remaining[~remaining.index.isin(picked_ids)]
        n = 30 - len(picked_ids)
        chosen = pool.sample(n=n, random_state=SEED)
        for sentence_id in chosen.index:
            picked_ids.append(sentence_id)
            picked_category[sentence_id] = "일반여행안내(보충)"

    picked_ids = picked_ids[:30]
    out = remaining.loc[picked_ids].reset_index()
    out["selected_for"] = out["id"].map(picked_category)
    return out


def main() -> None:
    dev = load_split_with_provenance("dev")
    wikivoyage = dev[dev["domain"] == "wikivoyage"].reset_index()  # id가 컬럼으로 들어온다
    wikivoyage = tag_categories(wikivoyage)

    selected = select_30(wikivoyage)
    # 카테고리를 번갈아 뽑았기 때문에 이미 순서 자체가 고루 섞여 있다 -
    # 그 순서대로 앞 10개는 TM 구축용, 나머지는 평가용으로 나눈다.
    tm_seed = selected.iloc[:10].reset_index(drop=True)
    evaluation = selected.iloc[10:].reset_index(drop=True)

    assert set(tm_seed["id"]).isdisjoint(set(evaluation["id"])), "TM/평가 ID 겹침 발생"
    assert len(selected) == 30
    assert len(tm_seed) == 10
    assert len(evaluation) == 20

    keep_cols = [
        "id", "split", "domain", "topic", "source_url",
        "한국어", "영어", "selected_for",
    ]
    FLORES_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    selected[keep_cols].to_csv(FLORES_PROCESSED_DIR / "wikivoyage_dev_30.csv", index=False)
    tm_seed[keep_cols].to_csv(FLORES_PROCESSED_DIR / "tm_seed_10.csv", index=False)
    evaluation[keep_cols].to_csv(FLORES_PROCESSED_DIR / "evaluation_20.csv", index=False)

    print("=== 선정 결과 (selected_for 기준 분포) ===")
    print(selected["selected_for"].value_counts())
    print(f"\nTM 구축용 10개 id: {sorted(tm_seed['id'].tolist())}")
    print(f"평가용 20개 id: {sorted(evaluation['id'].tolist())}")
    print(f"\n저장 위치: {FLORES_PROCESSED_DIR}")


if __name__ == "__main__":
    main()
