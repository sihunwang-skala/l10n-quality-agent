#!/usr/bin/env python3
"""Build site/index.html (KO default, EN toggle) in the same case-study format
as the health-agent portfolio page: left sidebar TOC, hero with metrics and a
switching screenshot frame, pinned scroll scenes, charts, product gallery.

CSS and scroll/i18n scripts live in template/ (reused as-is); all content is below.
Run:  python3 build.py
"""
import html
from pathlib import Path

HERE = Path(__file__).parent
GITHUB = "https://github.com/sihunwang-skala/l10n-quality-agent"


def en(s):
    return html.escape(s, quote=True)


def T(tag, ko, e, cls="", extra=""):
    """element with KO content and an EN swap in data-en"""
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-en="{en(e)}"{(" " + extra) if extra else ""}>{ko}</{tag}>'


# ---------------------------------------------------------------- sidebar
NAV = [
    ("context", "01 Context", "01 배경"),
    ("system-problem", "02 System Problem", "02 시스템 문제"),
    ("define", "03 Define", "03 정의"),
    ("decision", "04 Decision", "04 선택"),
    ("build", "05 Build", "05 구현"),
    ("approach", "06 Approach", "06 접근"),
    ("architecture", "07 Architecture", "07 구조"),
    ("evaluation", "08 Evaluation", "08 평가"),
    ("product", "09 Product", "09 화면"),
    ("safety", "10 Safety", "10 안전"),
    ("more", "11 More", "11 기타"),
]
side = (
    '<aside class="side"><a class="logo" href="#top">Sihun Wang</a>'
    '<div class="tree"><div class="t0">Work</div><div class="t1">Projects</div>'
    '<a class="t2 on" href="#top">L10n Quality Agent</a>'
    + "".join(f'<a class="t3" href="#{i}" data-en="{en(e)}">{k}</a>' for i, e, k in NAV)
    + '</div><div class="side-b"><button id="lang" class="tb" type="button" aria-label="Switch language" title="English / 한국어">EN</button>'
    '<button id="theme" class="tb" type="button" aria-label="Toggle dark mode" title="Dark mode">&#9790;</button>'
    '<div class="cp">&copy; 2026 Sihun Wang</div></div></aside>'
    '<div class="topbar"><a class="logo" href="#top">Sihun Wang</a><span><button id="lang2" class="tb" type="button">EN</button>'
    '<button id="theme2" class="tb" type="button">&#9790;</button></span></div>'
)

# ---------------------------------------------------------------- hero
SHOTS = [
    ("ui-hero.png", "서비스 화면", "Service screen"),
    ("ui-mode-poc.png", "입력 방식 3가지", "Three input modes"),
    ("ui-run.png", "실행 결과", "Run result"),
    ("ui-review.png", "검토·승인", "Review & approval"),
]
imgs = ""
for k, (f, ko, e) in enumerate(SHOTS):
    on = " on" if k == 0 else ""
    imgs += f'<img class="pi ko{on}" data-k="{k}" src="img/{f}" alt="{ko}"><img class="pi en{on}" data-k="{k}" src="img/{f}" alt="{e}">'
tabs = "".join(
    f'<button type="button" class="{"on" if k == 0 else ""}" data-i="{k}" data-en="{en(e)}">{ko}</button>'
    for k, (f, ko, e) in enumerate(SHOTS)
)


def hm(frm, to, suf, ko, e):
    return (
        f'<div class="hm"><div class="hf">{frm} <span class="ar">&rarr;</span></div>'
        f'<div class="hv"><span class="cnt" data-to="{to}" data-dec="0" data-suffix="{suf}">{to}{suf}</span></div>'
        f'{T("div", ko, e, "hl2")}</div>'
    )


hero = f"""<header class="hero" id="top"><div class="col hero-grid"><div class="hero-l">
<div class="tags rv"><span class="g1">Agentic</span><span class="g1">MQM</span><span class="g1">LangChain (LCEL)</span><span class="g1">Rollback</span><span class="g2">Localization</span><span class="g2">Translation QA</span><span class="g3">Deterministic Validation</span><span class="g3">Human-in-the-loop</span><span class="g3">Traceable Runs</span></div>
{T("h1", "L10n Quality Agent:<br>찾고, 고치고, 검증하고, 사람이 승인합니다", "L10n Quality Agent:<br>Find, Fix, Verify, and a Human Approves", "rv")}
{T("p", "&ldquo;고칠 때마다 전체를 다시 재서, 나빠지면 되돌립니다.&rdquo;", "&ldquo;Re-measure after every fix, and roll back if it gets worse.&rdquo;", "quote rv")}
{T("p", "AI 번역의 오류를 <b>MQM 기준</b>으로 찾고, 유형별 전문 도구로 고치고, 결정적 검사와 재평가로 확인한 뒤 <b>최종 승인은 사람</b>이 하는 번역 품질 개선 Agent입니다.", "A translation-quality agent that finds errors with the <b>MQM framework</b>, fixes them with category-specific tools, verifies each change with deterministic checks and re-evaluation, and leaves <b>final approval to a human</b>.", "lead rv")}
<div class="hmts rv">{T("div", "범용 &lsquo;고쳐줘&rsquo; 프롬프트에서 MQM 기반 Agent로", "From a generic &ldquo;fix it&rdquo; prompt to an MQM-based Agent", "hcap")}
<div class="hgrid">
{hm("범용 1개", 6, "", "전문 수정 체인 (MQM 카테고리별)", "Specialist fix chains (per MQM category)")}
{hm("상한 없음", 2, "회", "카테고리별 재시도 상한", "Retry cap per category")}
{hm("이력 없음", 7, "", "실행 상태 · 전 과정 JSON 기록", "Run states, every step recorded as JSON")}
{hm("자동 반영", 100, "%", "최종 승인은 사람", "Final approval by a human")}
</div></div>
<div class="meta rv">
<div><div class="k" data-en="USERS">대상</div>{T("div", "번역·현지화 품질을 다루는 사람, 번역 품질 자동화에 관심 있는 개발자", "People working on translation/localization quality; developers interested in automating it", "v")}</div>
<div><div class="k" data-en="DATA">데이터</div>{T("div", "공개 데이터셋 FLORES+ (TM·용어집·DNE는 직접 파생)", "Public FLORES+ dataset (TM, terminology and DNE derived by me)", "v")}</div>
<div><div class="k" data-en="EVALUATION">평가</div>{T("div", "FLORES+ dev 4개 언어 × 3문장(chrF), Wikivoyage KO→EN 5문장", "FLORES+ dev, 4 languages × 3 sentences (chrF); Wikivoyage KO→EN, 5 sentences", "v")}</div>
<div><div class="k" data-en="STACK">구성</div>{T("div", "LangChain (LCEL), Ollama · Qwen3.5 4B, OpenAI gpt-5-mini, Gradio", "LangChain (LCEL), Ollama + Qwen3.5 4B, OpenAI gpt-5-mini, Gradio", "v")}</div>
</div>
<a class="ext-link rv" href="{GITHUB}" target="_blank" rel="noopener" data-en="View on GitHub &#8599;">GitHub에서 보기 &#8599;</a></div>
<div class="ph-wrap rv" id="phw"><div class="ph-lb">UI</div><div class="ph win"><i class="notch"></i>{imgs}</div><div class="ph-tabs">{tabs}</div></div>
</div></header>"""

# ---------------------------------------------------------------- scenes
context = f"""<section class="cs scn " id="context" style="--scene-h:220vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "01 배경", "01 CONTEXT", "eb")}
{T("h2", "AI 번역은 빠르지만, 고치는 과정은 통제되지 않았습니다", "AI translation is fast, but the fixing step was uncontrolled")}
{T("p", "한국어 문장을 여러 언어로 번역한 뒤 품질을 사람이 일일이 확인하는 일은 느립니다. 그렇다고 AI에게 <b>고치기까지 통째로 맡기면</b> 무엇이 바뀌었는지 알 수 없습니다.", "Checking every translated sentence by hand is slow. But if you hand <b>the fixing step entirely to an AI</b>, you can no longer tell what changed.", "lead")}
</div><div class="stage-r"><div class="qv chatv"><div class="chat-h"><span class="av"></span><span class="chat-t">L10n Quality Agent</span></div>
<div class="msgs"><div class="um"><span class="tx" data-end="0.24" data-t-ko="이 회사는 San Jose 데이터센터에 약 2.5PB의 데이터를 저장합니다." data-t-en="This company stores about 2.5PB of data in its San Jose data center."></span><i class="caret"></i></div>
<div class="am"><div class="abub">{T("div", "이 번역에서 확인해야 할 오류 유형 (MQM)", "Error types to check in this translation (MQM)", "alabel")}
<div class="chips2">{"".join(f'<span class="chip" data-i="{i}" data-en="{en(e)}">{k}</span>' for i, (k, e) in enumerate([("정확성", "Accuracy"), ("용어", "Terminology"), ("철자", "Spelling"), ("문법", "Grammar"), ("문체", "Style"), ("유창성", "Fluency")]))}</div></div></div></div>
{T("div", "예시 문장은 작성자가 만든 가상의 문장입니다.", "The example sentence is fictional, written by the author.", "illus")}</div></div></div></div></div></section>"""


def card(ko_h, en_h, ko_p, en_p):
    return f'<div class="card">{T("h3", ko_h, en_h)}{T("p", ko_p, en_p)}</div>'


problem = f"""<section class="cs scn " id="system-problem" style="--scene-h:330vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "02 시스템 문제", "02 SYSTEM PROBLEM", "eb")}
{T("h2", "&lsquo;여기만 고쳐줘&rsquo;도, 고정된 순서 처리도 충분하지 않았습니다", "Neither &ldquo;just fix this&rdquo; nor a fixed order was enough")}
<ol class="ind"><li data-beat="0" data-en="Limits of a generic fix prompt">범용 수정 프롬프트의 한계</li><li data-beat="1" data-en="Limits of a fixed Workflow">고정 Workflow의 한계</li></ol></div>
<div class="stage-r"><div class="beats cardbeats">
<div class="beat" data-beat="0">{card("범용 수정 프롬프트의 한계", "Limits of a generic fix prompt", '오류 하나를 지적하면 <span class="hl">멀쩡한 부분까지 바꾸거나 새 오류를 만듭니다.</span> 숫자·단위·보호 용어가 틀어져도 모델은 &ldquo;다 고쳤다&rdquo;고 말하고, 수정 전후와 이유는 남지 않아 검수자가 확인할 수 없습니다.', 'Point out one error and it <span class="hl">rewrites parts that were fine or introduces new errors.</span> Even when numbers, units or protected terms drift, the model says &ldquo;all fixed&rdquo;, and no before/after or reasoning is kept for a reviewer.')}</div>
<div class="beat" data-beat="1">{card("고정 Workflow의 한계", "Limits of a fixed Workflow", 'accuracy &rsaquo; terminology &rsaquo; &hellip; 순으로 고정해 돌리면 재현은 쉽지만, 오류가 풀리지 않을 때 <span class="hl">다음에 무엇을 할지 판단하지 못합니다.</span> 실제 Baseline에서 4개 언어 12쌍이 모두 사람 검토로 넘어갔습니다.', 'Running accuracy &rsaquo; terminology &rsaquo; &hellip; in a fixed order is reproducible, but when an error will not resolve it <span class="hl">cannot decide what to do next.</span> In the actual baseline, all 12 pairs across 4 languages went to human review.')}</div>
</div></div></div></div></div></section>"""

define = f"""<section class="cs scn define" id="define" style="--scene-h:300vh"><div class="scene"><div class="stage"><div class="col">
{T("div", "03 정의", "03 DEFINE", "eb")}
<p class="hmw" data-fill="1" data-en="{en('<span class="ln">How might we fix one error at a time without touching the rest,</span><span class="ln">verify every change,</span><span class="ln"><em>roll back what makes things worse</em></span><span class="ln">and leave the final decision to a human?</span>')}"><span class="ln">다른 부분은 건드리지 않고 오류를 하나씩 고치고,</span><span class="ln">고칠 때마다 검증해서</span><span class="ln"><em>나빠진 변경은 되돌리며</em></span><span class="ln">최종 결정은 사람에게 맡기려면 어떻게 해야 할까?</span></p>
</div></div></div></section>"""

decision = f"""<section class="cs scn " id="decision" style="--scene-h:260vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "04 선택", "04 DECISION", "eb")}
{T("h2", "그래서 오류를 나눠 고치고, 검증하고, 사람이 승인하는 Agent를 선택했습니다", "So we chose an Agent that fixes by category, verifies, and has a human approve")}
{T("p", "LLM은 후보 번역을 만들 뿐이고, <b>채택·Rollback·상태 전환은 Python 코드</b>가 결정합니다. 실행 하나의 전체 이력은 <code>run_id</code> 단위 JSON으로 남습니다.", "The LLM only proposes candidate translations; <b>acceptance, rollback and state transitions are decided by Python code</b>. The full history of each run is saved as JSON per <code>run_id</code>.", "lead")}
</div><div class="stage-r"><div class="fan">
<div class="fc" style="--i:0;z-index:1"><img src="img/ui-run.png" alt="Run result"><span class="fl" data-en="Run result: history of accepts and rollbacks">실행 결과: 채택·Rollback 이력</span></div>
<div class="fc" style="--i:1;z-index:3"><img src="img/ui-review.png" alt="Review"><span class="fl" data-en="Review: diff and approval">검토: 변경점(diff)과 승인</span></div>
<div class="fc" style="--i:2;z-index:2"><img src="img/ui-mode-csv.png" alt="CSV batch"><span class="fl" data-en="CSV batch input">CSV 일괄 입력</span></div>
</div></div></div></div></div></section>"""

build = f"""<section class="cs scn " id="build" style="--scene-h:400vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "05 구현", "05 BUILD", "eb")}
{T("h2", "세 가지를 만들었습니다", "What I built")}
<ol class="ind"><li data-beat="0" data-en="MQM evaluation and specialist fixes">MQM 평가와 전문 수정</li><li data-beat="1" data-en="Deterministic validation and Rollback">결정적 검증과 Rollback</li><li data-beat="2" data-en="Agent, escalation and human approval">Agent, 에스컬레이션, 사람 승인</li></ol></div>
<div class="stage-r"><div class="beats cardbeats">
<div class="beat" data-beat="0"><div class="card"><h3><span class="hl">MQM 평가와 전문 수정</span></h3>{T("p", 'Pydantic 구조화 출력(<code>MQMResult</code>)으로 오류의 <span class="hl">카테고리·심각도·위치·수정 제안</span>을 받고, accuracy, terminology, spelling, grammar, style, fluency <b>6개 전용 수정 체인</b>이 각자 해당 오류만 고칩니다. 이미 맞는 표현은 <span class="hl">DNE</span>로 보호하고, TM·용어집을 프롬프트에 넣습니다.', 'Pydantic structured output (<code>MQMResult</code>) returns each error&rsquo;s <span class="hl">category, severity, span and suggested fix</span>, and <b>six dedicated fix chains</b> (accuracy, terminology, spelling, grammar, style, fluency) each repair only their own category. Already-correct phrases are protected by <span class="hl">DNE</span>; TM and terminology feed the prompts.')}</div></div>
<div class="beat" data-beat="1"><div class="card"><h3><span class="hl">결정적 검증과 Rollback</span></h3>{T("p", '숫자·단위·보호 용어·메타 주석 혼입은 LLM이 아니라 <span class="hl">Python 규칙</span>(<code>validation.py</code>)으로 검사합니다. 수정 후보는 전체를 <b>다시 MQM 평가</b>하고, 대상 오류가 줄지 않았거나 새 Critical 오류가 생기면 <span class="hl">후보를 버리고 이전 번역을 유지(Rollback)</span>합니다.', 'Numbers, units, protected terms and leaked meta-comments are checked by <span class="hl">Python rules</span> (<code>validation.py</code>), not the LLM. Every candidate is <b>fully re-evaluated with MQM</b>; if the target errors did not shrink or a new Critical error appears, <span class="hl">the candidate is discarded and the previous translation is kept (Rollback)</span>.')}</div></div>
<div class="beat" data-beat="2"><div class="card"><h3><span class="hl">Agent, 에스컬레이션, 사람 승인</span></h3>{T("p", '고정 우선순위로 풀리지 않으면 Qwen <span class="hl">Agent</span>가 남은 오류와 이력을 보고 다음 전략을 고르거나 포기하고, 그래도 안 되면 <b>OpenAI gpt-5-mini</b>가 한 번 더 시도합니다(키가 없으면 Mock). 마지막은 사람이 <b>직접 수정 / AI 재수정 / 승인 / 거부</b>를 선택합니다.', 'When fixed priority fails, the Qwen <span class="hl">Agent</span> reads the remaining errors and history to pick the next strategy or give up; if that fails, <b>OpenAI gpt-5-mini</b> gets one more attempt (a Mock when no key is set). Finally a human chooses <b>edit / AI re-revise / approve / reject</b>.')}</div></div>
</div></div></div></div></div></section>"""

# ---------------------------------------------------------------- approach (pipeline)
steps = [
    ("번역", "Translate", "TM 일치 시 신규 호출 생략", "Skipped on TM hit"),
    ("안전 검증", "Safety check", "숫자·단위·보호 용어", "Numbers, units, terms"),
    ("MQM 평가", "MQM evaluate", "오류 위치·심각도", "Error span and severity"),
    ("전문 수정", "Specialist fix", "카테고리별 최대 2회", "Max 2 per category"),
    ("재검증", "Re-verify", "채택 또는 Rollback", "Accept or Rollback"),
    ("Agent", "Agent", "다음 전략 판단", "Picks next strategy"),
    ("OpenAI", "OpenAI", "gpt-5-mini 한 번 더", "One more try"),
    ("사람 승인", "Human approval", "승인·거부·재수정", "Approve, reject, revise"),
]
pipe = "".join(
    f'<div class="s{" p" if i in (1, 4, 7) else ""}"><b data-en="{en(e)}">{k}</b><small data-en="{en(e2)}">{k2}</small></div>' + ('<span class="a">&rarr;</span>' if i < len(steps) - 1 else "")
    for i, (k, e, k2, e2) in enumerate(steps)
)
approach = f"""<section class="cs fig2s" id="approach"><div class="col">{T("div", "06 접근", "06 APPROACH", "eb")}
{T("h2", "고정 Workflow 위에 Agent와 에스컬레이션을 단계적으로 얹었습니다", "We layered the Agent and escalation on top of a fixed Workflow, step by step")}
<div class="fig"><div class="pipe">{pipe}</div>
{T("p", "<b>Figure 1.</b> 실행 흐름. 분홍색 단계는 <span class='hl'>LLM이 아니라 코드 또는 사람이 판단하는 지점</span>입니다.", "<b>Figure 1.</b> Run flow. The pink steps are <span class='hl'>decided by code or a human, not the LLM</span>.", "cap2")}</div></div></section>"""

# ---------------------------------------------------------------- architecture
team = (
    '<div class="team rv" aria-label="Workflow and its components"><span class="tnode sup" style="--i:0">QualityWorkflow</span><span class="tline"></span><div class="tagents">'
    + "".join(f'<span class="tn" style="--i:{i + 1}">{n}</span>' for i, n in enumerate(["Translate", "MQM Evaluate", "Revise ×6", "Validate", "Agent", "JsonRunStore"]))
    + "</div></div>"
)
architecture = f"""<section class="cs" id="architecture"><div class="col">{T("div", "07 구조", "07 ARCHITECTURE", "eb rv")}
{T("h2", '<span class="mk">LangChain 체인</span>으로 호출하고 <span class="mk">Python 코드</span>로 제어합니다', 'Model calls through <span class="mk">LangChain chains</span>, control in <span class="mk">Python code</span>', "rv")}
{team}
{T("p", "<code>workflow.py</code> 하나가 유일한 오케스트레이터이고, Ollama와 통신하는 곳은 <code>chains.py</code>뿐입니다. UI와 CLI는 같은 Workflow를 호출합니다. <b>RunRecord</b>는 모델명·temperature·seed·프롬프트 버전과 모든 번역 버전·시도 이력을 소유해, 설정이 바뀌어도 과거 실행을 그대로 확인할 수 있습니다.", "<code>workflow.py</code> is the only orchestrator, and <code>chains.py</code> is the only place that talks to Ollama. The UI and CLI call the same Workflow. <b>RunRecord</b> owns the model name, temperature, seed, prompt versions and every translation version and attempt, so past runs stay inspectable even after settings change.", "lead rv")}
<div class="rv"><div class="fig"><div class="imgbox"><img src="img/architecture.png" alt="LangChain chains and Python control architecture" style="display:block;width:100%;min-width:760px"></div>
{T("p", "<b>Figure 2.</b> 모델 호출은 <span class='hl'>LangChain 체인(LCEL)</span>, 실행 순서·채택 여부·검증은 <span class='hl'>Python 코드</span>.", "<b>Figure 2.</b> Model calls via <span class='hl'>LangChain chains (LCEL)</span>; order, acceptance and validation in <span class='hl'>Python code</span>.", "cap")}</div></div>
<div class="cards rv" style="margin-top:22px">
{card("번역 자원 3종", "Three translation resources", "<b>TM</b>(번역 메모리), <b>용어집</b>, <b>DNE</b>(이미 맞는 표현 보호)를 프롬프트와 검증에 주입합니다. TM에 일치해도 자동 승인하지 않습니다.", "<b>TM</b>, <b>terminology</b> and <b>DNE</b> (protect already-correct phrases) feed prompts and validation. A TM hit is never auto-approved.")}
{card("7가지 실행 상태", "Seven run states", "EVALUATING &rarr; REVISING &rarr; (HUMAN_REVIEW_REQUIRED | AWAITING_HUMAN_APPROVAL) &rarr; APPROVED / REJECTED. HUMAN_REVIEW_REQUIRED는 종단이 아니라 사람이 새 run을 분기하라는 신호입니다.", "EVALUATING &rarr; REVISING &rarr; (HUMAN_REVIEW_REQUIRED | AWAITING_HUMAN_APPROVAL) &rarr; APPROVED / REJECTED. HUMAN_REVIEW_REQUIRED is not terminal: it signals a human to branch a new run.")}
{card("재현성 스냅샷", "Reproducibility snapshot", "<code>parent_run_id</code>로 재수정 계보를 추적하고, 시도마다 수정 전후 MQM 결과를 비교용으로 저장합니다.", "Re-revision lineage is tracked via <code>parent_run_id</code>, and each attempt stores the before/after MQM results for comparison.")}
</div></div></section>"""

# ---------------------------------------------------------------- evaluation
CHRF = [("Japanese", 22.12, 22.12), ("Italian", 37.66, 37.66), ("French", 42.90, 37.26), ("German", 44.36, 45.96)]
SECS = [("Japanese", 2.58, 18.65), ("Italian", 1.29, 25.43), ("French", 1.34, 28.43), ("German", 1.35, 21.46)]


def rows(data, mx, unit, dec):
    out = ""
    for lang, a, b in data:
        out += f'<div class="row"><div class="name n0">{lang} · plain</div><div class="track"><div class="bar c0" style="--w:{a / mx * 100:.1f}%"></div><span class="bv">{a:.{dec}f}{unit}</span></div></div>'
        out += f'<div class="row"><div class="name n3">{lang} · agent</div><div class="track"><div class="bar final" style="--w:{b / mx * 100:.1f}%"></div><span class="bv">{b:.{dec}f}{unit}</span></div></div>'
    return out


WV = [
    ("889", "AWAITING", "0 → 0", "0", "1.7s", "67.3"),
    ("883", "AWAITING", "0 → 0", "0", "1.7s", "78.3"),
    ("806", "HUMAN_REVIEW", "1 → 1", "2", "27.2s", "33.9"),
    ("969", "HUMAN_REVIEW", "1 → 1", "2", "28.8s", "31.4"),
    ("938", "HUMAN_REVIEW", "3 → 1", "2", "28.6s", "31.7"),
]
wv_rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e_}</td><td>{f}</td></tr>" for a, b, c, d, e_, f in WV)

evaluation = f"""<section class="cs" id="evaluation"><div class="col">{T("div", "08 평가", "08 EVALUATION", "eb rv")}
{T("h2", "아직 &ldquo;더 좋아졌다&rdquo;고 말할 수 있는 단계는 아닙니다", "Not yet at &ldquo;it got better&rdquo;, and the numbers say so", "rv")}
{T("p", "FLORES+ dev 문장을 언어당 3개씩 뽑아(seed=42) <b>단순 번역(A)</b>과 <b>Agent 최종본(B)</b>을 chrF로 비교한 Baseline입니다. 표본이 작아 <span class='hl'>방향성만 보는 수치</span>입니다.", "A baseline on 3 FLORES+ dev sentences per language (seed=42), comparing <b>plain translation (A)</b> with the <b>agent&rsquo;s final output (B)</b> by chrF. The sample is small, so <span class='hl'>read these as direction only</span>.", "lead")}
<div class="grid6"><div class="rv chart key">{T("h3", "chrF: 단순 번역 vs Agent<span class='fin'>Baseline</span>", "chrF: plain vs Agent<span class='fin'>Baseline</span>")}{T("p", "언어별 평균(n=3). 높을수록 참조 번역과 가깝습니다.", "Mean per language (n=3). Higher is closer to the reference.", "q")}{rows(CHRF, 50, "", 1)}</div>
<div class="rv chart">{T("h3", "문장당 평균 소요 시간", "Mean time per sentence")}{T("p", "로컬 Ollama(Qwen3.5 4B) 기준, 초. 평가·재시도 호출이 늘어난 비용입니다.", "Local Ollama (Qwen3.5 4B), seconds. The cost of extra evaluate/retry calls.", "q")}{rows(SECS, 30, "s", 1)}</div></div>
{T("p", '<b>있는 그대로 읽으면:</b> 4개 언어 12쌍이 모두 <span class="mk">HUMAN_REVIEW_REQUIRED</span>로 끝났고, chrF는 일본어·이탈리아어 동일, 독일어 +1.6, 프랑스어 &minus;5.6이었습니다. 4B 로컬 모델에서 Agent는 점수를 일관되게 올리지 못했고 시간은 약 10~20배 늘었습니다. 지금 이 시스템의 가치는 점수 상승보다 <span class="mk">실패를 숨기지 않고 이유와 함께 사람에게 넘기는 것</span>입니다.', '<b>Read honestly:</b> all 12 pairs ended in <span class="mk">HUMAN_REVIEW_REQUIRED</span>; chrF was unchanged for Japanese and Italian, +1.6 for German and &minus;5.6 for French. With a 4B local model the Agent did not reliably raise scores and cost roughly 10&ndash;20&times; the time. Today the system&rsquo;s value is less a score gain than <span class="mk">not hiding failures: it hands them to a human with the reasons</span>.', "note2 rv")}
<details class="allres"><summary data-en="{en('Show the Wikivoyage KO→EN comparison<small>5 sentences with TM, terminology and DNE: status, MQM errors, attempts, time, chrF</small><span class="cta">Click to expand</span>')}">Wikivoyage KO→EN 비교 보기<small>TM·용어집·DNE 적용 5문장: 상태, MQM 오류, 시도, 시간, chrF</small><span class="cta">눌러서 펼치기</span></summary>
{T("p", "고정 Workflow 기준 첫 실행입니다. 5문장 중 2문장은 자동 검사를 통과해 사람 승인 대기, 3문장은 사람 검토로 넘어갔고 id 938만 오류가 3건에서 1건으로 줄었습니다.", "The first fixed-Workflow run. Two of five passed the automatic checks and await approval; three went to human review, and only id 938 reduced its errors (3 &rarr; 1).", "lead")}
<div class="rv"><table class="tbl"><tr><th>id</th><th data-en="Final status">최종 상태</th><th data-en="MQM errors">MQM 오류</th><th data-en="Attempts">시도</th><th data-en="Time">시간</th><th>chrF</th></tr>{wv_rows}</table></div></details>
<h3 class="grp rv" data-en="Problems found while experimenting">실험하면서 실제로 발견한 문제들</h3>
<div class="cards rv">
{card("결정적 검증기의 오탐", "False positive in the validator", "번역은 정확한데 &ldquo;2~3km&rdquo;가 &ldquo;2 to 3 kilometers&rdquo;와 대응되지 않아(풀어 쓴 단위) 숫자 검증에서 즉시 사람 검토로 갔습니다. 정규식 한계로 기록했습니다.", "The translation was right, but &ldquo;2~3km&rdquo; did not match &ldquo;2 to 3 kilometers&rdquo; (spelled-out unit), so the numeric check sent it straight to human review. Logged as a regex limitation.")}
{card("&ldquo;오류 없음 = 해결됨&rdquo; 버그", "A &ldquo;no errors = solved&rdquo; bug", "결정적 검증 실패로 MQM을 건너뛴 run의 <code>unresolved_errors</code>가 빈 리스트인데, Agent가 이를 해결로 보고 승인 대기로 올렸습니다. 진입 가드를 고치고 회귀 테스트를 추가했습니다.", "For runs that skipped MQM after a deterministic failure, <code>unresolved_errors</code> was empty and the Agent treated it as solved, queuing it for approval. Fixed the guard and added a regression test.")}
{card("근거 없는 전략 제안", "Ungrounded strategy proposals", "5문장 예비 실행에서 Agent가 추가로 해결한 건은 0건이었고, 감지되지 않은 카테고리(accuracy, terminology)를 골라 예산만 썼습니다. 다음 개선: <code>strategy</code>를 실제 남은 오류의 카테고리로 제한.", "In the 5-sentence preliminary run the Agent resolved nothing extra and spent budget on categories (accuracy, terminology) that were never detected. Next fix: constrain <code>strategy</code> to categories actually present.")}
{card("fluency 수정이 약하다는 신호", "A hint that fluency fixes are weak", "독일어 2문장은 chrF가 올랐지만 사람 검토로 끝났고, 한 문장은 다른 카테고리는 고쳤지만 fluency만 반복 실패했습니다. 카테고리별 accept/reject 집계가 다음 실험입니다.", "Both German sentences improved on chrF but ended in human review; one fixed other categories yet kept failing on fluency. Per-category accept/reject counts are the next experiment.")}
</div></div></section>"""

# ---------------------------------------------------------------- product gallery
PRODUCT = [
    ("ui-hero.png", "u", "Service", "서비스", "1. 서비스 화면", "1. Service screen", "왼쪽에서 입력 방식과 목표 국가를 고르면, 오른쪽에 번역 → MQM 평가 → 수정 → 사람 승인 단계가 진행 표시와 함께 나옵니다.", "Choose the input mode and target country on the left; the right side shows translate &rarr; MQM &rarr; revise &rarr; approval with progress."),
    ("ui-mode-poc.png", "u", "Input", "입력", "2. PoC 테스트", "2. PoC test", "내장 문장 30개 중 1개를 고릅니다(타이핑 없음). 설치 확인, 데모, 모델·프롬프트 변경 전후 비교에 씁니다.", "Pick one of 30 built-in sentences, no typing. For install checks, demos and before/after comparison of model or prompt changes."),
    ("ui-mode-direct.png", "u", "Input", "입력", "3. 직접 입력", "3. Direct input", "한국어 원문(필수)과 보호 용어·추가 지시(선택)를 넣어 사람이 한 문장씩 품질을 점검합니다.", "Enter the Korean source (required) plus protected terms and extra instructions (optional) to check one sentence at a time."),
    ("ui-mode-csv.png", "u", "Input", "입력", "4. CSV 업로드", "4. CSV upload", "<code>한국어</code> 열이 있는 CSV(최대 30문장)를 올리면 즉시 검증하고 &ldquo;몇 문장·몇 건이 실행될지&rdquo;를 미리 보여줍니다. 한 문장이 실패해도 나머지는 계속 진행합니다.", "Upload a CSV with a <code>한국어</code> column (max 30 sentences); it validates immediately and previews how many sentences/runs will execute. One failure does not stop the rest."),
    ("ui-run.png", "c", "Result", "결과", "5. 실행 결과", "5. Run result", "진행 단계, 상태 배지, 원문·번역 비교, 수정 이력(채택/Rollback), Agent 판단 근거를 국가별 카드로 보여줍니다.", "Progress steps, status badge, source vs. translation, revision history (accepted / rolled back) and Agent reasoning, as one card per country."),
    ("ui-review.png", "c", "Result", "결과", "6. 검토·승인", "6. Review & approval", "남은 MQM 오류와 이전 버전과의 변경점(diff)을 보고 직접 수정 / AI 재수정 / 승인 / 거부를 선택합니다. 프랑스어 예시는 숫자·단위 대응을 자동 확정할 수 없어 후보를 거부(Rollback)하고 사람에게 넘긴 의도된 동작입니다.", "See remaining MQM errors and a diff against the previous version, then edit / AI re-revise / approve / reject. The French example rejects the candidate (rollback) because number/unit correspondence cannot be confirmed automatically, which is intended."),
]
beats = ""
inds = ""
for i, (f, kind, tag_en, tag_ko, t_ko, t_en, d_ko, d_en) in enumerate(PRODUCT):
    key = " key" if i in (4, 5) else ""
    fig_en = f'<span class="tg {kind}">{tag_en}</span><b>{t_en}</b><br/>{d_en}'
    beats += (
        f'<div class="beat" data-beat="{i}"><figure class="tile{key}"><div class="shot"><img alt="{t_en}" src="img/{f}"/></div>'
        f'<figcaption data-en="{en(fig_en)}"><span class="tg {kind}">{tag_ko}</span><b>{t_ko}</b><br/>{d_ko}</figcaption></figure></div>'
    )
    inds += f'<li data-beat="{i}" data-en="{en(t_en)}">{t_ko}</li>'
product = f"""<section class="cs gal gal2" id="product"><div class="col stage-grid"><div class="stage-l">{T("div", "09 화면", "09 PRODUCT", "eb")}
{T("h2", "입력은 세 가지, 흐름은 같습니다", "Three ways in, one flow")}
{T("p", "어느 방식이든 이후 흐름(번역 &rarr; MQM 평가 &rarr; 수정 &rarr; 사람 승인)은 같습니다. 자동으로 하는 것은 수정까지이고, 승인은 항상 사람이 합니다. 화면 속 결과는 로컬 Qwen3.5 4B로 실제 실행해 저장된 기록을 다시 불러와 캡처했고, 문장은 모두 가상의 예시입니다.", "Whichever way you enter text, the rest is identical: translate &rarr; MQM &rarr; revise &rarr; human approval. Automation stops at revision; approval is always human. Results shown were captured by reloading real runs (local Qwen3.5 4B); all sentences are fictional.", "lead")}
<ol class="ind">{inds}</ol></div>
<div class="stage-r"><div class="beats cardbeats tilebeats">{beats}</div>
<div class="gnav"><button type="button" class="gb" data-d="-1" aria-label="Previous screen">&larr;</button><span class="gcount">1 / {len(PRODUCT)}</span><button type="button" class="gb" data-d="1" aria-label="Next screen">&rarr;</button></div></div></div></section>"""

# ---------------------------------------------------------------- safety / more
safety = f"""<section class="cs" id="safety"><div class="col">{T("div", "10 안전", "10 SAFETY", "eb rv")}{T("h2", "신뢰를 위한 장치", "Safeguards for trust", "rv")}
<div class="rv"><table class="tbl oneline">
<tr>{T("th", "결정적 검증", "Deterministic checks")}{T("td", "숫자·단위·보호 용어·메타 주석 혼입을 LLM이 아닌 Python 규칙으로 검사합니다.", "Numbers, units, protected terms and leaked meta-comments are checked by Python rules, not the LLM.")}</tr>
<tr>{T("th", "Rollback", "Rollback")}{T("td", "대상 오류가 줄지 않았거나 새 Critical 오류가 생기면 후보를 버리고 이전 번역을 유지합니다.", "If target errors did not shrink or a new Critical error appears, the candidate is discarded.")}</tr>
<tr>{T("th", "사람 승인", "Human approval")}{T("td", "Critical 오류, 반복 실패, 시도 상한 도달은 모두 사람 검토로 넘깁니다. 최종 승인은 항상 사람입니다.", "Critical errors, repeated failures and reaching the attempt cap all go to human review. Final approval is always human.")}</tr>
<tr>{T("th", "추적성", "Traceability")}{T("td", "수정 전후, 판단 근거, 채택/거부 사유를 <code>run_id</code>별 JSON으로 저장하고 결과는 CSV로 누적합니다.", "Before/after, reasoning and accept/reject reasons are stored per <code>run_id</code> as JSON; results accumulate in CSV.")}</tr>
<tr>{T("th", "검증", "Verification")}{T("td", "단위 테스트(pytest)로 검증기·워크플로우·Agent 가드를 점검하고, 발견한 버그는 회귀 테스트로 고정했습니다.", "pytest covers the validator, workflow and Agent guard; bugs found are pinned with regression tests.")}</tr>
</table></div></div></section>"""

more = f"""<section class="cs" id="more"><div class="col">{T("div", "11 기타", "11 MORE", "eb rv")}{T("h2", "기타", "More", "rv")}
<div class="rv"><table class="tbl oneline">
<tr>{T("th", "현재 한계", "Limits")}{T("td", "CSV는 순차 실행(최대 30문장). 비동기 큐·병렬·다중 사용자와 LangGraph Checkpointer는 미구현입니다. 4B 로컬 모델이라 판단 품질에 한계가 있고, 모델별 정량 비교·Golden Dataset 평가는 향후 과제입니다. RAG/Vector DB는 범위에서 제외했습니다.", "CSV runs sequentially (max 30). No async queue, parallelism, multi-user or LangGraph Checkpointer. A 4B local model limits judgment quality; per-model comparison and a golden dataset are future work. RAG/vector DB is out of scope.")}</tr>
<tr>{T("th", "다음 실험", "Next experiments")}{T("td", "Baseline 1(4개 언어 &times; 3문장)에서 카테고리별 accept/reject 비율을 집계하고, 나온 구체적 실패 사례를 근거로만 프롬프트를 바꿉니다.", "Aggregate per-category accept/reject rates in Baseline 1 (4 languages &times; 3 sentences), and change prompts only based on the concrete failures found.")}</tr>
<tr>{T("th", "데이터", "Data")}{T("td", "공개 데이터셋 FLORES+(CC BY-SA 4.0)만 사용했고, TM·용어집·DNE는 이를 바탕으로 새로 만들었습니다. 화면 속 예시 문장은 모두 가상입니다.", "Only the public FLORES+ dataset (CC BY-SA 4.0) is used; TM, terminology and DNE were newly derived from it. All example sentences shown are fictional.")}</tr>
<tr>{T("th", "독립성", "Independence")}{T("td", "작성자 개인이 개인 시간·장비로 만든 독립 프로젝트이며, 어떤 회사의 내부 코드·프롬프트·데이터·평가 결과도 포함하지 않습니다. 코드는 MIT 라이선스입니다.", "An independent personal project built on personal time and equipment; it contains no internal code, prompts, data or evaluation results of any company. Code is MIT-licensed.")}</tr>
<tr><th>Tech</th><td>Python 3.11, LangChain (LCEL), Pydantic, Ollama (Qwen3.5 4B), OpenAI gpt-5-mini</td></tr>
<tr><th>Tech (UI &amp; data)</th><td>Gradio, pandas, pytest, FLORES+</td></tr>
<tr>{T("th", "저장소", "Repository")}<td><a href="{GITHUB}" target="_blank" rel="noopener">github.com/sihunwang-skala/l10n-quality-agent</a></td></tr>
</table></div></div></section>"""

# ---------------------------------------------------------------- assemble
head = (HERE / "template/head.html").read_text(encoding="utf-8").replace("@@TITLE@@", "L10n Quality Agent")
override = """<style>
/* l10n additions on top of the shared case-study CSS */
.ph.win{width:100%;max-width:340px;aspect-ratio:4/4.7;border-width:8px;border-radius:18px}
.ph.win .notch{display:none}
.ph.win .pi{object-position:top left}
.tile .shot{display:block;width:100%;padding:0;cursor:default}
.tile .shot img{display:block;width:100%;max-height:62vh;object-fit:cover;object-position:top}
.tile .shot:hover{transform:none}
code{font:500 .88em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:1px 6px;border-radius:6px}
.card code,.tbl code{background:var(--bg)}
.pipe .s small{display:block}
.fig .pipe{padding:18px}
.fig .imgbox{overflow-x:auto;border:1px solid var(--line);border-radius:18px;padding:12px;background:#fff}
.tbl.oneline{width:100%;table-layout:fixed}.tbl.oneline th{width:170px}.tbl.oneline td,.tbl.oneline th{white-space:normal;overflow-wrap:anywhere}
</style>
"""
head = head.replace("</head>", override + "</head>") if "</head>" in head else head + override + "</head>"
scripts = (HERE / "template/scripts.html").read_text(encoding="utf-8")
page = (
    head + "<body>\n" + side + "<main>" + hero + "\n" + context + "\n" + problem + "\n" + define + "\n" + decision + "\n"
    + build + "\n" + approach + "\n" + architecture + "\n" + evaluation + "\n" + product + "\n" + safety + "\n" + more
    + "\n</main>\n" + scripts + "\n</body></html>\n"
)
(HERE / "index.html").write_text(page, encoding="utf-8")
print("wrote", HERE / "index.html", len(page), "bytes")
