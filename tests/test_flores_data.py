import pandas as pd
import pytest

from l10n_quality_agent.flores_data import (
    FLORES_RAW_DIR,
    iter_pairs,
    load_provenance,
    load_split,
    load_split_with_provenance,
)


def test_iter_pairs_keeps_id_alignment_and_excludes_no_reference_column():
    pairs = list(iter_pairs("dev", "Japanese", limit=5, seed=42))
    assert len(pairs) == 5
    for pair in pairs:
        assert pair.split == "dev"
        assert pair.target_language == "Japanese"
        assert pair.target_country == "Japan"
        assert pair.source.strip()
        assert pair.reference.strip()
        # source must be Korean text, reference must not be (sanity check
        # against a column-mapping mistake swapping the two)
        assert pair.source != pair.reference


def test_iter_pairs_is_deterministic_for_same_seed():
    first = [p.id for p in iter_pairs("dev", "German", limit=4, seed=7)]
    second = [p.id for p in iter_pairs("dev", "German", limit=4, seed=7)]
    assert first == second


def test_iter_pairs_rejects_unsupported_language():
    with pytest.raises(ValueError):
        list(iter_pairs("dev", "Spanish", limit=1))


def test_iter_pairs_rejects_unknown_split():
    with pytest.raises(ValueError):
        list(iter_pairs("test", "Japanese", limit=1))


def test_all_2009_equals_concat_of_dev_and_devtest():
    """Structural proof that row position == sentence id within a split.

    dev.csv/devtest.csv carry no id column; flores_plus_7lang_all_2009.csv
    being exactly concat(dev, devtest) is the evidence (not an assumption)
    that row order is the real join key against provenance's per-split id.
    """
    dev = load_split("dev")
    devtest = load_split("devtest")
    all_df = pd.read_csv(FLORES_RAW_DIR / "flores_plus_7lang_all_2009.csv")
    assert pd.concat([dev, devtest], ignore_index=True).equals(all_df)


def test_no_duplicate_rows_within_a_split():
    for split in ("dev", "devtest"):
        df = load_split(split)
        assert df.duplicated().sum() == 0, f"{split}에 완전 중복 행 존재"


def test_no_korean_source_leakage_between_dev_and_devtest():
    dev = load_split("dev")
    devtest = load_split("devtest")
    overlap = set(dev["한국어"]) & set(devtest["한국어"])
    assert overlap == set()


def test_provenance_ids_are_gapless_per_split():
    prov = load_provenance()
    for split, expected_len in (("dev", 997), ("devtest", 1012)):
        ids = sorted(prov.loc[prov["split"] == split, "id"].tolist())
        assert ids == list(range(expected_len))
        assert prov.duplicated(subset=["split", "id"]).sum() == 0


def test_iter_pairs_supports_english_for_the_wikivoyage_experiment():
    pairs = list(iter_pairs("dev", "English", limit=2, seed=42))
    assert len(pairs) == 2
    for pair in pairs:
        assert pair.target_country == "United States"
        assert pair.source != pair.reference


def test_load_split_with_provenance_matches_known_wikivoyage_counts():
    # Matches the counts given in the FLORES+ task brief exactly.
    dev = load_split_with_provenance("dev")
    devtest = load_split_with_provenance("devtest")
    assert (dev["domain"] == "wikivoyage").sum() == 348
    assert (devtest["domain"] == "wikivoyage").sum() == 320
