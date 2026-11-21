#!/usr/bin/env python3
"""Build site/index.html (KO default, EN toggle) in the same case-study format
as the health-agent portfolio page: left sidebar TOC, hero with metrics and a
switching screenshot frame, pinned scroll scenes, charts, product gallery.

Story: the point of this project is NOT a score comparison. It is that the Agent
structure shows *where* a translation breaks (stage, MQM category, span, reason)
and *when a human must step in* (HITL triggers), for the languages the user picks.

CSS and scroll/i18n scripts live in template/ (reused as-is); all content is below.
Case files and distributions come from real saved runs (runs/*.json, git-ignored).
Run:  python3 build.py
"""
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
GITHUB = "https://github.com/sihunwang-skala/l10n-quality-agent"



# ---------------------------------------------------------------- keyword highlighter
# Key terms get a neon marker bar. Applied to text only (never inside <code> or tags).
KW_KO = ["사람 검토", "사람 승인", "결정적 검사", "전문 도구", "재평가", "Rollback", "롤백", "MQM", "HITL", "Agent", "보호 용어", "채택", "거부"]
KW_EN = ["human review", "human approval", "deterministic checks", "specialist tools", "re-evaluation", "Rollback", "MQM", "HITL", "Agent", "protected terms", "accepted", "rejected"]


def K(html_str, lang):
    kws = sorted(KW_KO if lang == "ko" else KW_EN, key=len, reverse=True)
    pat = re.compile("|".join(re.escape(k) for k in kws))
    parts = re.split(r"(<code>.*?</code>|<[^>]+>)", html_str)
    out = []
    for part in parts:
        if not part or part.startswith("<"):
            out.append(part)
        else:
            out.append(pat.sub(lambda m: f"<mark class=kw>{m.group(0)}</mark>", part))
    return "".join(out)


def en(s):
    return html.escape(s, quote=True)


def T(tag, ko, e, cls="", extra=""):
    """element with KO content and an EN swap in data-en"""
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c} data-en="{en(K(e, "en"))}"{(" " + extra) if extra else ""}>{K(ko, "ko")}</{tag}>'


def card(ko_h, en_h, ko_p, en_p):
    return f'<div class="card">{T("h3", ko_h, en_h)}{T("p", ko_p, en_p)}</div>'


# ---------------------------------------------------------------- sidebar
# Standalone by default. `python3 build.py <out.html> --portfolio` links back to the
# portfolio (../) the way the health-agent page does.
PORTFOLIO = "--portfolio" in sys.argv
LOGO_HREF = "../" if PORTFOLIO else "#top"
BACK_LINK = (
    '<a href="../#projects" style="display:block;font-size:12px;opacity:.6;margin:-6px 0 10px">&larr; Portfolio</a>' if PORTFOLIO else ""
)
NAV = [
    ("context", "01 Context", "01 배경"),
    ("system-problem", "02 System Problem", "02 시스템 문제"),
    ("define", "03 Define", "03 정의"),
    ("decision", "04 Decision", "04 선택"),
    ("build", "05 Build", "05 구현"),
    ("approach", "06 Where humans step in", "06 사람 개입 지점"),
    ("architecture", "07 Architecture", "07 구조"),
    ("cases", "08 Case files", "08 실행 사례"),
    ("product", "09 Product", "09 화면"),
    ("safety", "10 Safety", "10 안전"),
    ("more", "11 More", "11 기타"),
]
side = (
    f'<aside class="side"><a class="logo" href="{LOGO_HREF}">Sihun Wang</a>{BACK_LINK}'
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
    ("ui-run.png", "실행 결과", "Run result"),
    ("ui-review.png", "검토·승인", "Review & approval"),
    ("ui-mode-direct.png", "언어 선택·입력", "Language & input"),
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
<div class="tags rv"><span class="g1">Agentic</span><span class="g1">Multi-language</span><span class="g1">MQM</span><span class="g1">Specialist Tools</span><span class="g2">Localization</span><span class="g2">Translation QA</span><span class="g3">Human-in-the-loop</span><span class="g3">Deterministic Validation</span><span class="g3">Traceable Runs</span></div>
{T("h1", "L10n Quality Agent:<br>어디서 막혔는지 찾아, 사람이 볼 지점을 알려줍니다", "L10n Quality Agent:<br>It finds where translation breaks and tells you where a human should look", "rv")}
{T("p", "Agent 개발 · HITL 설계", "Agent Development · Human-in-the-loop Design", "role rv")}
{T("p", "&ldquo;번역은 Agent가 돕고, 판단이 필요한 지점은 이유와 함께 사람에게 넘깁니다.&rdquo;", "&ldquo;The Agent helps translate; anything that needs judgment goes to a human, with the reason.&rdquo;", "quote rv")}
{T("p", "내가 고른 언어로 번역하고, <b>문법·유창성 등 6개 전문 도구</b>를 Agent가 골라 고칩니다. 그리고 <b>어느 단계의 어떤 오류에서 막혔는지, 왜 사람이 봐야 하는지</b>를 기록과 함께 보여줍니다.", "It translates into the languages you choose, and the Agent picks among <b>six specialist tools</b> (grammar, fluency and more) to fix it. It then shows <b>at which step and on which error it got stuck, and why a human should look</b>, backed by a full record.", "lead rv")}
<div class="hmts rv">{T("div", "번역 한 건이 거치는 구조", "What one translation goes through", "hcap")}
<div class="hgrid">
{hm("목표 언어", 5, "", "일본어·이탈리아어·프랑스어·독일어·영어 중 선택", "Choose from Japanese, Italian, French, German, English")}
{hm("수정 도구", 6, "", "accuracy ~ fluency, 쓸 도구는 Agent가 선택", "accuracy to fluency; the Agent chooses which to use")}
{hm("개입 지점", 7, "", "사람에게 넘어가는 조건, 이유와 함께 표시", "Conditions that hand off to a human, shown with reasons")}
{hm("최종 승인", 100, "%", "항상 사람이 합니다", "Always done by a human")}
</div></div>
<div class="meta rv">
<div><div class="k" data-en="USERS">대상</div>{T("div", "번역·현지화 품질을 다루는 사람, 번역 품질 자동화에 관심 있는 개발자", "People working on translation/localization quality; developers interested in automating it", "v")}</div>
<div><div class="k" data-en="INPUT">입력</div>{T("div", "PoC 문장 선택, 직접 입력, CSV 일괄 (문장 &times; 국가 여러 건)", "Pick a PoC sentence, type your own, or CSV batch (many sentences &times; countries)", "v")}</div>
<div><div class="k" data-en="JUDGEMENT">판단</div>{T("div", "MQM 6개 영역 + 결정적 검사(숫자·단위·보호 용어) + Agent 전략", "Six MQM categories + deterministic checks (numbers, units, protected terms) + Agent strategy", "v")}</div>
<div><div class="k" data-en="STACK">구성</div>{T("div", "LangChain (LCEL), Ollama · Qwen3.5 4B, OpenAI gpt-5-mini, Gradio", "LangChain (LCEL), Ollama + Qwen3.5 4B, OpenAI gpt-5-mini, Gradio", "v")}</div>
</div>
<a class="ext-link rv" href="{GITHUB}" target="_blank" rel="noopener" data-en="View on GitHub &#8599;">GitHub에서 보기 &#8599;</a></div>
<div class="ph-wrap rv" id="phw"><div class="ph-lb">UI</div><div class="ph win"><i class="notch"></i>{imgs}</div><div class="ph-tabs">{tabs}</div></div>
</div></header>"""

# ---------------------------------------------------------------- scenes
LANGS = [("일본어", "Japanese"), ("이탈리아어", "Italian"), ("프랑스어", "French"), ("독일어", "German"), ("영어", "English")]
context = f"""<section class="cs scn " id="context" style="--scene-h:220vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "01 배경", "01 CONTEXT", "eb")}
{T("h2", "여러 언어로 번역하면, 어느 번역을 사람이 봐야 할까요?", "Translate into several languages: which ones need a human?")}
{T("p", "한국어 문장을 여러 언어로 번역하면 결과가 금세 늘어납니다. 전부 사람이 읽을 수는 없고, 전부 AI에게 맡길 수도 없습니다. <b>사람이 봐야 할 번역과 이유</b>를 먼저 알려주는 것이 필요했습니다.", "Translating one Korean sentence into several languages multiplies the output fast. A person cannot read all of it, and none of it can simply be left to an AI. We needed something that says <b>which translations a human should look at, and why</b>.", "lead")}
</div><div class="stage-r"><div class="qv chatv"><div class="chat-h"><span class="av"></span><span class="chat-t">L10n Quality Agent</span></div>
<div class="msgs"><div class="um"><span class="tx" data-end="0.24" data-t-ko="이 회사는 San Jose 데이터센터에 약 2.5PB의 데이터를 저장합니다." data-t-en="This company stores about 2.5PB of data in its San Jose data center."></span><i class="caret"></i></div>
<div class="am"><div class="abub">{T("div", "내가 고른 언어마다 번역하고 점검합니다", "Translate and check in every language I chose", "alabel")}
<div class="chips2">{"".join(f'<span class="chip" data-i="{i}" data-en="{en(e)}">{k}</span>' for i, (k, e) in enumerate(LANGS))}</div></div></div></div>
{T("div", "예시 문장은 작성자가 만든 가상의 문장입니다.", "The example sentence is fictional, written by the author.", "illus")}</div></div></div></div></div></section>"""

problem = f"""<section class="cs scn " id="system-problem" style="--scene-h:330vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "02 시스템 문제", "02 SYSTEM PROBLEM", "eb")}
{T("h2", "번역문만 봐서는 어디가 문제인지, 사람이 봐야 하는지 알 수 없습니다", "From the translation alone you cannot tell what is wrong or whether a human must look")}
<ol class="ind"><li data-beat="0" data-en="Where is the problem?">어디가 문제인지 알 수 없다</li><li data-beat="1" data-en="Who should decide?">누가 판단해야 하는지 모른다</li></ol></div>
<div class="stage-r"><div class="beats cardbeats">
<div class="beat" data-beat="0">{card("어디가 문제인지 알 수 없다", "Where is the problem?", '번역 결과만 받으면 <span class="hl">어느 부분이, 어떤 종류의 오류인지</span>(정확성인지 문체인지) 알 수 없습니다. 모델에게 &ldquo;고쳐줘&rdquo;라고 하면 멀쩡한 부분까지 바뀌고, 고친 이유는 남지 않습니다.', 'With only the output you cannot tell <span class="hl">which part is wrong, or what kind of error</span> (accuracy or style). Asking the model to &ldquo;fix it&rdquo; changes parts that were fine and leaves no reason behind.')}</div>
<div class="beat" data-beat="1">{card("누가 판단해야 하는지 모른다", "Who should decide?", '전부 자동으로 통과시키면 위험하고, 전부 사람이 보면 비용이 큽니다. <span class="hl">자동으로 해도 되는 것과 사람이 봐야 하는 것의 경계</span>가 있어야 하고, 그 경계가 이유와 함께 보여야 합니다.', 'Passing everything automatically is risky, and reviewing everything by hand is expensive. There must be <span class="hl">a boundary between what can be automated and what a human must see</span>, shown with reasons.')}</div>
</div></div></div></div></div></section>"""

# short lines (<= ~18 Korean chars each) so no line wraps; words light up as you scroll
define = f"""<section class="cs scn define" id="define" style="--scene-h:300vh"><div class="scene"><div class="stage"><div class="col">
{T("div", "03 정의", "03 DEFINE", "eb")}
<p class="hmw" data-fill="1" data-en="{en('<span class="ln">How might we translate into</span><span class="ln">the languages the user chooses,</span><span class="ln">fix each error with the right tool,</span><span class="ln"><em>show exactly where it got stuck</em></span><span class="ln">and why a human needs to step in?</span>')}"><span class="ln">고른 언어로 번역하고,</span><span class="ln">오류 종류마다 알맞은 도구로 고치며,</span><span class="ln"><em>어디서 막혔는지 짚어</em></span><span class="ln">사람이 봐야 하는 이유를 알려주려면</span><span class="ln">어떻게 해야 할까?</span></p>
</div></div></div></section>"""

decision = f"""<section class="cs scn " id="decision" style="--scene-h:260vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "04 선택", "04 DECISION", "eb")}
{T("h2", "그래서 전문 도구를 고르는 Agent와, 사람에게 넘기는 신호를 만들었습니다", "So we built an Agent that picks specialist tools, plus signals that hand off to a human")}
{T("p", "Agent(Planner)는 <b>다음에 쓸 도구만 고르고</b>, 후보를 채택할지는 Python 검사와 MQM 재평가가 정합니다. 막히면 어느 단계에서 왜 막혔는지를 <code>RunRecord</code>에 남겨 사람에게 보여줍니다.", "The Agent (planner) <b>only chooses the next tool</b>; whether to accept a candidate is decided by Python checks and MQM re-evaluation. When it gets stuck, where and why is written to the <code>RunRecord</code> and shown to a human.", "lead")}
</div><div class="stage-r"><div class="fan">
<div class="fc" style="--i:0;z-index:1"><img src="img/ui-run.png" alt="Run result"><span class="fl" data-en="Run result: stage, status and Agent reasoning">실행 결과: 단계, 상태, Agent 판단 근거</span></div>
<div class="fc" style="--i:1;z-index:3"><img src="img/ui-review.png" alt="Review"><span class="fl" data-en="Review: remaining errors and diff">검토: 남은 오류와 변경점(diff)</span></div>
<div class="fc" style="--i:2;z-index:2"><img src="img/ui-mode-csv.png" alt="CSV batch"><span class="fl" data-en="CSV: many sentences × many countries">CSV: 여러 문장 × 여러 국가</span></div>
</div></div></div></div></div></section>"""

build = f"""<section class="cs scn " id="build" style="--scene-h:400vh"><div class="scene"><div class="stage"><div class="col stage-grid"><div class="stage-l">
{T("div", "05 구현", "05 BUILD", "eb")}
{T("h2", "세 가지를 만들었습니다", "What I built")}
<ol class="ind"><li data-beat="0" data-en="Translate into the languages you choose">고른 언어로 번역</li><li data-beat="1" data-en="Specialist tools chosen by the Agent">Agent가 고르는 전문 도구</li><li data-beat="2" data-en="Signals that hand off to a human">사람에게 넘기는 신호</li></ol></div>
<div class="stage-r"><div class="beats cardbeats">
<div class="beat" data-beat="0"><div class="card"><h3><span class="hl">고른 언어로 번역</span></h3>{T("p", '목표 국가를 고르면 언어가 함께 정해집니다(미국·일본·이탈리아·프랑스·독일). CSV에서는 한 행에 <code>Japan|Italy</code>처럼 <span class="hl">여러 국가</span>를 넣어 문장마다 언어별로 따로 실행합니다. TM·용어집·DNE와 보호 용어가 번역 프롬프트와 검증에 들어갑니다.', 'Choosing a target country also sets the language (US, Japan, Italy, France, Germany). In a CSV a row can hold <span class="hl">several countries</span> such as <code>Japan|Italy</code>, and each language runs separately. TM, terminology, DNE and protected terms feed the translation prompt and the checks.')}</div></div>
<div class="beat" data-beat="1"><div class="card"><h3><span class="hl">Agent가 고르는 전문 도구</span></h3>{T("p", 'MQM 평가가 오류의 <span class="hl">영역·심각도·위치</span>를 알려주면, Agent가 그 가운데 다음에 쓸 <b>전문 도구</b> 하나를 고릅니다. 도구는 각자 한 영역만 고치도록 제한됩니다: <code>accuracy</code>, <code>terminology</code>, <code>spelling</code>, <code>grammar</code>, <code>style</code>, <code>fluency</code>. 고른 이유도 함께 기록합니다.', 'MQM evaluation reports each error&rsquo;s <span class="hl">category, severity and span</span>, and the Agent picks the next <b>specialist tool</b> from them. Each tool is restricted to one category: <code>accuracy</code>, <code>terminology</code>, <code>spelling</code>, <code>grammar</code>, <code>style</code>, <code>fluency</code>. The reason for the choice is recorded too.')}</div></div>
<div class="beat" data-beat="2"><div class="card"><h3><span class="hl">사람에게 넘기는 신호</span></h3>{T("p", '후보는 <span class="hl">Python 검사와 MQM 재평가</span>를 통과해야 채택되고, 아니면 Rollback합니다. 안전 검증 실패, Critical 오류, 반복 실패, Agent의 포기처럼 <b>7가지 지점</b>에서 자동 처리를 멈추고, <b>어느 단계에서 왜</b> 멈췄는지를 붙여 사람에게 넘깁니다.', 'A candidate is accepted only if it passes <span class="hl">Python checks and an MQM re-evaluation</span>; otherwise it is rolled back. At <b>seven points</b> (safety-check failure, Critical error, repeated failure, Agent giving up, and more) automation stops and the run is handed to a human with <b>the step and the reason</b>.')}</div></div>
</div></div></div></div></div></section>"""

# ---------------------------------------------------------------- 06 where humans step in (interactive map)
MAP = [
    (
        "통과", "Pass", "ok",
        "자동 검사 통과", "Automatic checks passed",
        "코드", "Code",
        "MQM 재평가에서 남은 오류가 없으면 <code>AWAITING_HUMAN_APPROVAL</code>. 이 경우에도 자동 승인하지 않습니다.",
        "When MQM re-evaluation leaves no errors the run becomes <code>AWAITING_HUMAN_APPROVAL</code>. It is still never auto-approved.",
        "오류 없음 · 수정 이력 · 최종 승인 버튼", "No errors · revision history · final approve button",
        "", "",
    ),
    (
        "안전 검증 실패", "Safety check failed", "",
        "결정적 검사에서 막힘", "Stopped by a deterministic check",
        "코드 (<code>validation.py</code>)", "Code (<code>validation.py</code>)",
        "보호 용어 누락, 숫자·단위 대응 확정 불가, 번역에 섞인 메타 주석. LLM이 아니라 규칙으로 판단해 <code>HUMAN_REVIEW_REQUIRED</code>로 보냅니다. Agent-first 경로에서는 Agent가 MQM으로 원인을 한 번 더 조사합니다.",
        "Missing protected term, number/unit correspondence that cannot be confirmed, or meta-commentary leaked into the translation. Rules, not the LLM, decide and send the run to <code>HUMAN_REVIEW_REQUIRED</code>. On the Agent-first path the Agent re-investigates the cause with MQM.",
        "원문과 번역의 숫자·단위 목록을 나란히 보여 줍니다", "Source and translation number/unit lists side by side",
        "프랑스어 &lsquo;2,5 PB&rsquo;처럼 소수점 표기가 달라 같은 값으로 확정하지 못한 경우 → 사례 B", "French &lsquo;2,5 PB&rsquo;: a different decimal format that could not be confirmed as the same value → Case B",
    ),
    (
        "Critical 오류", "Critical error", "",
        "심각한 오류는 자동 수정 안 함", "Critical errors are never auto-fixed",
        "코드 (<code>critical_count</code>)", "Code (<code>critical_count</code>)",
        "MQM 평가에 심각도 critical 오류가 하나라도 있으면 수정 도구를 부르지 않고 바로 사람 검토로 전환합니다.",
        "If MQM reports even one critical error, no tool is called and the run goes straight to human review.",
        "남은 오류 목록(영역·심각도·설명)", "Remaining error list (category, severity, explanation)",
        "", "",
    ),
    (
        "카테고리 2회 실패", "Two failures in a category", "",
        "같은 도구가 두 번 실패", "The same tool failed twice",
        "코드 (<code>MAX_ATTEMPTS_PER_CATEGORY=2</code>)", "Code (<code>MAX_ATTEMPTS_PER_CATEGORY=2</code>)",
        "후보가 검증을 못 넘거나, 대상 오류가 줄지 않거나, 새 Critical 오류가 생기면 거부(Rollback)합니다. 같은 영역에서 두 번 거부되면 사람에게 넘깁니다.",
        "A candidate is rejected (rollback) if it fails validation, does not reduce the target errors, or adds a new Critical error. Two rejections in one category hand the run to a human.",
        "수정 이력: 채택/거부와 거부 사유", "Revision history: accepted/rejected and the reasons",
        "일본어 &lsquo;fluency 오류가 감소하지 않음&rsquo; → 사례 A", "Japanese &lsquo;fluency errors did not decrease&rsquo; → Case A",
    ),
    (
        "전체 시도 12회", "12 attempts overall", "",
        "시도 총량 상한", "Overall attempt cap",
        "코드 (<code>MAX_TOTAL_ATTEMPTS=12</code>)", "Code (<code>MAX_TOTAL_ATTEMPTS=12</code>)",
        "영역별로는 한계에 안 닿아도 한 번의 실행에서 수정 시도가 12회가 되면 멈추고 사람에게 넘깁니다. 끝없이 돌지 않게 하는 안전장치입니다.",
        "Even if no single category hits its limit, a run stops after 12 revision attempts and goes to a human, so it can never loop forever.",
        "&ldquo;전체 수정 상한 12회 도달&rdquo; 사유", "The reason &ldquo;overall limit of 12 reached&rdquo;",
        "", "",
    ),
    (
        "Agent 포기", "Agent gives up", "",
        "Agent가 사람 몫이라고 판단", "The Agent decides it is a human call",
        "Agent (Planner)", "Agent (planner)",
        "Planner가 <code>human_review</code>를 고르거나, 전략 최대 2개를 써도 오류가 남으면 사람에게 넘깁니다. 고른 전략과 그 이유가 <code>agent_decisions</code>에 문장으로 남습니다.",
        "The planner picks <code>human_review</code>, or errors remain after at most two strategies, and the run goes to a human. The chosen strategies and their reasons are stored as sentences in <code>agent_decisions</code>.",
        "Agent 전략 선택과 근거 문장", "The Agent&rsquo;s strategy choices and reasoning",
        "&ldquo;엄밀한 오류라기보다 표현의 미세한 차이&rdquo; → 사례 C", "&ldquo;less an error than a subtle difference in expression&rdquo; → Case C",
    ),
    (
        "OpenAI도 미통과", "OpenAI also failed", "",
        "에스컬레이션 후에도 남음", "Still unresolved after escalation",
        "코드 + OpenAI <code>gpt-5-mini</code>", "Code + OpenAI <code>gpt-5-mini</code>",
        "Qwen Agent가 못 푼 건은 OpenAI가 한 번 더 시도합니다. 후보는 같은 가드레일과 MQM 재평가를 거치고, 통과하지 못하면 그대로 사람 검토입니다. 키가 없으면 Mock이라 상태를 바꾸지 않습니다.",
        "What the Qwen Agent could not solve gets one more attempt from OpenAI. Its candidate faces the same guardrails and MQM re-evaluation; if it fails, the run stays in human review. Without a key a Mock is used and nothing changes.",
        "OpenAI 후보와 거부 사유", "The OpenAI candidate and the rejection reason",
        "", "",
    ),
    (
        "실행 예외", "Run exception", "",
        "실행 자체가 실패", "The run itself failed",
        "코드 (<code>except</code>)", "Code (<code>except</code>)",
        "모델 호출 실패나 구조화 출력 검증 실패 같은 예외가 나면 숨기지 않고 사유를 <code>failure_reasons</code>에 적어 사람 검토로 돌립니다.",
        "On an exception such as a failed model call or invalid structured output, the reason is written to <code>failure_reasons</code> and the run goes to human review instead of being hidden.",
        "예외 종류와 메시지", "Exception type and message",
        "", "",
    ),
]
map_btns = ""
map_panels = ""
for i, (kl, ke, cls, hl_ko, hl_en, who_ko, who_en, how_ko, how_en, see_ko, see_en, ex_ko, ex_en) in enumerate(MAP):
    on = " on" if i == 0 else ""
    num = "✓" if i == 0 else str(i)
    map_btns += f'<button type="button" class="lq-n {cls}{on}" data-i="{i}" style="--k:{i}"><i>{num}</i><span data-en="{en(ke)}">{kl}</span></button>'
    ex = f'<div class="lq-r"><b data-en="Real example">실제 예시</b>{T("span", ex_ko, ex_en)}</div>' if ex_ko else ""
    map_panels += (
        f'<div class="lq-d{on}" data-i="{i}"><div class="lq-h">{T("h3", hl_ko, hl_en)}</div>'
        f'<div class="lq-r"><b data-en="Who decides">누가 판단</b>{T("span", who_ko, who_en)}</div>'
        f'<div class="lq-r"><b data-en="Condition">조건</b>{T("span", how_ko, how_en)}</div>'
        f'<div class="lq-r"><b data-en="What the human sees">사람이 보는 것</b>{T("span", see_ko, see_en)}</div>{ex}</div>'
    )

approach = f"""<section class="cs fig2s" id="approach"><div class="col">{T("div", "06 사람 개입 지점", "06 WHERE HUMANS STEP IN", "eb rv")}
{T("h2", "자동 처리가 <span class='mk'>어디서 멈추는지</span>, 이유와 함께 알려줍니다", "It tells you <span class='mk'>where automation stops</span>, with the reason", "rv")}
{T("p", "번역은 한 건마다 이 지점들을 지납니다. 멈춘 지점에 따라 사람이 봐야 할 내용이 달라지므로, 번호를 눌러 <b>누가 판단하고, 무엇을 사람에게 보여주는지</b> 확인해 보세요.", "Every translation passes these points. What a human must look at depends on where it stopped, so click a number to see <b>who decides and what the human is shown</b>.", "lead rv")}
<div class="lq rv"><div class="lq-map" id="lqmap">{map_btns}</div><div class="lq-panel">{map_panels}</div>
{T("p", "<b>Figure 1.</b> 코드 상수와 실제 실행 기록에서 정리한 <span class='hl'>사람 개입 지점 7가지와 정상 통과</span>.", "<b>Figure 1.</b> <span class='hl'>Seven human-handoff points plus the pass path</span>, taken from the code constants and real run records.", "cap2")}</div></div></section>"""

# ---------------------------------------------------------------- 07 architecture
team = (
    '<div class="team rv" aria-label="Workflow and its components"><span class="tnode sup" style="--i:0">QualityWorkflow</span><span class="tline"></span><div class="tagents">'
    + "".join(f'<span class="tn" style="--i:{i + 1}">{n}</span>' for i, n in enumerate(["Translate", "MQM Evaluate", "Planner (Agent)", "Tools ×6", "Validate", "RunRecord"]))
    + "</div></div>"
)
architecture = f"""<section class="cs" id="architecture"><div class="col">{T("div", "07 구조", "07 ARCHITECTURE", "eb rv")}
{T("h2", "<span class='mk'>Agent는 고르고</span>, <span class='mk'>코드가 정합니다</span>", "<span class='mk'>The Agent chooses</span>, <span class='mk'>code decides</span>", "rv")}
{team}
{T("p", "<code>agent.py</code>의 Planner는 도구 이름 하나와 이유만 돌려줍니다(Tool-calling Agent가 아니라 Planner Chain). 후보 번역을 채택할지는 <code>validation.py</code>와 MQM 재평가가 정하고, 모델과 통신하는 곳은 <code>chains.py</code>뿐입니다. 이 구조 덕분에 <b>무엇이 어디서 막혔는지</b>를 모두 필드로 남길 수 있습니다.", "The planner in <code>agent.py</code> returns just a tool name and a reason (a planner chain, not a tool-calling agent). Whether to accept a candidate is decided by <code>validation.py</code> and MQM re-evaluation, and <code>chains.py</code> is the only place that talks to the model. This is what lets every <b>stuck point</b> be stored as a field.", "lead rv")}
<div class="rv"><div class="fig"><div class="imgbox"><img src="img/architecture.png" alt="LangChain chains and Python control architecture" style="display:block;width:100%;min-width:760px"></div>
{T("p", "<b>Figure 2.</b> 모델 호출은 <span class='hl'>LangChain 체인(LCEL)</span>, 실행 순서·채택 여부·검증은 <span class='hl'>Python 코드</span>.", "<b>Figure 2.</b> Model calls via <span class='hl'>LangChain chains (LCEL)</span>; order, acceptance and validation in <span class='hl'>Python code</span>.", "cap")}</div></div>
<h3 class="grp rv" data-en="What every run records: where and why it got stuck">실행마다 남는 기록: 어디서, 왜 막혔는가</h3>
<div class="cards rv">
{card("<code>versions</code> · <code>attempts</code>", "<code>versions</code> · <code>attempts</code>", "채택된 번역 버전과, 채택·거부를 모두 포함한 시도 이력. 도구별로 수정 전후 MQM 결과와 거부 사유가 들어 있습니다.", "Accepted translation versions and every attempt, accepted or rejected, with before/after MQM results and rejection reasons per tool.")}
{card("<code>agent_decisions</code>", "<code>agent_decisions</code>", "Agent가 고른 전략과 이유, 호출하지 않고 건너뛴 도구까지 문장으로 남깁니다. 사람이 Agent의 판단을 되짚어 볼 수 있습니다.", "The strategies the Agent chose and why, even tools skipped without a call, stored as sentences so a human can retrace its reasoning.")}
{card("<code>unresolved_errors</code> · <code>failure_reasons</code>", "<code>unresolved_errors</code> · <code>failure_reasons</code>", "끝내 남은 MQM 오류(영역·심각도·위치)와, 안전 검증·상한·예외 같은 멈춘 사유. 사람이 가장 먼저 읽는 부분입니다.", "The MQM errors that remain (category, severity, span) and the reasons it stopped: safety check, caps, exceptions. The first thing a human reads.")}
{card("7가지 실행 상태", "Seven run states", "EVALUATING &rarr; REVISING &rarr; HUMAN_REVIEW_REQUIRED 또는 AWAITING_HUMAN_APPROVAL &rarr; APPROVED / REJECTED. HUMAN_REVIEW_REQUIRED는 종단이 아니라 사람이 새 run을 분기하라는 신호입니다.", "EVALUATING &rarr; REVISING &rarr; HUMAN_REVIEW_REQUIRED or AWAITING_HUMAN_APPROVAL &rarr; APPROVED / REJECTED. HUMAN_REVIEW_REQUIRED is not terminal: it signals a human to branch a new run.")}
</div></div></section>"""

# ---------------------------------------------------------------- 08 case files (real runs)
KIND = {
    "auto": ("자동", "Auto"),
    "check": ("결정적 검사", "Check"),
    "agent": ("Agent", "Agent"),
    "rb": ("Rollback", "Rollback"),
    "human": ("사람", "Human"),
}
CASES = [
    {
        "tab": ("A · 일본어", "A · Japanese"),
        "title": ("지명 표기는 고치고, 뉘앙스는 사람에게", "It fixed the place name and left a nuance for a human"),
        "sum": ("한국어 &lsquo;San Jose&rsquo;가 일본어에서 &lsquo;サンホセ&rsquo;로 옮겨졌습니다. spelling 도구가 이를 고쳤고, 남은 문체 문제는 도구가 해결하지 못해 사람 몫으로 남았습니다.", "&lsquo;San Jose&rsquo; came out as &lsquo;サンホセ&rsquo; in Japanese. The spelling tool fixed it; a remaining style issue the tool could not resolve was left for a human."),
        "steps": [
            ("auto", "초기 번역 (v1)", "Initial translation (v1)", "この会社は、米国カリフォルニア州<b>サンホセ</b>にあるデータセンターに約 2.5PB のデータを保存し&hellip;", "この会社は、米国カリフォルニア州<b>サンホセ</b>にあるデータセンターに約 2.5PB のデータを保存し&hellip;"),
            ("agent", "MQM 평가 → Agent가 spelling 도구 선택", "MQM evaluation → the Agent picks the spelling tool", "<b>spelling · minor</b> — &lsquo;サンホセ&rsquo;는 일본어 표기 &lsquo;サンノゼ&rsquo;와 다르다는 지적. Agent(전략 1/2)는 지역명 표기 오류라 먼저 고쳐야 한다고 판단하고 spelling 도구를 호출했습니다.", "<b>spelling · minor</b>: &lsquo;サンホセ&rsquo; differs from the Japanese form &lsquo;サンノゼ&rsquo;. The Agent (strategy 1/2) judged it a place-name error to fix first and called the spelling tool."),
            ("auto", "후보 채택 → v2", "Candidate accepted → v2", "サンホセ → <b>サンノゼ</b>. 재평가에서 spelling 오류가 사라져 채택했습니다.", "サンホセ → <b>サンノゼ</b>. The spelling error was gone after re-evaluation, so it was accepted."),
            ("rb", "fluency 도구 후보 거부 → Rollback", "Fluency tool candidate rejected → Rollback", "남은 오류 <b>fluency · minor</b>(&lsquo;매일 새벽&rsquo; 뉘앙스 누락)에 Agent(전략 2/2)가 fluency 도구를 호출했지만 &ldquo;fluency 오류가 감소하지 않음&rdquo;으로 거부되어 v2를 유지했습니다.", "For the remaining <b>fluency · minor</b> error (the &lsquo;early morning&rsquo; nuance missing) the Agent (strategy 2/2) called the fluency tool, but &ldquo;fluency errors did not decrease&rdquo;, so it was rejected and v2 kept."),
            ("human", "사람 검토 필요", "Human review required", "남은 오류: <b>fluency · minor</b>. &lsquo;새벽&rsquo;을 번역에 넣을지는 문체 판단이라, 시도 이력과 거부 사유가 함께 남은 채 사람에게 넘어갑니다.", "Remaining error: <b>fluency · minor</b>. Whether to include &lsquo;early morning&rsquo; is a style call, so it goes to a human with the attempt history and the rejection reason."),
        ],
    },
    {
        "tab": ("B · 프랑스어", "B · French"),
        "title": ("번역은 맞아 보여도, 숫자 표기를 확정하지 못해 사람에게", "It looks right, but the number format could not be confirmed"),
        "sum": ("프랑스어 &lsquo;2,5 PB&rsquo;를 결정적 검사가 원문 &lsquo;2.5PB&rsquo;와 같은 값으로 확정하지 못했습니다. 코드가 먼저 멈추고, Agent는 원인을 조사했습니다.", "The deterministic check could not confirm French &lsquo;2,5 PB&rsquo; as the same value as the source &lsquo;2.5PB&rsquo;. Code stopped first and the Agent investigated."),
        "steps": [
            ("auto", "초기 번역 (v1)", "Initial translation (v1)", "Cette entreprise stocke environ <b>2,5 PB</b> de données dans son centre de données situé à San Jose en Californie (États-Unis)&hellip;", "Cette entreprise stocke environ <b>2,5 PB</b> de données dans son centre de données situé à San Jose en Californie (États-Unis)&hellip;"),
            ("check", "결정적 검사: 숫자 대응 확정 불가", "Deterministic check: numbers cannot be confirmed", "원문 <code>['2.5','02','00']</code> ↔ 번역 <code>['2','5','02','00']</code>. 소수점 쉼표(2,5)를 같은 값으로 확정하지 못해 이 건을 사람 검토 대상으로 표시했습니다.", "Source <code>['2.5','02','00']</code> ↔ translation <code>['2','5','02','00']</code>. The check could not confirm the decimal comma (2,5) as the same value, so it flagged the run for human review."),
            ("agent", "Agent가 원인 조사 (MQM 재평가)", "The Agent investigates (MQM re-evaluation)", "MQM이 아직 돌지 않은 상태라 Agent가 직접 평가를 실행해 <b>accuracy · minor</b> 1건(California &lsquo;주&rsquo; 단위 표현이 약해짐)을 찾았습니다.", "MQM had not run yet, so the Agent ran it and found one <b>accuracy · minor</b> issue (the &lsquo;state&rsquo; level of California is weakened)."),
            ("agent", "전략 1/2: fluency 선택 → 호출 안 함", "Strategy 1/2: fluency → not called", "해당 영역에 미해결 오류가 없어 도구를 부르지 않고 건너뛰었습니다. Planner가 실제 오류에 근거하지 않고 고른 사례로, 이 사실도 그대로 기록됩니다.", "No unresolved error in that category, so the tool was skipped. A case of the planner choosing without grounding in an actual error, and that fact is recorded as is."),
            ("rb", "전략 2/2: accuracy 후보 거부 → Rollback", "Strategy 2/2: accuracy candidate rejected → Rollback", "후보가 현재 번역과 동일하고, 숫자 대응도 확정하지 못해 거부했습니다. v1을 유지합니다.", "The candidate was identical to the current translation and numbers still could not be confirmed, so it was rejected. v1 is kept."),
            ("human", "사람 검토 필요", "Human review required", "사람이 볼 것: <b>① 2,5 = 2.5 표기 차이인지</b>, <b>② California &lsquo;주&rsquo;를 더 살릴지</b>. 두 이유가 같은 화면에 함께 표시됩니다.", "What the human checks: <b>① whether 2,5 = 2.5 is just a format difference</b>, <b>② whether to preserve &lsquo;state&rsquo; for California</b>. Both reasons appear on the same screen."),
        ],
    },
    {
        "tab": ("C · 영어", "C · English"),
        "title": ("Agent가 &lsquo;고칠 문제가 아니다&rsquo;라고 사람에게 넘김", "The Agent decided it was not a fix and handed it over"),
        "sum": ("FLORES+(공개 데이터) 문장입니다. Agent가 수정 도구를 부르지 않고, 표현의 미세한 차이라는 이유와 함께 사람 판단으로 넘겼습니다.", "A FLORES+ (public data) sentence. The Agent did not call a fix tool and handed it to a human, with the reason that it was a subtle difference in expression."),
        "steps": [
            ("auto", "초기 번역 (v1)", "Initial translation (v1)", "&hellip;genuine imported models might cost more than <b>their country of origin</b>.", "&hellip;genuine imported models might cost more than <b>their country of origin</b>."),
            ("agent", "MQM 재평가", "MQM re-evaluation", "<b>fluency · minor</b> 1건: 원문 &lsquo;모국&rsquo;을 &lsquo;their country of origin&rsquo;으로 옮긴 부분.", "One <b>fluency · minor</b> issue: the source &lsquo;모국&rsquo; rendered as &lsquo;their country of origin&rsquo;."),
            ("agent", "전략 1/2: <code>human_review</code> 선택", "Strategy 1/2: <code>human_review</code>", "Planner는 &ldquo;엄밀한 오류라기보다는 표현의 미세한 차이&rdquo;라고 판단해 수정 도구를 호출하지 않았습니다.", "The planner judged it &ldquo;less an error than a subtle difference in expression&rdquo; and called no fix tool."),
            ("human", "사람 검토 필요", "Human review required", "남은 오류 <b>fluency · minor</b> 1건과 Agent의 판단 근거가 남아, 사람은 받아들일지만 정하면 됩니다.", "One <b>fluency · minor</b> error and the Agent&rsquo;s reasoning remain, so the human only decides whether to accept it."),
        ],
    },
]
tabs_html = "".join(
    f'<button type="button" class="{"on" if i == 0 else ""}" data-i="{i}" data-en="{en(c["tab"][1])}">{c["tab"][0]}</button>' for i, c in enumerate(CASES)
)
cases_html = ""
for i, c in enumerate(CASES):
    steps = ""
    for kind, tk, te, bk, be in c["steps"]:
        lk, le = KIND[kind]
        steps += (
            f'<li class="lq-s {kind}"><span class="lq-k" data-en="{en(le)}">{lk}</span>'
            f'{T("b", tk, te)}{T("p", bk, be)}</li>'
        )
    cases_html += (
        f'<div class="lq-c{" on" if i == 0 else ""}" data-i="{i}">{T("h3", c["title"][0], c["title"][1])}'
        f'{T("p", c["sum"][0], c["sum"][1], "lead")}<ol class="lq-trace">{steps}</ol></div>'
    )

# distributions from the saved runs (runs/*.json, 127 runs)
WHY = [
    ("카테고리 수정 2회 실패", "Two failures in a category", 42),
    ("숫자·단위 확정 불가", "Numbers/units unconfirmed", 28),
    ("Agent 포기·전략 소진", "Agent gave up / strategies used up", 16),
    ("Critical 오류", "Critical error", 1),
    ("보호 용어 누락", "Protected term missing", 1),
    ("검증 위치(span) 불일치", "Span mismatch", 1),
]
LEFT = [("fluency", 51), ("accuracy", 27), ("spelling", 6), ("grammar", 1), ("terminology", 1), ("style", 1)]
TOOLS_USE = [("spelling", 5, 1), ("grammar", 2, 0), ("fluency", 10, 63), ("accuracy", 6, 31), ("style", 0, 2)]


def rows_why(items, mx, cls):
    out = ""
    for ko, e, val in items:
        out += f'<div class="row"><div class="name n0" data-en="{en(e)}">{ko}</div><div class="track"><div class="bar {cls}" style="--w:{val / mx * 100:.1f}%"></div><span class="bv">{val}</span></div></div>'
    return out


def rows_plain(items, mx, cls):
    out = ""
    for name, val in items:
        out += f'<div class="row"><div class="name n0">{name}</div><div class="track"><div class="bar {cls}" style="--w:{val / mx * 100:.1f}%"></div><span class="bv">{val}</span></div></div>'
    return out


def rows_tools(items):
    out = ""
    for name, ok, rb in items:
        tot = ok + rb
        out += (
            f'<div class="row"><div class="name n0">{name}</div><div class="track"><div class="bar final" style="--w:{ok / tot * 100:.1f}%"></div>'
            f'<span class="bv">{ok} / {tot}</span></div></div>'
        )
    return out


cases = f"""<section class="cs" id="cases"><div class="col">{T("div", "08 실행 사례", "08 CASE FILES", "eb rv")}
{T("h2", "실제 실행 기록으로 보는 &lsquo;어디서, 왜 막혔나&rsquo;", "Real run records: where and why it got stuck", "rv")}
{T("p", "저장된 실행 기록(<code>runs/*.json</code>)에서 고른 사례입니다. 번역이 더 좋아졌는지 점수로 겨루는 것이 아니라, <b>Agent의 단계마다 무슨 일이 일어났고 사람에게 무엇이 남았는지</b>를 따라갑니다.", "Cases picked from the saved run records (<code>runs/*.json</code>). They do not score whether the translation got better; they follow <b>what happened at each Agent step and what was left for the human</b>.", "lead rv")}
<div class="lq rv"><div class="ph-tabs lq-tabs" id="lqtabs">{tabs_html}</div>{cases_html}</div>

<h3 class="grp rv" data-en="Where do humans end up being needed? (127 saved runs)">사람이 필요해지는 곳은 어디였나 (저장된 run 127건)</h3>
<div class="grid6"><div class="rv chart key">{T("h3", "사람 검토로 넘어간 89건: 멈춘 이유<span class='fin'>HITL</span>", "89 runs handed to a human: why it stopped<span class='fin'>HITL</span>")}{T("p", "한 건은 하나의 이유로 분류했습니다. 숫자·단위 28건에는 &lsquo;2~3km&rsquo;, &lsquo;1600킬로미터 → 1,600km&rsquo;처럼 오류라기보다 표기 차이로 확정하지 못한 경우가 포함됩니다.", "Each run is classified under one reason. The 28 number/unit cases include format differences, such as &lsquo;2~3km&rsquo; or &lsquo;1600 킬로미터 → 1,600km&rsquo;, that could not be confirmed.", "q")}{rows_why(WHY, 51, "final")}</div>
<div class="rv chart">{T("h3", "사람에게 남은 오류: MQM 영역", "Errors left for the human: MQM category")}{T("p", "사람 검토 건에 남은 미해결 오류 86개를 영역별로 센 것입니다.", "The 86 unresolved errors left in the human-review runs, counted by category.", "q")}{rows_plain(LEFT, 51, "c2")}</div></div>
<div class="grid6"><div class="rv chart">{T("h3", "도구별 수정 시도: 채택 / 전체", "Tool attempts: accepted / total")}{T("p", "같은 기록에서 수정 시도 중 재평가를 통과해 채택된 비율입니다. 도구마다 잘 듣는 영역이 달라, 사람이 필요한 영역을 미리 짐작할 수 있습니다.", "Of the revision attempts in the same records, the share that passed re-evaluation and was accepted. Tools differ in what they can fix, so you can anticipate where a human will be needed.", "q")}{rows_tools(TOOLS_USE)}</div>
<div class="rv chart">{T("h3", "이 숫자를 읽는 법", "How to read these numbers")}{T("p", "개발·실험 중 쌓인 기록이라(영어 82·일본어 16·프랑스어 12·이탈리아어 9·독일어 8) <b>성능 지표가 아닙니다.</b> 같은 문장을 반복 실행한 건도 포함됩니다.", "These accumulated during development and experiments (English 82, Japanese 16, French 12, Italian 9, German 8), so they are <b>not a performance metric</b>; repeated runs of the same sentence are included.", "q")}
{T("p", "<span class='hl'>이 기록에서 사람 몫으로 남는 것은 주로 fluency와 accuracy의 미세한 차이와, 숫자·단위 표기의 확정 불가였습니다.</span> 그래서 이 영역에서 멈출 때 이유를 붙여 알려주는 것이 Agent 구조의 핵심 역할입니다.", "<span class='hl'>In these records, what is left for humans is mostly subtle fluency/accuracy differences and number/unit formats that cannot be confirmed.</span> Reporting the reason when it stops in those areas is the Agent structure&rsquo;s main job.", "note")}</div></div>
</div></section>"""

# ---------------------------------------------------------------- 09 product gallery
PRODUCT = [
    ("ui-hero.png", "u", "Service", "서비스", "1. 서비스 화면", "1. Service screen", "입력 방식과 목표 국가를 고르면 번역 &rarr; MQM 평가 &rarr; 수정 &rarr; 사람 승인 단계가 진행 표시와 함께 나옵니다.", "Choose the input mode and target country; the steps translate &rarr; MQM &rarr; revise &rarr; approval appear with progress."),
    ("ui-mode-direct.png", "u", "Input", "입력", "2. 직접 입력: 언어 고르기", "2. Direct input: choose languages", "한국어 원문(필수)과 목표 국가, 보호 용어·추가 지시(선택)를 넣고 사람이 한 문장씩 점검합니다.", "Enter the Korean source (required), target countries, and optional protected terms and instructions to check one sentence at a time."),
    ("ui-mode-csv.png", "u", "Input", "입력", "3. CSV: 여러 문장 × 여러 국가", "3. CSV: many sentences × many countries", "<code>한국어</code> 열이 있는 CSV(최대 30문장)를 올리면 즉시 검증하고 &ldquo;몇 건이 실행될지&rdquo;를 미리 보여줍니다. 한 행에 <code>Japan|Italy</code>처럼 쓰면 언어별로 따로 실행되고, 한 건이 실패해도 나머지는 계속됩니다.", "Upload a CSV with a <code>한국어</code> column (max 30 sentences); it validates at once and previews how many runs will execute. A row like <code>Japan|Italy</code> runs per language, and one failure does not stop the rest."),
    ("ui-mode-poc.png", "u", "Input", "입력", "4. PoC 테스트", "4. PoC test", "내장 문장 30개 중 하나를 골라 바로 돌려 봅니다. 설치 확인과 데모, 모델·프롬프트 변경 전후 비교에 씁니다.", "Pick one of 30 built-in sentences and run it right away, for install checks, demos, and before/after comparison of model or prompt changes."),
    ("ui-run.png", "c", "Result", "결과", "5. 실행 결과: 단계·상태·판단 근거", "5. Run result: steps, status, reasoning", "진행 단계, 상태 배지, 원문·번역 비교, 수정 이력(채택/Rollback), Agent 판단 근거를 국가별 카드로 보여줍니다. 어디서 멈췄는지가 한눈에 보입니다.", "Progress steps, status badge, source vs. translation, revision history (accepted / rolled back) and Agent reasoning per country, so where it stopped is visible at a glance."),
    ("ui-review.png", "c", "Result", "결과", "6. 검토·승인", "6. Review & approval", "남은 MQM 오류와 실패 사유, 이전 버전과의 변경점(diff)을 보고 직접 수정 / AI 재수정 / 승인 / 거부를 선택합니다. 프랑스어 예시는 숫자·단위를 자동 확정할 수 없어 후보를 거부하고 사람에게 넘긴 의도된 동작입니다.", "See remaining MQM errors, failure reasons and a diff against the previous version, then edit / AI re-revise / approve / reject. The French example rejects the candidate and hands off because numbers/units cannot be confirmed automatically, which is intended."),
]
beats = ""
inds = ""
for i, (f, kind, tag_en, tag_ko, t_ko, t_en, d_ko, d_en) in enumerate(PRODUCT):
    key = " key" if i in (4, 5) else ""
    fig_en = f'<span class="tg {kind}">{tag_en}</span><b>{t_en}</b><br/>{d_en}'
    beats += (
        f'<div class="beat" data-beat="{i}"><figure class="tile{key}"><div class="shot"><img alt="{en(t_en)}" src="img/{f}"/></div>'
        f'<figcaption data-en="{en(fig_en)}"><span class="tg {kind}">{tag_ko}</span><b>{t_ko}</b><br/>{d_ko}</figcaption></figure></div>'
    )
    inds += f'<li data-beat="{i}" data-en="{en(t_en)}">{t_ko}</li>'
product = f"""<section class="cs gal gal2" id="product"><div class="col stage-grid"><div class="stage-l">{T("div", "09 화면", "09 PRODUCT", "eb")}
{T("h2", "고르고, 돌리고, 막힌 곳을 확인합니다", "Choose, run, and check where it got stuck")}
{T("p", "어느 입력 방식이든 이후 흐름(번역 &rarr; MQM 평가 &rarr; 수정 &rarr; 사람 승인)은 같습니다. 화면 속 결과는 로컬 Qwen3.5 4B로 실제 실행해 저장된 기록을 다시 불러와 캡처했고, 문장은 모두 작성자가 만든 가상의 예시입니다.", "Whichever way you enter text, the rest is identical: translate &rarr; MQM &rarr; revise &rarr; human approval. Results shown were captured by reloading real runs (local Qwen3.5 4B); all sentences are fictional examples by the author.", "lead")}
<ol class="ind">{inds}</ol></div>
<div class="stage-r"><div class="beats cardbeats tilebeats">{beats}</div>
<div class="gnav"><button type="button" class="gb" data-d="-1" aria-label="Previous screen">&larr;</button><span class="gcount">1 / {len(PRODUCT)}</span><button type="button" class="gb" data-d="1" aria-label="Next screen">&rarr;</button></div></div></div></section>"""

# ---------------------------------------------------------------- 10 / 11
VP = GITHUB + "/blob/main/docs/VALIDATION_PROTOCOL.md"
safety = f"""<section class="cs" id="safety"><div class="col">{T("div", "10 안전", "10 SAFETY", "eb rv")}{T("h2", "사람이 결정권을 갖도록", "Keeping the decision with a human", "rv")}
<div class="rv"><table class="tbl oneline">
<tr>{T("th", "자동 승인 없음", "No auto-approval")}{T("td", "오류가 하나도 없어도 <code>AWAITING_HUMAN_APPROVAL</code>에서 멈춥니다. 번역 메모리(TM) 일치도 자동 승인하지 않습니다.", "Even with zero errors the run stops at <code>AWAITING_HUMAN_APPROVAL</code>. A translation-memory (TM) hit is not auto-approved either.")}</tr>
<tr>{T("th", "Agent의 권한 제한", "Limited Agent authority")}{T("td", "Agent는 다음 도구와 이유만 고릅니다. 후보의 채택·Rollback·상태 전환은 Python 검사와 MQM 재평가가 정합니다.", "The Agent only chooses the next tool and a reason. Acceptance, rollback and state transitions are decided by Python checks and MQM re-evaluation.")}</tr>
<tr>{T("th", "결정적 검사", "Deterministic checks")}{T("td", "보호 용어, 숫자·단위, 번역에 섞인 메타 주석은 LLM이 아니라 규칙으로 막고, 확정할 수 없으면 사람에게 넘깁니다.", "Protected terms, numbers/units and leaked meta-comments are caught by rules, not the LLM; if they cannot be confirmed the run goes to a human.")}</tr>
<tr>{T("th", "설명 가능성", "Explainability")}{T("td", "수정 전후, Agent 판단 근거, 채택/거부 사유를 <code>run_id</code>별 JSON으로 저장하고 결과는 CSV로 누적합니다.", "Before/after, Agent reasoning and accept/reject reasons are stored per <code>run_id</code> as JSON; results accumulate in CSV.")}</tr>
<tr>{T("th", "검증 원칙", "Validation protocol")}{T("td", "테스트 통과는 번역 품질의 증거가 아니고, 실험 결과가 사람 승인을 대신하지 않습니다. 증거의 범위는 <a href='" + VP + "' target='_blank' rel='noopener'>VALIDATION_PROTOCOL.md</a>에 정리했습니다.", "Passing tests is not proof of translation quality, and an experiment result does not replace human approval. The evidence boundaries are written down in <a href='" + VP + "' target='_blank' rel='noopener'>VALIDATION_PROTOCOL.md</a>.")}</tr>
</table></div></div></section>"""

more = f"""<section class="cs" id="more"><div class="col">{T("div", "11 기타", "11 MORE", "eb rv")}{T("h2", "기타", "More", "rv")}
<div class="rv"><table class="tbl oneline">
<tr>{T("th", "현재 한계", "Limits")}{T("td", "소형 로컬 모델(Qwen3.5 4B) 기준이라 Agent의 판단 품질에 한계가 있습니다. Planner가 실제 오류에 근거하지 않고 도구를 고르는 경우가 있어(사례 B), 선택 가능한 도구를 남은 오류의 영역으로 제한하는 개선을 계획 중입니다. 숫자·단위 검사는 표기 차이를 오탐할 수 있습니다.", "The small local model (Qwen3.5 4B) limits the Agent&rsquo;s judgment. The planner sometimes picks a tool without grounding in an actual error (Case B); restricting its choices to categories present in the remaining errors is planned. The number/unit check can false-positive on format differences.")}</tr>
<tr>{T("th", "미구현", "Not built")}{T("td", "CSV는 순차 실행(최대 30문장)입니다. 비동기 큐·병렬·다중 사용자와 LangGraph Checkpointer, 모델별 정량 비교와 Golden Dataset 평가는 향후 과제입니다. RAG/Vector DB는 범위에서 제외했습니다.", "CSV runs sequentially (max 30). Async queue, parallelism, multi-user, a LangGraph Checkpointer, per-model quantitative comparison and a golden dataset are future work. RAG/vector DB is out of scope.")}</tr>
<tr>{T("th", "데이터", "Data")}{T("td", "공개 데이터셋 FLORES+(CC BY-SA 4.0)만 사용했고, TM·용어집·DNE는 이를 바탕으로 새로 만들었습니다. 화면과 사례 속 예시 문장은 FLORES+ 문장을 제외하면 모두 가상입니다.", "Only the public FLORES+ dataset (CC BY-SA 4.0) is used; TM, terminology and DNE were newly derived from it. Apart from FLORES+ sentences, all example sentences shown are fictional.")}</tr>
<tr>{T("th", "독립성", "Independence")}{T("td", "작성자 개인이 개인 시간·장비로 만든 독립 프로젝트이며, 어떤 회사의 내부 코드·프롬프트·데이터·평가 결과도 포함하지 않습니다. 코드는 MIT 라이선스입니다.", "An independent personal project built on personal time and equipment; it contains no internal code, prompts, data or evaluation results of any company. Code is MIT-licensed.")}</tr>
<tr><th>Tech</th><td>Python 3.11, LangChain (LCEL), Pydantic, Ollama (Qwen3.5 4B), OpenAI gpt-5-mini</td></tr>
<tr><th>Tech (UI &amp; data)</th><td>Gradio (PWA, English/한국어), pandas, pytest, FLORES+</td></tr>
<tr>{T("th", "저장소", "Repository")}<td><a href="{GITHUB}" target="_blank" rel="noopener">github.com/sihunwang-skala/l10n-quality-agent</a></td></tr>
</table></div></div></section>"""

# ---------------------------------------------------------------- assemble
head = (HERE / "template/head.html").read_text(encoding="utf-8").replace("@@TITLE@@", "L10n Quality Agent")
override = """<style>
/* l10n additions on top of the shared case-study CSS */
.ph.win{width:100%;max-width:340px;aspect-ratio:4/4.7;border-width:8px;border-radius:18px}
.ph.win .notch{display:none}
.role{font:700 14px/1.4 "Noto Sans KR",sans-serif;letter-spacing:.06em;color:var(--ac);margin:0 0 14px}
/* product gallery: always one screen at a time (slides), even when the page is not pinned */
html:not(.pinned) .tilebeats .beat{display:none}
html:not(.pinned) .tilebeats .beat.on{display:block}
/* hero screenshots: wide browser window below the text, so the web app is readable */
.hero-grid{grid-template-columns:minmax(0,1fr)!important}
.ph-wrap{max-width:1040px;width:100%;margin:28px auto 0}
.ph.win{width:100%;max-width:1040px;height:auto;aspect-ratio:auto;border:0;border-radius:14px;background:#fff;box-shadow:0 24px 60px rgba(20,20,40,.18);overflow:hidden;padding:0}
.ph.win::before{content:"";display:block;height:30px;background:#eceef2;border-bottom:1px solid #d9dde4}
.ph.win .pi{position:relative;inset:auto;width:100%;height:auto;max-height:660px;object-fit:cover;object-position:top;transform:none;opacity:1;display:none}
.ph.win .pi.on{display:block}
.ph-tabs{justify-content:flex-start}
.ph.win{background:#fff}
.ph.win .pi{object-position:top;object-fit:contain;background:#fff;display:none}
.ph.win .pi.on{display:block}
html[lang=en] .ph.win .pi.ko{display:none}
html:not([lang=en]) .ph.win .pi.en{display:none}
.tile .shot{display:block;width:100%;padding:0;cursor:default}
.tile .shot img{display:block;width:100%;max-height:62vh;object-fit:cover;object-position:top}
.tile .shot:hover{transform:none}
code{font:500 .88em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);padding:1px 6px;border-radius:6px}
.card code,.tbl code,.lq code{background:var(--bg)}
.fig .imgbox{overflow-x:auto;border:1px solid var(--line);border-radius:18px;padding:12px;background:#fff}
.tbl.oneline{width:100%;table-layout:fixed}.tbl.oneline th{width:170px}.tbl.oneline td,.tbl.oneline th{white-space:normal;overflow-wrap:anywhere}
/* narrow / portrait screens: never let the hero push the page wider than the viewport */
.hero-grid>*{min-width:0}
@media (max-width:1100px){.hero-grid{grid-template-columns:minmax(0,1fr)}.quote{white-space:normal;overflow:visible}.ph.win{max-width:420px}}
html,body{overflow-x:clip}
/* tap affordance: map buttons gently bounce in, then hint once when scrolled into view */
.lq-n{transition:transform .2s ease,border-color .2s,background .2s,box-shadow .2s}
.lq-n:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(16,24,40,.10)}
.lq-n:active{transform:scale(.97)}
.lq-n.bounce{animation:lqBounce .6s cubic-bezier(.3,1.5,.5,1) both;animation-delay:calc(var(--k,0) * 70ms)}
.lq-n.hint i{animation:lqPulse 1.6s ease-in-out 2}
.lq-n.on i{transform:scale(1.08)}
@keyframes lqBounce{0%{opacity:0;transform:translateY(12px) scale(.96)}60%{opacity:1;transform:translateY(-4px) scale(1.02)}100%{opacity:1;transform:none}}
@keyframes lqPulse{0%,100%{box-shadow:0 0 0 0 rgba(47,42,107,.35)}50%{box-shadow:0 0 0 7px rgba(47,42,107,0)}}
.lq-panel{transition:box-shadow .3s}
.lq-panel.flash{animation:lqFlash .5s ease}
@keyframes lqFlash{0%{box-shadow:0 0 0 0 rgba(47,42,107,.25)}100%{box-shadow:0 0 0 14px rgba(47,42,107,0)}}
@media (prefers-reduced-motion:reduce){.lq-n,.lq-n.bounce,.lq-n.hint i,.lq-panel.flash{animation:none!important;transition:none!important}}
/* paper-style typography (matches the technical report): one sans family, bold headings, tighter tracking */
*{font-family:"Noto Sans KR","Apple SD Gothic Neo","Helvetica Neue",Arial,sans-serif!important}
code,pre,kbd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace!important}
body{font-size:16px!important;line-height:1.85!important;color:#111!important}
h1,h2,h3,h4{font-weight:700!important;letter-spacing:-.01em!important;line-height:1.35!important}
.cs h2,h1{font-size:clamp(24px,3vw,34px)!important}
.hmw{font-weight:700!important;letter-spacing:-.02em!important}
.lead,.cs .lead,.lq-s p,.card p,.note2{font-weight:400!important;line-height:1.85!important}
.eb,.lq-k,.lq-r b,.tg,.ptags,.tags span{font-weight:700!important;letter-spacing:.04em!important}
/* keyword highlighter: neon marker behind key terms */
mark.kw{background:linear-gradient(transparent 52%,#ffef3a 52%,#ffef3a 92%,transparent 92%);color:inherit;padding:0 .12em;font-weight:700;border-radius:2px;-webkit-box-decoration-break:clone;box-decoration-break:clone}
html[data-theme=dark] mark.kw{background:linear-gradient(transparent 52%,rgba(255,239,58,.55) 52%,rgba(255,239,58,.55) 92%,transparent 92%);color:#fff}
/* definition sentence: keep every line on one row, words light up with scroll */
.hmw{max-width:none}
.hmw .ln{white-space:nowrap}
@media (max-width:900px){.hmw .ln{white-space:normal}}
/* human-handoff map */
.lq-map{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:6px 0 16px}
.lq-n{all:unset;box-sizing:border-box;cursor:pointer;display:flex;align-items:center;gap:10px;padding:12px 14px;border:1.5px solid var(--line);border-radius:14px;background:var(--bg);font:600 14px/1.3 Inter,"Noto Sans KR",sans-serif;transition:.2s}
.lq-n i{font:700 12px/1 Manrope,sans-serif;font-style:normal;flex:none;width:26px;height:26px;border-radius:50%;display:grid;place-items:center;background:var(--soft)}
.lq-n:hover{border-color:var(--ac)}
.lq-n.on{border-color:var(--ac);background:var(--soft)}.lq-n.on i{background:var(--ac);color:var(--bg)}
.lq-n.ok i{background:#d9f0e2;color:#1f6b45}html[data-theme=dark] .lq-n.ok i{background:#16352a;color:#8fd6b0}
.lq-n.ok.on i{background:#2e8b57;color:#fff}
.lq-panel{border:1px solid var(--line);border-radius:18px;background:var(--soft);padding:26px 30px;min-height:300px}
.lq-d{display:none}.lq-d.on{display:block;animation:lqin .45s ease}
@keyframes lqin{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.lq-h h3{font:500 22px/1.3 Inter,"Noto Sans KR",sans-serif;letter-spacing:-.03em;margin:0 0 14px}
.lq-r{display:grid;grid-template-columns:120px 1fr;gap:14px;padding:12px 0;border-top:1px solid var(--line);font-size:15px;line-height:1.65;color:var(--mute)}
.lq-r b{font:700 11.5px/1.9 Manrope,sans-serif;letter-spacing:.12em;color:var(--ink);text-transform:uppercase}
.lq-r span{min-width:0}
/* case files */
.lq-tabs{justify-content:flex-start;margin:6px 0 22px}
.lq-c{display:none}.lq-c.on{display:block;animation:lqin .45s ease}
.lq-c>h3{font:500 clamp(22px,2.4vw,28px)/1.3 Inter,"Noto Sans KR",sans-serif;letter-spacing:-.03em;margin:0 0 8px}
.lq-c .lead{margin-bottom:22px}
.lq-trace{list-style:none;margin:0;padding:0 0 0 22px;border-left:2px solid var(--line)}
.lq-s{position:relative;margin:0 0 18px;padding:0 0 0 6px}
.lq-s::before{content:"";position:absolute;left:-30px;top:6px;width:12px;height:12px;border-radius:50%;background:var(--grey);border:3px solid var(--bg)}
.lq-s.agent::before{background:#7fa8dc}.lq-s.check::before{background:#a597d9}.lq-s.rb::before{background:#e4572e}.lq-s.human::before{background:#ffc928}.lq-s.auto::before{background:#7cc096}
.lq-k{display:inline-block;font:700 10.5px/1 Manrope,sans-serif;letter-spacing:.12em;text-transform:uppercase;padding:5px 9px;border-radius:99px;margin-right:10px;background:var(--soft);color:var(--mute);vertical-align:1px}
.lq-s.agent .lq-k{background:#e3edf9;color:#27538a}.lq-s.check .lq-k{background:#ece9fb;color:#2f2a6b}.lq-s.rb .lq-k{background:#fde7e1;color:#a83a1c}.lq-s.human .lq-k{background:#ffefb8;color:#5b4300}.lq-s.auto .lq-k{background:#dff1e6;color:#1f6b45}
html[data-theme=dark] .lq-s.agent .lq-k{background:#1d2f47;color:#a6c7ef}html[data-theme=dark] .lq-s.check .lq-k{background:#27244d;color:#c9c5ff}html[data-theme=dark] .lq-s.rb .lq-k{background:#3d1f17;color:#ffb199}html[data-theme=dark] .lq-s.human .lq-k{background:#3b3010;color:#ffd96a}html[data-theme=dark] .lq-s.auto .lq-k{background:#16352a;color:#8fd6b0}
.lq-s b{font:600 16.5px/1.4 Inter,"Noto Sans KR",sans-serif;color:var(--ink)}
.lq-s p{margin:6px 0 0;font-size:15px;line-height:1.7;color:var(--mute)}
.lq-s p b{font-size:inherit;font-weight:700}
@media (max-width:900px){.lq-map{grid-template-columns:repeat(2,minmax(0,1fr))}.lq-r{grid-template-columns:1fr;gap:2px}.lq-panel{padding:20px}}
</style>
"""
head = head.replace("</head>", override + "</head>") if "</head>" in head else head + override + "</head>"
scripts = (HERE / "template/scripts.html").read_text(encoding="utf-8")
custom_js = """<script>
/* keep the page from drifting sideways (it caused the cut-off text on some screens) */
(function(){addEventListener("scroll",function(){if(scrollX){scrollTo(0,scrollY)}},{passive:true});})();
/* handoff map + case tabs: all text is already in the DOM (with data-en), so the language switch keeps working */
(function(){
function pick(box,btnSel,paneSel,i){box.querySelectorAll(btnSel).forEach(function(b){b.classList.toggle('on',+b.dataset.i===i)});box.querySelectorAll(paneSel).forEach(function(p){p.classList.toggle('on',+p.dataset.i===i)})}
var map=document.getElementById('lqmap');
if(map){var root=map.closest('.lq');var panel=root.querySelector('.lq-panel');
 map.querySelectorAll('.lq-n').forEach(function(b){b.addEventListener('click',function(){pick(root,'.lq-n','.lq-d',+b.dataset.i);if(panel){panel.classList.remove('flash');void panel.offsetWidth;panel.classList.add('flash')}})});
 /* when the map scrolls into view: bounce the buttons in once, then pulse the first unvisited one as a hint */
 var played=false;
 var io=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting||played)return;played=true;io.disconnect();
   var btns=map.querySelectorAll('.lq-n');btns.forEach(function(b){b.classList.add('bounce')});
   setTimeout(function(){btns.forEach(function(b){b.classList.remove('bounce')});var h=map.querySelector('.lq-n:not(.on)');if(h)h.classList.add('hint');setTimeout(function(){if(h)h.classList.remove('hint')},3400)},900)})},{threshold:.35});
 io.observe(map);
}
var tabs=document.getElementById('lqtabs');
if(tabs){var box=tabs.closest('.lq');tabs.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){pick(box,'#lqtabs button','.lq-c',+b.dataset.i)})})}
})();
</script>"""
page = (
    head + "<body>\n" + side + "<main>" + hero + "\n" + context + "\n" + problem + "\n" + define + "\n" + decision + "\n"
    + build + "\n" + approach + "\n" + architecture + "\n" + cases + "\n" + product + "\n" + safety + "\n" + more
    + "\n</main>\n" + scripts + "\n" + custom_js + "\n</body></html>\n"
)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
out = Path(args[0]) if args else HERE / "index.html"
out.write_text(page, encoding="utf-8")
print("wrote", out, len(page), "bytes")
