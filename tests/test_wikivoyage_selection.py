"""Validates the persisted 30-sentence Wikivoyage/dev selection
(data/flores_plus/processed/{wikivoyage_dev_30,tm_seed_10,evaluation_20}.csv)
against the hard constraints from the FLORES+ task brief: no id overlap
between the TM-build and evaluation sets, both drawn only from dev, and the
two subsets union back to exactly the 30-sentence set.
"""

import pandas as pd
import pytest

from l10n_quality_agent.config import FLORES_PROCESSED_DIR

ALL_30 = FLORES_PROCESSED_DIR / "wikivoyage_dev_30.csv"
TM_10 = FLORES_PROCESSED_DIR / "tm_seed_10.csv"
EVAL_20 = FLORES_PROCESSED_DIR / "evaluation_20.csv"

pytestmark = pytest.mark.skipif(
    not (ALL_30.exists() and TM_10.exists() and EVAL_20.exists()),
    reason="scripts/select_wikivoyage_30.py를 아직 실행하지 않음",
)


def test_no_id_overlap_between_tm_and_evaluation():
    tm = pd.read_csv(TM_10)
    ev = pd.read_csv(EVAL_20)
    assert set(tm["id"]).isdisjoint(set(ev["id"]))


def test_set_sizes_are_exactly_10_and_20():
    assert len(pd.read_csv(TM_10)) == 10
    assert len(pd.read_csv(EVAL_20)) == 20
    assert len(pd.read_csv(ALL_30)) == 30


def test_tm_and_evaluation_union_equals_the_30_selection():
    all30 = pd.read_csv(ALL_30)
    tm = pd.read_csv(TM_10)
    ev = pd.read_csv(EVAL_20)
    assert set(tm["id"]) | set(ev["id"]) == set(all30["id"])


def test_all_selected_rows_are_dev_wikivoyage():
    all30 = pd.read_csv(ALL_30)
    assert (all30["split"] == "dev").all()
    assert (all30["domain"] == "wikivoyage").all()


def test_selection_covers_multiple_categories():
    all30 = pd.read_csv(ALL_30)
    assert all30["selected_for"].nunique() >= 5
