"""로컬 FLORES+ 7개 언어 CSV를 읽기 전용으로 다루는 최소한의 어댑터.

프로젝트 전체의 데이터 처리 방식을 대체하는 게 아니라, baseline/평가
스크립트가 필요로 하는 딱 그만큼만 담당한다 - 이 Agent가 이미 지원하는 언어
(`config.COUNTRY_LANGUAGE`) 중 하나에 대해 (source, reference) 쌍을 순회하고,
FLORES+의 dev/devtest 분할과 문장 id 정렬을 그대로 유지한다.

참조 번역은 `reference`라는 이름으로만 노출한다 - 호출하는 쪽이 실수로
번역/수정 프롬프트에 섞어 넣지 못하게 하기 위해서다(`iter_pairs` 참고).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import COUNTRY_LANGUAGE, FLORES_RAW_DIR

DATA_DIR = FLORES_RAW_DIR
SOURCE_COLUMN = "한국어"

# 이 Agent가 지원하는 target_language별 FLORES+ 컬럼명(한국어).
# English는 FLORES+ Wikivoyage KO->EN 실험을 위해 추가했다. 스페인어는
# CSV에는 있지만 이 Agent에 대응하는 target_country가 아직 없어서, 실제로
# 필요하다는 게 확인되기 전까지는 범위 밖으로 둔다.
FLORES_COLUMN_BY_LANGUAGE = {
    "English": "영어",
    "Japanese": "일본어",
    "Italian": "이탈리아어",
    "French": "프랑스어",
    "German": "독일어",
}


@dataclass(frozen=True)
class FloresPair:
    split: str
    id: int
    target_language: str
    target_country: str
    source: str
    reference: str


def _split_path(split: str) -> Path:
    if split not in {"dev", "devtest"}:
        raise ValueError(f"알 수 없는 split: {split!r} (dev 또는 devtest만 허용)")
    return DATA_DIR / f"flores_plus_7lang_{split}.csv"


def load_split(split: str) -> pd.DataFrame:
    """FLORES+ split 하나를 로드한다. 행 순서가 곧 split 내 문장 id다."""
    path = _split_path(split)
    if not path.exists():
        raise FileNotFoundError(
            f"FLORES+ 파일을 찾을 수 없음: {path}. "
            "data/flores_plus/raw/flores_plus_7lang_{dev,devtest}.csv가 있는지 확인하세요."
        )
    return pd.read_csv(path)


def load_provenance() -> pd.DataFrame:
    return pd.read_csv(FLORES_RAW_DIR / "flores_plus_7lang_provenance.csv")


def load_split_with_provenance(split: str) -> pd.DataFrame:
    """split의 병렬 문장들을 문장 id 기준으로 provenance 행과 결합한다.

    dev.csv/devtest.csv에는 자체 id 컬럼이 없다 - split 내 행 위치가 곧 id다
    (구조적으로 확인함: flores_plus_7lang_all_2009.csv는 concat(dev, devtest)와
    행 단위로 정확히 일치하고, provenance의 split별 id 범위도 각 split 행
    수만큼 0..N-1로 빈틈없이 이어진다). 이 전제를 그냥 가정만 하고 넘어가지
    않도록 `tests/test_flores_data.py`가 같은 구조적 사실을 검증한다 - 나중에
    데이터가 바뀌어 이 전제가 깨지면 조용히 문장이 어긋나는 대신 테스트가
    바로 실패한다.
    """
    df = load_split(split).reset_index(drop=True)
    df.index.name = "id"
    prov = load_provenance()
    prov_split = prov[prov["split"] == split].set_index("id").sort_index()
    if len(prov_split) != len(df):
        raise ValueError(
            f"{split}: provenance 행 수({len(prov_split)})와 CSV 행 수({len(df)})가 다름"
        )
    if list(prov_split.index) != list(range(len(df))):
        raise ValueError(f"{split}: provenance id가 0..N-1 연속이 아님 - 정렬/결합 불가")
    return df.join(prov_split, how="left")


def iter_pairs(
    split: str,
    target_language: str,
    limit: int | None = None,
    seed: int | None = 42,
):
    """split 하나에 대해 FloresPair(source=한국어, reference=target_language)를 순회한다.

    `reference`는 FLORES+의 사람 번역이다 - chrF 같은 채점 용도로만 쓰고,
    번역/수정 체인의 입력으로는 절대 넣지 않아야 한다.
    """
    if target_language not in FLORES_COLUMN_BY_LANGUAGE:
        supported = ", ".join(FLORES_COLUMN_BY_LANGUAGE)
        raise ValueError(
            f"이 Agent가 아직 지원하지 않는 target_language: {target_language!r} "
            f"(지원: {supported})"
        )
    target_country = next(
        country
        for country, language in COUNTRY_LANGUAGE.items()
        if language == target_language
    )
    column = FLORES_COLUMN_BY_LANGUAGE[target_language]
    df = load_split(split)
    if limit is not None:
        df = df.sample(n=min(limit, len(df)), random_state=seed).sort_index()
    for row_id, row in df.iterrows():
        yield FloresPair(
            split=split,
            id=int(row_id),
            target_language=target_language,
            target_country=target_country,
            source=row[SOURCE_COLUMN],
            reference=row[column],
        )
