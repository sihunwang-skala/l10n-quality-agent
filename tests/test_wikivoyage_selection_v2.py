"""Validates the expanded selection (TM 40 + evaluation 30 = 70), the
current decision superseding the original 10+20. See
test_wikivoyage_selection.py for the still-valid checks on the original
30-sentence round this one extends.
"""

import pandas as pd
import pytest

from l10n_quality_agent.config import FLORES_PROCESSED_DIR

ALL_70 = FLORES_PROCESSED_DIR / "wikivoyage_dev_70.csv"
TM_40 = FLORES_PROCESSED_DIR / "tm_seed_40.csv"
EVAL_30 = FLORES_PROCESSED_DIR / "evaluation_30.csv"
TM_10 = FLORES_PROCESSED_DIR / "tm_seed_10.csv"
EVAL_20 = FLORES_PROCESSED_DIR / "evaluation_20.csv"

pytestmark = pytest.mark.skipif(
    not (ALL_70.exists() and TM_40.exists() and EVAL_30.exists()),
    reason="scripts/expand_wikivoyage_selection.py를 아직 실행하지 않음",
)


def test_no_id_overlap_between_tm_40_and_evaluation_30():
    tm = pd.read_csv(TM_40)
    ev = pd.read_csv(EVAL_30)
    assert set(tm["id"]).isdisjoint(set(ev["id"]))


def test_set_sizes_are_exactly_40_30_and_70():
    assert len(pd.read_csv(TM_40)) == 40
    assert len(pd.read_csv(EVAL_30)) == 30
    assert len(pd.read_csv(ALL_70)) == 70


def test_tm_and_evaluation_union_equals_the_70_selection():
    all70 = pd.read_csv(ALL_70)
    tm = pd.read_csv(TM_40)
    ev = pd.read_csv(EVAL_30)
    assert set(tm["id"]) | set(ev["id"]) == set(all70["id"])


def test_original_10_and_20_are_preserved_as_subsets():
    """The expansion must extend, not replace: the original TM-seed and
    evaluation sentences (already built into the TM, already used in the
    Agent experiments) must still be present in the new 40/30 sets."""
    old_tm = pd.read_csv(TM_10)
    old_eval = pd.read_csv(EVAL_20)
    tm_40 = pd.read_csv(TM_40)
    eval_30 = pd.read_csv(EVAL_30)
    assert set(old_tm["id"]) <= set(tm_40["id"])
    assert set(old_eval["id"]) <= set(eval_30["id"])


def test_all_selected_rows_are_dev_wikivoyage():
    all70 = pd.read_csv(ALL_70)
    assert (all70["split"] == "dev").all()
    assert (all70["domain"] == "wikivoyage").all()


def test_no_duplicate_ids_within_the_70():
    all70 = pd.read_csv(ALL_70)
    assert all70["id"].duplicated().sum() == 0
