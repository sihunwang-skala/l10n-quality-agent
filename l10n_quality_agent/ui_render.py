"""Gradio UI가 쓰는 HTML 렌더링 도우미 (순수 함수, 모델·네트워크 호출 없음).

RunRecord를 받아 진행 단계, 상태 배지, MQM 오류 카드, 수정 이력 타임라인,
버전 diff를 HTML 조각으로 만든다. 사용자 입력/모델 출력은 모두 escape한다.
"""

from __future__ import annotations

import difflib
from html import escape

from .schemas import AgentStatus, MQMError, RunRecord

STEPS = ["번역", "MQM 평가", "전문 수정", "재검증", "사람 승인"]

# status -> (한글 라벨, css 클래스, 아이콘)
STATUS_META = {
    AgentStatus.DRAFT: ("초안", "st-idle", "●"),
    AgentStatus.EVALUATING: ("평가 중", "st-run", "◔"),
    AgentStatus.REVISING: ("수정 중", "st-run", "◑"),
    AgentStatus.HUMAN_REVIEW_REQUIRED: ("사람 검토 필요", "st-warn", "!"),
    AgentStatus.AWAITING_HUMAN_APPROVAL: ("승인 대기", "st-wait", "◷"),
    AgentStatus.APPROVED: ("승인됨", "st-ok", "✓"),
    AgentStatus.REJECTED: ("거부됨", "st-bad", "✕"),
}

SEVERITY_LABEL = {"minor": "경미", "major": "주요", "critical": "치명"}

CSS = """
:root { --lq-ink:#1f2430; --lq-mute:#6b7385; --lq-line:#e3e6ee; --lq-bg:#f6f7fb; --lq-card:#fff;
  --lq-brand:#4f46e5; --lq-ok:#16a34a; --lq-warn:#d97706; --lq-bad:#dc2626; --lq-wait:#2563eb; }
.dark { --lq-ink:#e8eaf0; --lq-mute:#9aa3b8; --lq-line:#2d3342; --lq-bg:#171a23; --lq-card:#1f2330; }
.gradio-container { max-width: 1280px !important; }
.lq-hero { display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
  padding:20px 24px; border-radius:16px; color:#fff;
  background:linear-gradient(120deg,#4338ca 0%,#6366f1 55%,#0ea5e9 100%); }
.lq-hero h1 { margin:0; font-size:1.55rem; letter-spacing:-.01em; color:#fff; }
.lq-hero p { margin:4px 0 0; opacity:.9; font-size:.92rem; color:#fff; }
.lq-badges { display:flex; gap:8px; flex-wrap:wrap; }
.lq-badge { background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.3); color:#fff;
  padding:4px 10px; border-radius:999px; font-size:.78rem; white-space:nowrap; }
.lq-card { background:var(--lq-card); border:1px solid var(--lq-line); border-radius:14px;
  padding:16px 18px; margin:0 0 14px; color:var(--lq-ink); }
.lq-head { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:12px; }
.lq-country { font-weight:700; font-size:1.05rem; }
.lq-lang { color:var(--lq-mute); font-size:.85rem; }
.lq-pill { margin-left:auto; padding:4px 12px; border-radius:999px; font-size:.8rem; font-weight:600; }
.st-idle { background:#e5e7eb; color:#374151; } .st-run { background:#e0e7ff; color:#3730a3; }
.st-warn { background:#fef3c7; color:#92400e; } .st-wait { background:#dbeafe; color:#1e40af; }
.st-ok { background:#dcfce7; color:#166534; } .st-bad { background:#fee2e2; color:#991b1b; }
.lq-steps { display:flex; gap:6px; margin:4px 0 14px; }
.lq-step { flex:1; text-align:center; font-size:.75rem; color:var(--lq-mute); padding-top:8px;
  border-top:4px solid var(--lq-line); border-radius:2px; }
.lq-step.done { border-color:var(--lq-ok); color:var(--lq-ok); }
.lq-step.now { border-color:var(--lq-brand); color:var(--lq-brand); font-weight:700; }
.lq-step.now.pulse { animation:lqpulse 1.2s ease-in-out infinite; }
.lq-step.warn { border-color:var(--lq-warn); color:var(--lq-warn); font-weight:700; }
.lq-step.bad { border-color:var(--lq-bad); color:var(--lq-bad); font-weight:700; }
@keyframes lqpulse { 50% { opacity:.45; } }
.lq-cols { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
@media (max-width:760px) { .lq-cols { grid-template-columns:1fr; } .lq-steps { flex-wrap:wrap; } }
.lq-box { background:var(--lq-bg); border:1px solid var(--lq-line); border-radius:10px; padding:10px 12px; }
.lq-label { font-size:.72rem; color:var(--lq-mute); text-transform:uppercase; letter-spacing:.05em; margin-bottom:4px; }
.lq-text { font-size:1rem; line-height:1.6; white-space:pre-wrap; word-break:break-word; }
.lq-metrics { display:flex; gap:10px; flex-wrap:wrap; margin:12px 0; }
.lq-metric { flex:1; min-width:96px; background:var(--lq-bg); border:1px solid var(--lq-line);
  border-radius:10px; padding:8px 12px; }
.lq-metric b { display:block; font-size:1.3rem; line-height:1.2; }
.lq-metric span { font-size:.72rem; color:var(--lq-mute); }
.lq-h { font-size:.85rem; font-weight:700; margin:14px 0 6px; }
.lq-err { border-left:4px solid var(--lq-warn); background:var(--lq-bg); border-radius:8px;
  padding:8px 12px; margin-bottom:6px; font-size:.88rem; line-height:1.5; }
.lq-err.major { border-color:#ea580c; } .lq-err.critical { border-color:var(--lq-bad); }
.lq-tag { display:inline-block; padding:1px 8px; border-radius:6px; font-size:.72rem; font-weight:600;
  background:#e0e7ff; color:#3730a3; margin-right:6px; }
.lq-tag.sev { background:#fde68a; color:#78350f; }
.lq-tl { position:relative; margin-left:8px; padding-left:18px; border-left:2px solid var(--lq-line); }
.lq-ev { position:relative; margin-bottom:10px; font-size:.86rem; line-height:1.5; }
.lq-ev::before { content:""; position:absolute; left:-25px; top:5px; width:10px; height:10px; border-radius:50%;
  background:var(--lq-mute); border:2px solid var(--lq-card); }
.lq-ev.ok::before { background:var(--lq-ok); } .lq-ev.no::before { background:var(--lq-bad); }
.lq-ev small { color:var(--lq-mute); display:block; }
.lq-details { margin-top:10px; font-size:.85rem; } .lq-details summary { cursor:pointer; color:var(--lq-brand); }
.lq-details p { margin:6px 0; line-height:1.55; }
.lq-diff ins { background:#bbf7d0; color:#14532d; text-decoration:none; border-radius:3px; padding:0 1px; }
.lq-diff del { background:#fecaca; color:#7f1d1d; border-radius:3px; padding:0 1px; }
.lq-empty { text-align:center; color:var(--lq-mute); padding:48px 16px; border:2px dashed var(--lq-line);
  border-radius:14px; }
.lq-empty b { display:block; font-size:1.05rem; color:var(--lq-ink); margin-bottom:6px; }
.lq-live { display:flex; align-items:center; gap:10px; font-size:.88rem; color:var(--lq-brand); margin-bottom:8px; }
.lq-dot { width:10px; height:10px; border-radius:50%; background:var(--lq-brand); animation:lqpulse 1s infinite; }
.lq-stats { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px; }
"""


def status_pill(status: AgentStatus) -> str:
    label, css, icon = STATUS_META.get(status, (str(status), "st-idle", "●"))
    return f'<span class="lq-pill {css}">{icon} {escape(label)}</span>'


def stage_from_message(message: str) -> int:
    """진행 로그 한 줄에서 현재 파이프라인 단계를 추정한다 (0~3)."""
    if "초기 번역" in message or "입력 확인" in message:
        return 1
    if "재평가" in message or "재검증" in message or "채택" in message or "거부" in message:
        return 3
    if "전략 선택" in message or "수정" in message:
        return 2
    if "MQM" in message:
        return 1
    return 0


def render_stepper(status: AgentStatus | None = None, stage: int | None = None, pulse: bool = False) -> str:
    """status(완료 기록) 또는 stage(진행 중 단계 인덱스)로 5단계 진행 표시줄을 만든다."""
    marks: list[str] = []
    for index in range(len(STEPS)):
        css = ""
        if status is not None:
            last = len(STEPS) - 1
            if status == AgentStatus.APPROVED:
                css = "done"
            elif status == AgentStatus.REJECTED:
                css = "bad" if index == last else "done"
            elif status == AgentStatus.HUMAN_REVIEW_REQUIRED:
                css = "warn" if index == last else "done"
            elif status == AgentStatus.AWAITING_HUMAN_APPROVAL:
                css = "now" if index == last else "done"
            else:
                css = "done" if index < 1 else ("now" if index == 1 else "")
        elif stage is not None:
            css = "done" if index < stage else ("now pulse" if index == stage and pulse else "now" if index == stage else "")
        marks.append(f'<div class="lq-step {css}">{index + 1}. {escape(STEPS[index])}</div>')
    return '<div class="lq-steps">' + "".join(marks) + "</div>"


def _error_card(error: MQMError) -> str:
    fix = f"<br>💡 제안: {escape(error.suggested_fix)}" if error.suggested_fix else ""
    span = f"<br>구간: <code>{escape(error.span)}</code>" if error.span else ""
    return (
        f'<div class="lq-err {escape(error.severity)}">'
        f'<span class="lq-tag">{escape(error.category)}</span>'
        f'<span class="lq-tag sev">{escape(SEVERITY_LABEL.get(error.severity, error.severity))}</span>'
        f"{escape(error.explanation)}{span}{fix}</div>"
    )


def _timeline(record: RunRecord) -> str:
    if not record.attempts:
        return ""
    events = []
    for attempt in record.attempts:
        ok = attempt.accepted
        reasons = "".join(f"<br>· {escape(reason)}" for reason in attempt.failure_reasons)
        before = len(attempt.mqm_before.errors)
        after = len(attempt.mqm_after.errors) if attempt.mqm_after else None
        delta = f"오류 {before}개 → {after}개" if after is not None else f"오류 {before}개"
        events.append(
            f'<div class="lq-ev {"ok" if ok else "no"}">'
            f'<b>{escape(attempt.category)}</b> {attempt.attempt}차 시도 · '
            f'{"채택" if ok else "거부 (Rollback)"} <small>{escape(delta)}</small>'
            f'<small>{escape(attempt.candidate)}</small>{reasons}</div>'
        )
    return '<div class="lq-h">🛠 수정 이력</div><div class="lq-tl">' + "".join(events) + "</div>"


def render_run_card(record: RunRecord, country: str = "") -> str:
    current = record.versions[-1].translation if record.versions else ""
    accepted = sum(1 for attempt in record.attempts if attempt.accepted)
    rejected = len(record.attempts) - accepted
    metrics = [
        (f"v{record.versions[-1].version}" if record.versions else "-", "현재 버전"),
        (str(len(record.attempts)), f"수정 시도 (채택 {accepted} · 거부 {rejected})"),
        (str(len(record.unresolved_errors)), "남은 오류"),
        ("TM 일치" if record.tm_hit else "신규", "초기 번역"),
    ]
    metric_html = "".join(
        f'<div class="lq-metric"><b>{escape(value)}</b><span>{escape(label)}</span></div>'
        for value, label in metrics
    )
    errors = "".join(_error_card(error) for error in record.unresolved_errors)
    errors_html = f'<div class="lq-h">⚠ 해결되지 않은 오류</div>{errors}' if errors else ""
    reasons = "".join(f"<p>· {escape(reason)}</p>" for reason in record.failure_reasons)
    reasons_html = f'<div class="lq-h">실패 사유</div>{reasons}' if reasons else ""
    decisions = ""
    if record.agent_decisions:
        items = "".join(f"<p>{escape(decision)}</p>" for decision in record.agent_decisions)
        decisions = (
            f'<details class="lq-details"><summary>🤖 Agent 판단 근거 ({len(record.agent_decisions)})</summary>{items}</details>'
        )
    return (
        '<div class="lq-card">'
        f'<div class="lq-head"><span class="lq-country">{escape(country or record.request.target_country)}</span>'
        f'<span class="lq-lang">{escape(record.request.target_language)} · run {escape(record.run_id[:8])}</span>'
        f"{status_pill(record.status)}</div>"
        f"{render_stepper(status=record.status)}"
        '<div class="lq-cols">'
        f'<div class="lq-box"><div class="lq-label">한국어 원문</div><div class="lq-text">{escape(record.request.source)}</div></div>'
        f'<div class="lq-box"><div class="lq-label">번역 ({escape(record.request.target_language)})</div>'
        f'<div class="lq-text">{escape(current)}</div></div></div>'
        f'<div class="lq-metrics">{metric_html}</div>'
        f"{errors_html}{reasons_html}{_timeline(record)}{decisions}</div>"
    )


def render_live(country: str, index: int, total: int, stage: int, message: str, done_cards: list[str]) -> str:
    live = (
        '<div class="lq-card">'
        f'<div class="lq-live"><span class="lq-dot"></span>'
        f"<b>{escape(country)}</b> 처리 중 · 전체 {index - 1}/{total}개 완료</div>"
        f"{render_stepper(stage=stage, pulse=True)}"
        f'<div class="lq-text" style="font-size:.85rem;color:var(--lq-mute)">{escape(message)}</div></div>'
    )
    return live + "".join(done_cards)


def render_empty() -> str:
    return (
        '<div class="lq-empty"><b>아직 실행 결과가 없습니다</b>'
        "왼쪽에서 입력 방식(PoC 테스트 · 직접 입력 · CSV 업로드)과 목표 국가를 고른 뒤 ‘번역 실행’을 누르세요.</div>"
    )


def render_diff(old: str, new: str) -> str:
    """두 번역문의 글자 단위 차이를 보여준다 (CJK에서도 읽히도록 문자 기준)."""
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    parts = []
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(escape(old[a0:a1]))
            continue
        if a1 > a0:
            parts.append(f"<del>{escape(old[a0:a1])}</del>")
        if b1 > b0:
            parts.append(f"<ins>{escape(new[b0:b1])}</ins>")
    return '<div class="lq-card lq-diff"><div class="lq-label">선택 버전 → 현재 버전 변경점</div>' \
           f'<div class="lq-text">{"".join(parts)}</div></div>'


def render_version_diff(record: RunRecord, version: int | None) -> str:
    if not record.versions:
        return ""
    chosen = next((item for item in record.versions if item.version == version), record.versions[-1])
    if chosen.translation == record.versions[-1].translation:
        return (
            '<div class="lq-card"><div class="lq-label">버전 비교</div>'
            '<div class="lq-text" style="color:var(--lq-mute)">선택한 버전이 현재 버전과 같습니다. '
            "이전 버전을 고르면 변경점이 표시됩니다.</div></div>"
        )
    return render_diff(chosen.translation, record.versions[-1].translation)


def render_status_stats(statuses: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in statuses:
        counts[value] = counts.get(value, 0) + 1
    css = {s.value: STATUS_META[s][1] for s in STATUS_META}
    chips = "".join(
        f'<span class="lq-pill {css.get(name, "st-idle")}" style="margin-left:0">{escape(name)} · {count}</span>'
        for name, count in counts.items()
    )
    return f'<div class="lq-stats">{chips}</div>' if chips else ""


def render_hero(openai_tag: str, resources: list[str]) -> str:
    badges = ["Qwen 로컬 Agent", f"OpenAI · {openai_tag}"] + resources
    chips = "".join(f'<span class="lq-badge">{escape(item)}</span>' for item in badges)
    return (
        '<div class="lq-hero"><div><h1>L10n Quality Agent</h1>'
        "<p>번역 → MQM 평가 → 유형별 수정 → 재검증 → 사람 승인. 모든 과정이 기록됩니다.</p></div>"
        f'<div class="lq-badges">{chips}</div></div>'
    )


MODE_GUIDES = {
    "poc": {
        "title": "🧪 PoC 테스트 · 내장 예시 문장",
        "intent": "프로젝트가 정상 동작하는지 확인하는 <b>테스트·데모용</b> 모드입니다.",
        "input": "내장 문장 30개 중 <b>1개 선택</b> (직접 입력할 것 없음)",
        "does": "공개 데이터 FLORES+ 문장을 번역 → MQM 평가 → 수정합니다. 결과 CSV의 <code>id</code>에 문장 번호가 기록됩니다.",
        "when": "설치 확인, 데모, 모델·프롬프트를 바꾼 뒤 같은 문장으로 비교할 때",
    },
    "direct": {
        "title": "✍️ 직접 입력 · 사람이 타이핑",
        "intent": "<b>사람이 문장을 직접 쓰고</b> 한 건씩 결과를 확인하는 모드입니다.",
        "input": "한국어 원문 <b>(필수)</b> · 보호 용어, 추가 지시 <b>(선택)</b>",
        "does": "입력한 한 문장을 선택한 국가마다 따로 실행합니다. 결과를 보고 직접 수정·AI 재수정·승인할 수 있습니다.",
        "when": "실제 업무 문장의 품질을 점검하거나, 특정 용어가 유지되는지 시험할 때",
    },
    "csv": {
        "title": "📄 CSV 업로드 · 자동 일괄 번역",
        "intent": "여러 문장이 담긴 <b>CSV 파일을 올리면 모든 행을 자동으로</b> 차례대로 번역합니다.",
        "input": "<code>한국어</code> 열이 있는 CSV <b>(필수)</b> · 선택 열: <code>id</code>, <code>목표국가</code>, <code>보호용어</code>, <code>추가지시</code> · 최대 30문장",
        "does": "행마다 번역 → MQM → 수정까지 <b>자동</b>으로 실행하고 결과 CSV에 저장합니다. <b>최종 승인은 자동이 아니라</b> ‘검토·승인’ 탭에서 사람이 합니다.",
        "when": "문장 여러 개를 한꺼번에 점검할 때. 아래 양식을 내려받아 채우면 됩니다",
    },
}


def render_mode_guide(mode: str) -> str:
    key = "csv" if "CSV" in mode else "poc" if "PoC" in mode else "direct"
    guide = MODE_GUIDES[key]
    rows = [("입력할 것", guide["input"]), ("하는 일", guide["does"]), ("이럴 때", guide["when"])]
    body = "".join(
        f'<div style="display:flex;gap:10px;margin-top:6px"><div class="lq-label" style="min-width:64px;margin:3px 0 0">{label}</div>'
        f'<div style="font-size:.85rem;line-height:1.5">{text}</div></div>'
        for label, text in rows
    )
    return (
        '<div class="lq-card" style="margin:8px 0 12px">'
        f'<div style="font-weight:700;margin-bottom:4px">{guide["title"]}</div>'
        f'<div style="font-size:.88rem">{guide["intent"]}</div>{body}</div>'
    )


def render_csv_check(rows: int, jobs: int, errors: list[str]) -> str:
    if errors:
        items = "".join(f"<li>{escape(error)}</li>" for error in errors[:8])
        return (
            '<div class="lq-card" style="border-color:var(--lq-bad)"><b style="color:var(--lq-bad)">'
            f"실행할 수 없습니다</b><ul style=\"margin:6px 0 0 18px;font-size:.85rem\">{items}</ul></div>"
        )
    return (
        '<div class="lq-card" style="border-color:var(--lq-ok)"><b style="color:var(--lq-ok)">✓ 실행 준비 완료</b>'
        f'<div style="font-size:.85rem;margin-top:4px">{rows}문장 · 총 {jobs}건 자동 번역 예정 '
        "(문장당 수십 초~수 분 걸릴 수 있습니다)</div></div>"
    )


def render_batch_summary(done: int, failed: int, total: int) -> str:
    percent = int(100 * (done + failed) / total) if total else 0
    fail = f" · <span style=\"color:var(--lq-bad)\">실패 {failed}</span>" if failed else ""
    return (
        '<div class="lq-card"><div style="font-weight:700;margin-bottom:6px">일괄 번역 진행 '
        f"{done + failed}/{total}{fail}</div>"
        f'<div style="height:8px;background:var(--lq-line);border-radius:6px;overflow:hidden">'
        f'<div style="width:{percent}%;height:100%;background:var(--lq-brand)"></div></div></div>'
    )


def render_batch_error(label: str, source: str, message: str) -> str:
    return (
        '<div class="lq-card" style="border-color:var(--lq-bad)">'
        f'<div class="lq-head"><span class="lq-country">{escape(label)}</span>'
        '<span class="lq-pill st-bad">✕ 실행 실패</span></div>'
        f'<div class="lq-text">{escape(source)}</div>'
        f'<div class="lq-text" style="color:var(--lq-bad);font-size:.85rem;margin-top:6px">{escape(message)}</div></div>'
    )
