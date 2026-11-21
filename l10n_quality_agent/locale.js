(app) => {
  const koToEn = {
    "기본 모델 · Qwen3.5 4B (로컬)": "Primary model · Qwen3.5 4B (local)",
    "보조 모델 · OpenAI gpt-5-mini (API, 키 없음 → Mock)": "Fallback model · OpenAI gpt-5-mini (API, no key → mock)",
    "번역 → MQM 평가 → 유형별 수정 → 재검증 → 사람 승인. 모든 과정이 기록됩니다.": "Translate → MQM review → targeted revisions → recheck → human approval. Every step is recorded.",
    "① 어떻게 입력할까요?": "① How would you like to enter text?",
    "② 어느 나라 번역으로?": "② Which languages should we translate into?",
    "🧪 PoC 테스트 · 내장 예시 문장": "🧪 PoC test · sample sentence",
    "✍️ 직접 입력 · 사람이 타이핑": "✍️ Direct input · type manually",
    "📄 CSV 업로드 · 자동 일괄 번역": "📄 CSV upload · automated batch translation",
    "프로젝트가 정상 동작하는지 확인하는 테스트·데모용 모드입니다.": "Use this mode to test or demo that the project is working.",
    "내장 문장 30개 중 1개 선택 (직접 입력할 것 없음)": "Choose one of 30 included sentences. No typing needed.",
    "공개 데이터 FLORES+ 문장을 번역 → MQM 평가 → 수정합니다. 결과 CSV의 id에 문장 번호가 기록됩니다.": "Translate a public FLORES+ sentence, review it with MQM, and revise it. The sentence ID is saved in the results CSV.",
    "설치 확인, 데모, 모델·프롬프트를 바꾼 뒤 같은 문장으로 비교할 때": "Check the setup, demo the app, or compare model and prompt changes on the same sentence.",
    "사람이 문장을 직접 쓰고 한 건씩 결과를 확인하는 모드입니다.": "Write a sentence and review its result one at a time.",
    "한국어 원문 (필수) · 보호 용어, 추가 지시 (선택)": "Korean source text (required) · protected terms and extra instructions (optional)",
    "입력한 한 문장을 선택한 국가마다 따로 실행합니다. 결과를 보고 직접 수정·AI 재수정·승인할 수 있습니다.": "Run the sentence separately for each selected language. Review, edit, revise with AI, or approve the result.",
    "실제 업무 문장의 품질을 점검하거나, 특정 용어가 유지되는지 시험할 때": "Check real work text or confirm that protected terms stay unchanged.",
    "여러 문장이 담긴 CSV 파일을 올리면 모든 행을 자동으로 차례대로 번역합니다.": "Upload a CSV to translate each row automatically, one after another.",
    "행마다 번역 → MQM → 수정까지 자동으로 실행하고 결과 CSV에 저장합니다. 최종 승인은 자동이 아니라 ‘검토·승인’ 탭에서 사람이 합니다.": "Each row is translated, reviewed with MQM, revised, and saved to a results CSV. A person gives final approval in the Review tab.",
    "문장 여러 개를 한꺼번에 점검할 때. 아래 양식을 내려받아 채우면 됩니다": "Review many sentences at once. Download and fill in the template below.",
    "입력할 것": "What to enter",
    "하는 일": "What it does",
    "이럴 때": "Use this when",
    "실행할 수 없습니다": "Cannot run",
    "✓ 실행 준비 완료": "✓ Ready to run",
    "문장당 수십 초~수 분 걸릴 수 있습니다": "May take tens of seconds to a few minutes per sentence",
    "일괄 번역 진행 ": "Batch translation progress ",
    "실패 ": "Failed ",
    "✕ 실행 실패": "✕ Run failed",
    "키 있음": "API key set",
    "키 없음 → Mock": "No key → mock mode",
    "키가 등록되어 있습니다.": "API key is set.",
    "보조 모델을 쓰려면 API 키 등록이 필요합니다.": "Set an API key to use the fallback model.",
    "저장 결과": "Saved results",
    "실행 과정": "Run details",
    "현재 선택한 결과를 다시 저장하거나 CSV를 내려받을 수 있습니다.": "Save the selected result again or download the CSV.",
    "어떻게 입력할까요?": "How would you like to enter text?",
    "내장 예시 문장 (총 30개)": "Sample sentence (30 included)",
    "고르기만 하면 됩니다. 입력할 내용은 없습니다": "Choose a sample. No typing needed.",
    "선택한 문장 (읽기 전용)": "Selected sentence (read only)",
    "한국어 원문 (필수)": "Korean source text (required)",
    "번역할 한국어 문장을 직접 입력하세요": "Enter the Korean text to translate",
    "보호 용어 (선택)": "Protected terms (optional)",
    "추가 지시 (선택)": "Extra instructions (optional)",
    "CSV 양식 (내려받아 채워서 올리세요)": "CSV template (download, fill in, and upload)",
    "번역할 CSV 업로드": "Upload a CSV to translate",
    "업로드 내용 미리보기": "Upload preview",
    "어느 나라 번역으로?": "Which languages should we translate into?",
    "고급 옵션": "Advanced options",
    "번역 실행": "Run translation",
    "실행 결과": "Run results",
    "검토 · 승인": "Review and approve",
    "직접 수정": "Edit manually",
    "AI 재수정": "Revise with AI",
    "직접 수정 저장": "Save manual edit",
    "AI 재수정 실행": "Run AI revision",
    "최종 승인": "Approve final version",
    "거부": "Reject",
    "처리 결과": "Action result",
    "저장된 결과 CSV": "Saved results CSV",
    "현재 선택 결과 저장": "Save selected result",
    "새로고침": "Refresh",
    "저장 상태": "Save status",
    "CSV 행 수와 저장 위치": "CSV row count and file location",
    "저장된 결과 미리보기": "Saved results preview",
    "결과 CSV 열기·다운로드": "Open or download results CSV",
    "상세 로그": "Detailed log",
    "결과 저장 파일": "Results file",
    "CSV 업로드 (자동 일괄 번역)": "CSV upload (batch translation)",
    "직접 입력 (사람이 타이핑)": "Direct input (type manually)",
    "PoC 테스트 (내장 예시 문장)": "PoC test (sample sentence)",
    "한국어 원문": "Korean source text",
    "보호 용어": "Protected terms",
    "추가 지시": "Extra instructions",
    "입력할 것": "What to enter",
    "하는 일": "What it does",
    "이럴 때": "Use this when",
    "실행 중": "Running",
    "번역": "Translation",
    "MQM 평가": "MQM review",
    "전문 수정": "Targeted revision",
    "재검증": "Recheck",
    "사람 승인": "Human approval",
    "초안": "Draft",
    "평가 중": "Evaluating",
    "수정 중": "Revising",
    "사람 검토 필요": "Needs human review",
    "승인 대기": "Awaiting approval",
    "승인됨": "Approved",
    "거부됨": "Rejected",
    "오류": "Errors",
    "남은 오류": "Remaining errors",
    "현재 버전": "Current version",
    "초기 번역": "Initial translation",
    "수정 이력": "Revision history",
    "해결되지 않은 오류": "Unresolved errors",
    "Agent 판단 근거": "Agent reasoning",
    "원문": "Source",
    "번역문": "Translation",
    "수정 시도": "Revision attempts",
    "채택": "Accepted",
    "거부": "Rejected",
    "경미": "Minor",
    "주요": "Major",
    "치명": "Critical",
    "정확성": "Accuracy",
    "용어": "Terminology",
    "철자": "Spelling",
    "문법": "Grammar",
    "문체": "Style",
    "유창성": "Fluency",
    "저장했습니다": "Saved",
    "비교할 이전 버전": "Previous version",
    "검토 대상 국가": "Language to review",
    "번역문 직접 편집": "Edit translation",
    "선택 버전에 대한 추가 수정 지시": "Instructions for the selected version",
    "AI 재수정에 사용할 모델": "Model for AI revision",
    "결과는 자동 저장됩니다": "Results are saved automatically",
    "전체": "All",
    "일본어": "Japanese",
    "프랑스어": "French",
    "영어": "English",
    "한국어": "Korean",
  };
  const key = "l10n-quality-agent-language";
  let language = localStorage.getItem(key) || "ko";
  const translateText = (value) => {
    const trimmed = value.trim();
    const translated = koToEn[trimmed];
    return translated ? value.replace(trimmed, translated) : value;
  };
  const apply = () => {
    document.documentElement.lang = language;
    const root = document.querySelector(".gradio-container") || document.body;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (const node of nodes) {
      if (node.parentElement?.closest("code,pre,textarea,[data-l10n-source]")) continue;
      const original = node.__l10nOriginal ?? node.textContent;
      node.__l10nOriginal = original;
      const next = language === "ko" ? original : translateText(original);
      if (node.textContent !== next) node.textContent = next;
    }
    root.querySelectorAll("input,textarea,button,[role=tab],label").forEach((el) => {
      for (const attr of ["placeholder", "aria-label", "title"]) {
        if (!el.hasAttribute(attr)) continue;
        const original = el.getAttribute(`data-l10n-${attr}`) ?? el.getAttribute(attr);
        el.setAttribute(`data-l10n-${attr}`, original);
        el.setAttribute(attr, language === "ko" ? original : translateText(original));
      }
    });
  };
  const mount = () => {
    if (!document.body) return;
    let toggle = document.getElementById("l10n-language-toggle");
    if (!toggle) {
      toggle = document.createElement("div");
      toggle.id = "l10n-language-toggle";
      toggle.innerHTML = '<button type="button" data-language="en">English</button><button type="button" data-language="ko">한국어</button>';
      document.body.appendChild(toggle);
      toggle.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-language]");
        if (!button) return;
        language = button.dataset.language;
        localStorage.setItem(key, language);
        toggle.querySelectorAll("button").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
        apply();
      });
    }
    toggle.querySelectorAll("button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.language === language)));
    apply();
  };
  mount();
  const observer = new MutationObserver(() => mount());
  observer.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  return app;
}

