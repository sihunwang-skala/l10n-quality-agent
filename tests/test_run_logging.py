from l10n_quality_agent.run_logging import setup_run_logger


def test_setup_run_logger_creates_a_new_timestamped_file_each_call(tmp_path):
    logger1, path1 = setup_run_logger(name="test.logger.a", log_dir=tmp_path)
    logger1.info("첫 번째 실행")
    logger2, path2 = setup_run_logger(name="test.logger.b", log_dir=tmp_path)
    logger2.info("두 번째 실행")

    assert path1 != path2
    assert path1.exists() and path2.exists()
    assert "첫 번째 실행" in path1.read_text(encoding="utf-8")
    assert "두 번째 실행" in path2.read_text(encoding="utf-8")


def test_debug_only_appears_when_verbose(tmp_path):
    logger, path = setup_run_logger(name="test.logger.quiet", verbose=False, log_dir=tmp_path)
    logger.debug("이건 안 보여야 함")
    logger.info("이건 보여야 함")
    content = path.read_text(encoding="utf-8")
    assert "이건 안 보여야 함" not in content
    assert "이건 보여야 함" in content


def test_verbose_enables_debug_output(tmp_path):
    logger, path = setup_run_logger(name="test.logger.verbose", verbose=True, log_dir=tmp_path)
    logger.debug("verbose 모드 상세 로그")
    content = path.read_text(encoding="utf-8")
    assert "verbose 모드 상세 로그" in content


def test_log_lines_are_timestamped(tmp_path):
    logger, path = setup_run_logger(name="test.logger.ts", log_dir=tmp_path)
    logger.info("시각 확인용")
    content = path.read_text(encoding="utf-8")
    # e.g. "2026-09-22 12:00:00 [INFO] 시각 확인용"
    first_line = content.strip().splitlines()[0]
    assert first_line[:4].isdigit()  # starts with a year
    assert "[INFO]" in first_line
