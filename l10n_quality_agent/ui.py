"""검증된 핵심 Workflow 위에 얇게 얹은 Gradio UI.

모든 국가가 하나의 흐름을 탄다. TM/용어집/DNE는 Wikivoyage KO->EN 자료라
목표 언어가 English일 때만 적용되고, 다른 언어는 건너뛴다. 수정은 고정
우선순위 루프 대신 Agent(QualityWorkflow.run_via_agent)가 처음부터 맡는다.
"""

from __future__ import annotations

import csv
from queue import Empty, Queue
from threading import Thread
from time import monotonic
from pathlib import Path
import subprocess

import gradio as gr
import pandas as pd

from .agent import OpenAIAgentMock, QwenAgent
from .config import COUNTRY_LANGUAGE, FLORES_PROCESSED_DIR
from .dne import DoNotEditList, default_dne_path
from .openai_agent import OpenAIAgent, is_openai_configured, openai_user_revise
from .presentation import format_record
from .resources import apply_resources
from .results_csv import FIELDS, RESULTS_CSV, SOURCE_CSV, save_result
from .schemas import AgentStatus, TranslationRequest
from .terminology import Terminology, default_terminology_path
from .tm import TranslationMemory, default_tm_path
from .workflow import QualityWorkflow

COUNTRIES = list(COUNTRY_LANGUAGE)
SAMPLE_SENTENCES_FILE = FLORES_PROCESSED_DIR / "evaluation_30.csv"


# 리소스 파일이 없어도 앱은 실행되도록 선택적으로 읽는다.
def _tm() -> TranslationMemory | None:
    path = default_tm_path()
    return TranslationMemory.from_json_file(path) if path.exists() else None


workflow = QualityWorkflow(tm=_tm())
agent = QwenAgent(workflow.chains)


def _run_with_progress(call, progress):
    result = {}
    errors = []

    def worker():
        try:
            result["record"] = call(progress.put)
        except Exception as exc:  # 조용히 묻지 않고 UI에 그대로 보여준다
            errors.append(exc)

    thread = Thread(target=worker, daemon=True)
    thread.start()
    started_at = monotonic()
    last_heartbeat = -1
    while thread.is_alive() or not progress.empty():
        try:
            yield "step", progress.get(timeout=0.5)
        except Empty:
            elapsed = int(monotonic() - started_at)
            if thread.is_alive() and elapsed != last_heartbeat:
                last_heartbeat = elapsed
                yield "heartbeat", f"⏳ 모델 응답 대기 중 · {elapsed}초 경과"
    if errors:
        raise errors[0]
    return result["record"]


def _sample_sentence_choices() -> list[str]:
    if not SAMPLE_SENTENCES_FILE.exists():
        return []
    df = pd.read_csv(SAMPLE_SENTENCES_FILE)
    return [f"{row['id']}: {row['한국어']}" for _, row in df.iterrows()]


def load_sample_sentence(choice: str):
    if not choice:
        return gr.update()
    return gr.update(value=choice.split(": ", 1)[1] if ": " in choice else choice)


def _terminology() -> Terminology | None:
    path = default_terminology_path()
    return Terminology.from_json_file(path) if path.exists() else None


def _dne() -> DoNotEditList | None:
    path = default_dne_path()
    return DoNotEditList.from_json_file(path) if path.exists() else None


def _readable_step(message: str) -> str:
    """길게 이어진 조사 로그에 제목과 문단 구분을 붙여준다."""
    if message.startswith("[Agent] [조사] "):
        body = message.removeprefix("[Agent] [조사] ")
        reason, separator, outcome = body.partition(" -> ")
        return "Agent 조사\n" + reason + ("\n\n결과\n" + outcome if separator else "")
    if message.startswith("[Agent] [조사 결론] "):
        body = message.removeprefix("[Agent] [조사 결론] ")
        if "MQM 재평가에서 추가 오류를 찾지 못함" in body and "결정적 검증" in body:
            return "Agent 조사 결론\nMQM 추가 오류 없음. 자동 안전 검증 경고가 남아 승인 대기 중."
        return "Agent 조사 결론\n" + body
    if "전략 선택: " in message and " - " in message:
        choice, reason = message.split(" - ", 1)
        if choice.startswith("[Agent ") and "/" in choice:
            number = choice.split("[Agent ", 1)[1].split("/", 1)[0]
            limit = choice.split("/", 1)[1].split("]", 1)[0]
            choice = choice.replace(f"[Agent {number}/{limit}]", f"[Agent 판단 {number}회차 · 최대 {limit}회]")
        return choice + "\n사유: " + reason
    if ": " in message and len(message) > 100:
        heading, body = message.split(": ", 1)
        return heading + "\n" + body
    return message


def choose_results_file(current_path: str) -> str:
    """최종 승인을 누르면 저장할 기존 CSV 파일을 고르게 한다."""
    script = 'POSIX path of (choose file with prompt "승인 결과를 추가할 기존 CSV 파일을 선택하세요")'
    completed = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if completed.returncode:
        raise gr.Error("파일 선택이 취소되었습니다. 최종 승인은 적용하지 않았습니다.")
    chosen = completed.stdout.strip()
    if not chosen.lower().endswith(".csv") or not Path(chosen).is_file():
        raise gr.Error("기존 CSV 파일을 선택하세요.")
    if Path(chosen).resolve() == SOURCE_CSV.resolve():
        raise gr.Error("원본 평가 CSV에는 저장할 수 없습니다. 별도 결과 파일을 선택하세요.")
    with Path(chosen).open(encoding="utf-8-sig", newline="") as handle:
        if not set(FIELDS).issubset(csv.DictReader(handle).fieldnames or []):
            raise gr.Error("번역 결과 열이 있는 기존 CSV 파일을 선택하세요.")
    return chosen


def _save_result(record, results_path: str) -> str:
    # 사용자가 지정한 별도 결과 파일만 갱신한다. 원본 평가 CSV는 보호한다.
    destination = Path(results_path).expanduser()
    if destination.suffix.lower() != ".csv":
        raise gr.Error("결과 파일은 .csv 확장자를 사용하세요.")
    if destination.resolve() == SOURCE_CSV.resolve():
        raise gr.Error("원본 평가 CSV에는 저장할 수 없습니다. 별도 결과 파일을 선택하세요.")
    save_result(record, results_csv=destination)
    return f"저장했습니다: {destination}"


def load_results_view(results_path: str):
    """저장된 CSV를 화면에 보여주고 다운로드용 파일도 함께 반환한다."""
    destination = Path(results_path).expanduser().resolve()
    if not destination.is_file():
        return pd.DataFrame(columns=["id", "한국어", "목표국가", "번역결과", "상태"]), None, "저장된 결과가 없습니다."
    frame = pd.read_csv(destination, dtype=str, keep_default_na=False)
    preview = frame[["id", "한국어", "목표국가", "번역결과", "상태"]]
    return preview, str(destination), f"저장된 결과: {len(frame)}행 · {destination}"


def save_selected_result(run_map, country, results_path):
    """지금 선택된 HITL 실행 건을 수동으로 저장한다."""
    run_id = (run_map or {}).get(country)
    if not run_id:
        return "저장할 실행 국가를 먼저 선택하세요.", *load_results_view(results_path)
    record = workflow.store.load(run_id)
    message = _save_result(record, results_path)
    return message, *load_results_view(results_path)


def run_translation(source, countries, terms, instruction, use_openai, results_path=str(RESULTS_CSV)):
    selected = countries if isinstance(countries, list) else [countries]
    selected = [country for country in selected if country]
    if not selected:
        raise gr.Error("목표 국가를 하나 이상 선택하세요.")
    if not source or not source.strip():
        raise gr.Error("한국어 원문을 입력하세요.")

    terminology = _terminology()
    dne = _dne()

    multi = len(selected) > 1  # 국가가 여러 개일 때만 [국가] 접두사를 붙인다

    run_map = {}
    transcript = []
    # 국가별로 독립 실행해 한 국가의 실패가 다른 국가 결과를 덮지 않게 한다.
    for country_index, country in enumerate(selected, 1):

        def tag(msg: str, _country=country) -> str:
            return f"[{_country}] {msg}" if multi else msg

        country_steps = [f"국가 {country_index}/{len(selected)}: {country}"] if multi else []
        target_language = COUNTRY_LANGUAGE.get(country, country)
        request = TranslationRequest(
            source=source,
            target_language=target_language,
            target_country=country,
            protected_terms=[term.strip() for term in terms.split(",") if term.strip()],
            additional_instruction=instruction,
        )
        if target_language == "English":
            # TM/용어집/DNE는 Wikivoyage KO->EN 자료라 다른 언어엔 적용하지 않는다.
            request = apply_resources(request, terminology, dne)
            if request.protected_terms:
                country_steps.append(tag(f"적용된 용어집/DNE: {request.protected_terms}"))
            if request.additional_instruction != instruction:
                country_steps.append(tag(f"적용된 용어 지시: {request.additional_instruction}"))

        progress = Queue()
        runner = _run_with_progress(
            lambda callback, req=request: workflow.run_via_agent(
                req, agent, progress_callback=callback
            ),
            progress,
        )
        while True:
            try:
                message_type, message = next(runner)
                if message_type == "step":
                    country_steps.append(tag(_readable_step(message)))
                    heartbeat = []
                else:
                    heartbeat = [tag(message)]
                summary = (
                    f"전체 진행: {country_index - 1}/{len(selected)}개 완료 · "
                    f"현재 {country} 처리 중"
                )
                live = "\n\n".join(
                    [summary] + transcript + ["\n\n".join(country_steps + heartbeat)]
                )
                yield live, run_map, gr.update(), gr.update()
            except StopIteration as finished:
                record = finished.value
                break

        if record.status == AgentStatus.HUMAN_REVIEW_REQUIRED and use_openai:
            escalation = OpenAIAgent(workflow.chains) if is_openai_configured() else OpenAIAgentMock()
            openai_tag = "실제 실행" if is_openai_configured() else "Mock, 키 없음"
            country_steps.append(tag(f"--- Qwen Agent도 실패 → OpenAI Agent 개입 ({openai_tag}) ---"))
            record = escalation.run(record, progress_callback=lambda msg: country_steps.append(tag(msg)))
            workflow.store.save(record)

        # 위 진행 로그에 전체 기록이 이미 있으니 여기선 요약 한 줄이면 충분하다.
        saved_message = _save_result(record, results_path)
        country_steps.append(tag(f"최종: {record.status.value}\nrun_id={record.run_id}\n\n{record.current_version.translation}"))
        country_steps.append(tag(saved_message))
        run_map[country] = record.run_id
        transcript.append(
            f"## {country} 완료 ({country_index}/{len(selected)})\n\n" + "\n\n".join(country_steps)
        )
        versions = [str(version.version) for version in record.versions]
        yield (
            "\n\n".join(
                [f"전체 진행: {country_index}/{len(selected)}개 완료"] + transcript
            ),
            run_map,
            gr.update(choices=list(run_map), value=country),
            gr.update(choices=versions, value=versions[-1] if versions else None),
        )


def set_status(run_map, country, action, results_path=str(RESULTS_CSV)):
    run_id = (run_map or {}).get(country)
    if not run_id:
        return "승인/거부할 국가 실행을 선택하세요."
    try:
        record = workflow.approve(run_id) if action == "approve" else workflow.reject(run_id)
    except ValueError as exc:
        return f"{exc} (현재 상태: {workflow.store.load(run_id).status.value})"
    return format_record(record) + "\n\n" + _save_result(record, results_path)


def approve_with_file_choice(run_map, country, current_path):
    run_id = (run_map or {}).get(country)
    if not run_id:
        return "승인할 국가 실행을 선택하세요.", current_path
    record = workflow.store.load(run_id)
    if record.status != AgentStatus.AWAITING_HUMAN_APPROVAL:
        return f"승인 대기 상태의 실행만 승인할 수 있습니다. (현재 상태: {record.status.value})", current_path
    chosen = choose_results_file(current_path)
    return set_status(run_map, country, "approve", chosen), chosen


def refresh_versions(run_map, country):
    run_id = (run_map or {}).get(country)
    if not run_id:
        return gr.update(choices=[], value=None)
    record = workflow.store.load(run_id)
    versions = [str(item.version) for item in record.versions]
    return gr.update(choices=versions, value=versions[-1] if versions else None)


def direct_edit(run_map, country, new_translation, results_path=str(RESULTS_CSV)):
    run_id = (run_map or {}).get(country)
    if not run_id:
        return "직접 수정할 국가 실행을 먼저 선택하세요."
    if not new_translation or not new_translation.strip():
        return "수정할 번역문을 입력하세요."
    try:
        record = workflow.apply_human_edit(run_id, new_translation.strip())
    except Exception as exc:
        return f"직접 수정 처리 중 오류: {type(exc).__name__}: {exc}"
    return format_record(record) + "\n\n" + _save_result(record, results_path)


def ai_revise(run_map, country, version, instruction, model_choice, results_path=str(RESULTS_CSV)):
    run_id = (run_map or {}).get(country)
    if not run_id or not version:
        yield "실행 국가와 버전을 먼저 선택하세요.", run_map, gr.update()
        return

    use_openai = model_choice.startswith("OpenAI")
    if use_openai and not is_openai_configured():
        record = workflow.store.load(run_id)
        record = OpenAIAgentMock().run(record)
        workflow.store.save(record)
        saved_message = _save_result(record, results_path)
        yield (
            format_record(record)
            + "\n\n(OPENAI_API_KEY가 설정되지 않아 Mock으로 대체됨 - 실제 API 미호출, 추가 지시는 반영되지 않았습니다.)\n\n"
            + saved_message,
            run_map,
            gr.update(),
        )
        return

    reviser = (
        lambda request, translation: openai_user_revise(
            request, translation, request.additional_instruction
        )
        if use_openai else None
    )
    progress = Queue()
    runner = _run_with_progress(
        lambda callback: workflow.revise_from_version(
            run_id, int(version), instruction, progress_callback=callback, reviser=reviser
        ),
        progress,
    )
    lines = []
    while True:
        try:
            message_type, message = next(runner)
            prefix = "진행" if message_type == "step" else "대기"
            lines.append(f"[{country}] {prefix}: {message}")
            yield "\n".join(lines), run_map, gr.update()
        except StopIteration as finished:
            record = finished.value
            break
    updated_map = dict(run_map)
    updated_map[country] = record.run_id
    saved_message = _save_result(record, results_path)
    versions = [str(item.version) for item in record.versions]
    yield (
        format_record(record) + "\n\n" + saved_message,
        updated_map,
        gr.update(choices=versions, value=versions[-1] if versions else None),
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="L10n Quality Agent") as app:
        gr.Markdown("# L10n Quality Agent")
        gr.Markdown(
            "번역 직후 고정 우선순위 규칙 대신 **Qwen Agent가 바로** MQM 결과를 보고 다음 전략을 결정합니다. "
            "목표 언어가 English인 국가는 Wikivoyage KO→EN 용어집/DNE/TM이 자동 적용됩니다."
        )
        run_map = gr.State({})

        with gr.Row():
            sample_choice = gr.Dropdown(
                _sample_sentence_choices(), label="예시 문장 불러오기 (선택 시 아래 원문에 채워짐)"
            )
        source = gr.Textbox(label="한국어 원문")
        countries = gr.Dropdown(
            COUNTRIES,
            value=[COUNTRIES[0]],
            multiselect=True,
            label="목표 국가(복수 선택 가능)",
        )
        terms = gr.Textbox(label="보호 용어(쉼표 구분)")
        instruction = gr.Textbox(label="추가 지시")
        openai_tag = "실제 실행" if is_openai_configured() else "Mock, 키 없음"
        use_openai = gr.Checkbox(
            value=False, label=f"Qwen Agent도 실패하면 OpenAI Agent 개입 ({openai_tag})"
        )
        results_path = gr.Textbox(
            value=str(RESULTS_CSV), label="결과 저장 파일", interactive=False
        )
        run_button = gr.Button("번역 실행")
        output = gr.Textbox(label="실행 과정 · TM/용어집/DNE · MQM · 수정 이력 · 최종 상태", lines=22)

        gr.Markdown("### 결과 검토 및 HITL")
        result_country = gr.Dropdown(label="결과 검토 대상 국가")
        version = gr.Dropdown(label="이전 번역 버전")

        with gr.Group():
            gr.Markdown("**A. 직접 수정**")
            edit_box = gr.Textbox(label="번역문을 직접 편집")
            edit_button = gr.Button("직접 수정 저장")

        with gr.Group():
            gr.Markdown("**B. AI에게 추가 지시**")
            revision_instruction = gr.Textbox(label="선택 버전에 대한 추가 수정 지시")
            model_choice = gr.Radio(
                ["Qwen (로컬, 실제 실행)", f"OpenAI ({openai_tag})"],
                value="Qwen (로컬, 실제 실행)",
                label="모델 선택",
            )
            ai_revise_button = gr.Button("AI 재수정 실행")

        with gr.Row():
            approve = gr.Button("최종 승인")
            reject = gr.Button("거부")

        with gr.Accordion("저장된 결과 CSV", open=True):
            gr.Markdown("번역·수정 결과는 자동 저장됩니다. 아래에서 현재 선택한 결과를 다시 저장하거나 CSV를 내려받을 수 있습니다.")
            save_current = gr.Button("현재 선택 결과 CSV에 저장")
            refresh_results = gr.Button("저장된 CSV 새로고침")
            results_message = gr.Textbox(label="저장 상태", interactive=False)
            results_summary = gr.Textbox(
                value=load_results_view(str(RESULTS_CSV))[2],
                label="CSV 행 수와 저장 위치",
                interactive=False,
            )
            results_preview = gr.Dataframe(
                value=load_results_view(str(RESULTS_CSV))[0],
                label="저장된 결과 미리보기",
                interactive=False,
                wrap=True,
            )
            results_file = gr.File(
                value=load_results_view(str(RESULTS_CSV))[1],
                label="결과 CSV 열기·다운로드",
                interactive=False,
            )

        sample_choice.change(load_sample_sentence, [sample_choice], [source])
        run_button.click(
            run_translation,
            [source, countries, terms, instruction, use_openai, results_path],
            [output, run_map, result_country, version],
        )
        result_country.change(refresh_versions, [run_map, result_country], version)
        edit_button.click(
            direct_edit, [run_map, result_country, edit_box, results_path], output
        )
        ai_revise_button.click(
            ai_revise,
            [run_map, result_country, version, revision_instruction, model_choice, results_path],
            [output, run_map, version],
        )
        approve.click(
            approve_with_file_choice,
            [run_map, result_country, results_path],
            [output, results_path],
        )
        reject.click(
            lambda runs, country, path: set_status(runs, country, "reject", path),
            [run_map, result_country, results_path],
            output,
        )
        save_current.click(
            save_selected_result,
            [run_map, result_country, results_path],
            [results_message, results_preview, results_file, results_summary],
        )
        refresh_results.click(
            load_results_view,
            [results_path],
            [results_preview, results_file, results_summary],
        )
    return app


if __name__ == "__main__":
    build_app().launch()
