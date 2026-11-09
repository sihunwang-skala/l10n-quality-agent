"""tm_seed_10.csv로 Wikivoyage KO->EN 시드 TM을 만들어
data/flores_plus/resources/tm/ 아래 JSON으로 저장한다. 완전 일치만 지원.

사용법: python scripts/build_tm.py
"""

from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from l10n_quality_agent.config import FLORES_PROCESSED_DIR, TM_DIR
from l10n_quality_agent.tm import build_tm_from_seed_csv, default_tm_path


def main() -> None:
    csv_path = FLORES_PROCESSED_DIR / "tm_seed_40.csv"
    tm = build_tm_from_seed_csv(csv_path, target_language="English")
    TM_DIR.mkdir(parents=True, exist_ok=True)
    out_path = default_tm_path()
    out_path.write_text(tm.to_json(), encoding="utf-8")
    print(f"TM 항목 {len(tm)}개 저장: {out_path}")


if __name__ == "__main__":
    main()
