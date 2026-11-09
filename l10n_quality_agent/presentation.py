"""CLI와 노트북이 공유하는, 사람이 읽기 좋은 출력 도우미."""

from __future__ import annotations

from .schemas import AgentStatus, RunRecord


def format_record(record: RunRecord) -> str:
    lines = [
        "=" * 40,
        f"실행 ID: {record.run_id}",
        f"상태: {record.status.value}",
        f"원문: {record.request.source}",
    ]
    if record.tm_hit:
        lines.append(f"TM 매칭: source_id={record.tm_source_id} (신규 번역 생략)")
    if record.versions:
        lines.append(f"현재 번역: {record.current_version.translation}")
        lines.append("번역 버전:")
        lines.extend(
            f"- v{version.version}: {version.translation}"
            for version in record.versions
        )
    if record.attempts:
        lines.append("수정 이력:")
        for attempt in record.attempts:
            result = "채택" if attempt.accepted else "거부"
            lines.append(
                f"- {attempt.category} {attempt.attempt}/2: {result} / {attempt.candidate}"
            )
            lines.extend(f"  사유: {reason}" for reason in attempt.failure_reasons)
    if record.agent_decisions:
        lines.append("Qwen Agent 전략 결정:")
        lines.extend(f"- {decision}" for decision in record.agent_decisions)
    if record.unresolved_errors:
        lines.append("해결되지 않은 오류:")
        lines.extend(
            f"- {error.category} ({error.severity}): {error.explanation}"
            for error in record.unresolved_errors
        )
    lines.extend(f"실패 사유: {reason}" for reason in record.failure_reasons)
    if record.status == AgentStatus.HUMAN_REVIEW_REQUIRED:
        lines.insert(1, "자동 수정 중단: 사람 검토 필요")
    lines.append("=" * 40)
    return "\n".join(lines)

