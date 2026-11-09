"""사람이 읽기 편한 TXT 실행 로그. 기존 JSON 실행 기록과 CSV 비교 리포트는
건드리거나 대체하지 않고 그 옆에 따로 남긴다.

setup_run_logger()를 호출할 때마다 타임스탬프가 찍힌 새 파일을 만든다 - 이전
실행 로그에 이어쓰거나 덮어쓰지 않는다. 모든 핸들러가 즉시 flush하므로
(StreamHandler.emit은 레코드마다 flush한다), 실행 도중 크래시가 나도 그
시점까지 로그는 디스크에 남아 있다.

로그 레벨: 콘솔과 파일 모두 기본은 INFO로, 단계마다 한 줄씩 간결하게
남긴다. 프롬프트/응답 전문은 `verbose=True`를 넘겼을 때만 켜지는 DEBUG
레벨에서만 남겨야 한다. API 키 등 민감 정보는 이 로거로 절대 남기지 않는다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

DEFAULT_LOG_DIR = Path("reports/test_logs")


def setup_run_logger(
    name: str = "l10n_agent.run",
    verbose: bool = False,
    log_dir: str | Path = DEFAULT_LOG_DIR,
) -> tuple[logging.Logger, Path]:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"test_{timestamp}.txt"
    counter = 1
    while log_path.exists():
        counter += 1
        log_path = log_dir / f"test_{timestamp}_{counter}.txt"

    level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger = logging.getLogger(name)
    logger.handlers.clear()  # 한 프로세스에서 여러 번 호출돼도 핸들러가 중복 안 쌓이게
    logger.setLevel(level)
    logger.propagate = False

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger, log_path
