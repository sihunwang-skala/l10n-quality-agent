# Experiment Log

프롬프트/Agent 변경 실험 기록. 한 번에 하나의 가설만 바꾸고, 변경 전후 결과를 기록한다. 아직 프롬프트를 실제로 바꾼 적은 없다 — 지금까지는 전부 Baseline 측정.

---

## 2026-09-22 · Baseline 0 (스모크 테스트, 프롬프트 변경 없음)

**목적**: FLORES+ 연결 파이프라인이 끝까지 도는지 확인, 다음 실험에 쓸 표본 규모 감을 잡기.

**조건**: split=dev, language=German, n=2 (seed=42로 뽑힌 id 453, 792), 프롬프트/코드 변경 없음(오늘 세션에서 이미 반영된 `reasoning=False`, `num_predict=1536`, `keep_alive=30m` 설정 그대로).

**결과**:

| id | chrF A(단순번역) | chrF B(Agent 최종) | B 상태 | attempts | 비고 |
|---|---|---|---|---|---|
| 453 | 58.8 | 62.9 | HUMAN_REVIEW_REQUIRED | 3 (2 accepted) | fluency 오류 1건, 2회 수정 시도 후 실패 → 사람 검토 |
| 792 | 45.2 | 45.9 | HUMAN_REVIEW_REQUIRED | 2 (1 accepted) | accuracy+spelling 오류, 2회 시도 후 실패 → 사람 검토 |

**관찰**:
- Agent가 두 사례 모두 chrF를 개선시킴(단순 번역보다 나음) — Checkpoint 03까지의 속도/truncation 수정이 최소한 이 2문장에서는 결과를 망가뜨리지 않았다는 확인.
- 두 사례 모두 "오류를 발견했지만 카테고리별 2회 시도 안에 완전히 못 고침" 패턴으로 사람 검토 전환. `AWAITING_HUMAN_APPROVAL`까지 간 사례가 아직 없어서, 이 패턴이 흔한 것인지는 표본 2개로는 판단 불가.
- id 453에서 후보 채택이 2회 있었다는 것(accepted=2, attempts=3)은 다른 카테고리(예: terminology)는 성공적으로 고쳤고, fluency 하나만 반복 실패했다는 뜻 — 카테고리별 성공률이 다를 수 있다는 신호(가설 후보).

**결론**: 롤백 없음, 프롬프트 변경 없음. **다음 실험 후보 가설**(아직 미검증):
- 가설 A: fluency 카테고리 수정 프롬프트(`REVISION_ROLES["fluency"]`)가 다른 카테고리보다 실패율이 높을 수 있다 — 표본을 늘려 카테고리별 accept/reject 비율을 먼저 집계해야 확인 가능.
- 가설 B: `category_count(after, category) >= category_count(evaluation, category)` 재시도-거부 조건이, MQM이 같은 카테고리 안에서 잔여 문제를 다른 설명으로 재탐지할 때 "개선됐는데도 거부"로 오판할 수 있다 — 이건 프롬프트가 아니라 `workflow.py`의 판정 로직 이슈라 이번 작업 범위(프롬프트 개선)에서는 벗어남. 근거가 더 쌓이면 별도 이슈로 기록.

---

## 2026-09-22 · Wikivoyage KO→EN 확장: 단일 문장 스모크 3종 (section 17 순서)

**조건**: TM(10개) + 용어집(승인 4/candidate 1) + DNE(승인 1) 적용, target_language=English/target_country=United States.

| # | 목적 | 소요시간 | 결과 |
|---|---|---|---|
| 1 | TM 매칭 | 32.70s | `tm_hit=True, tm_source_id=865`, 신규 번역 호출 생략 확인(`chains.translate` 미호출), 번역=TM 원문 그대로. 이후 MQM+수정 루프는 정상 진행되어 `HUMAN_REVIEW_REQUIRED`로 종료 — TM 매칭도 자동 승인되지 않는다는 요구사항 충족. |
| 2 | 신규 번역 + MQM | 1.01s | **MQM까지 못 감** — `validate_initial()`이 숫자/단위 불일치로 즉시 `HUMAN_REVIEW_REQUIRED` 처리. 원인: 원문 "2~3km"(범위 표현)가 `['2','3km']`로, 번역 "2 to 3 kilometers"가 `['2','3']`로 추출됨(단위가 spelled-out("kilometers")이라 `NUMBER_UNIT_RE`의 약어 목록에 없어서 unit이 통째로 빠짐). **번역 자체는 정확한데 결정적 검증기의 정규식 한계로 오탐** — Checkpoint 03의 "90만원" 사례와 같은 계열의 새로운 오탐 유형. |
| 3 | 수정 + Rollback | 17.75s | fluency 오류 1건, 2회 수정 시도 모두 "대상 카테고리 오류가 감소하지 않음"으로 거부 → v1으로 Rollback 유지, `HUMAN_REVIEW_REQUIRED`. 고정 Workflow가 실패하는 실제 사례 확보 — **다음 단계(Qwen Agent) 트리거 조건과 정확히 일치**. |

**결론**: TM/용어집/DNE 배선 정상 동작 확인. MQM+Workflow 로직은 기존 그대로 재사용됨(코드 변경 없음). 발견된 신규 이슈(#2, 범위 표현+spelled-out 단위 오탐)는 이번 범위에서 수정하지 않고 한계로 기록만 함 — 검증기 정규식 확장은 별도 작업.

## 2026-09-22 · Qwen Agent 도입 + 실제 버그 발견/수정 + 평가 5문장 예비 실행

**버그 발견 (실제 Qwen 파이프라인 첫 실행에서 즉시 드러남)**: `QwenAgent.run()`이 `record.unresolved_errors`가 빈 리스트인 경우(=`validate_initial`의 결정적 검증 실패로 MQM을 아예 안 돌리고 `HUMAN_REVIEW_REQUIRED`가 된 경우)를 "오류 없음=해결됨"으로 오판해서 **아무 것도 안 하고 `AWAITING_HUMAN_APPROVAL`로 잘못 승인**해버림. 숫자 불일치라는 실제 실패 사유를 조용히 덮어쓰는 심각한 버그. `agent.py`의 진입 가드에 `or not record.unresolved_errors` 조건 추가로 수정, `tests/test_agent.py::test_agent_does_not_touch_record_with_empty_unresolved_errors`로 회귀 방지.

**평가용 20문장 중 5개(id 889/883/806/969/938)로 예비 실행** (TM+용어집+DNE 적용, `--agent --verbose`):

| id | 고정 Workflow 결과 | Agent 개입 결과 | 비고 |
|---|---|---|---|
| 889 | HUMAN_REVIEW_REQUIRED (MQM 전 단계, 숫자검증 실패) | 변화 없음(정상 — 처리할 오류 없어서 스킵) | "2~3km" 범위 표현 오탐, 위 스모크 테스트와 동일 유형 |
| 883 | HUMAN_REVIEW_REQUIRED (MQM 전 단계, 숫자검증 실패) | 변화 없음(정상) | "지난 20년" 숫자 매칭 실패 |
| 806 | HUMAN_REVIEW_REQUIRED (fluency 2회 실패) | **변화 없음** — Agent가 accuracy→human_review 순으로 골랐지만 accuracy 카테고리엔 실제 미해결 오류가 없어 스킵됨 | 아래 한계 참고 |
| 969 | HUMAN_REVIEW_REQUIRED (accuracy 2회 실패) | 변화 없음 — Agent가 1회 만에 human_review 선택 | 정직한 포기 판단(타당해 보임: "도로망 외부"라는 구조적 의미 차이는 단어 치환으로 해결 안 됨) |
| 938 | HUMAN_REVIEW_REQUIRED (v1→v2 채택 후 fluency 잔여 1건, 2회 시도 실패) | **변화 없음** — Agent가 terminology를 2번 골랐지만 둘 다 미해결 오류 없어 스킵 | 아래 한계 참고 |

**결론 (있는 그대로 보고 — Agent가 불리해도 숨기지 않음)**: 이 5문장에서 Qwen Agent 계층은 **단 한 건도 추가로 해결하지 못함**. 순수 토큰/시간 비용만 추가(총 20회 Ollama 호출, 90초).

**발견된 한계 (Planner Chain의 근본적 문제)**: id 806, 938에서 Planner가 고른 전략(`accuracy`, `terminology`)이 실제 MQM 미해결 오류 목록에 없는 카테고리였음 — LLM이 "이건 사실 accuracy/terminology 문제야"라고 그럴듯하게 설명하지만, 그 카테고리의 오류가 MQM 재평가에서 실제로 감지된 적이 없어서 `selected`가 비어 코드가 그냥 건너뜀(크래시는 안 나지만 예산만 소모). 즉 **Planner가 실제 감지된 오류에 근거하지 않고 카테고리를 제안하는 경향**이 있음 — "기존 우선순위는 참고하되 실제 근거가 있을 때만 전략을 변경"이라는 요구사항을 프롬프트 지시만으로는 완전히 지키지 못하고 있다는 뜻. 다음 개선 후보: planner 프롬프트에 "선택한 strategy는 반드시 아래 남은 오류 목록의 category 중 하나여야 한다"는 제약을 명시하거나, 구조화 출력 스키마 자체에서 `strategy`를 `unresolved_errors`의 category 집합으로 제한(현재는 6개 고정 Literal + human_review).

이 발견은 verbose TXT 로그(`reports/test_logs/test_20260922_121641.txt`)에 원문 그대로 남아있음 — Agent의 판단 근거(reasoning)를 그대로 볼 수 있어 이런 한계를 바로 잡아낼 수 있었음(로깅 기능의 실제 가치 확인).

## 다음 실험 (예정, 아직 미실행)

**Baseline 1 (본 규모)**: split=dev, 4개 언어(Japanese/Italian/French/German) × 3문장(seed=42) = 12쌍. 목적: 카테고리별 accept/reject 집계, 언어별 chrF A vs B 차이 확인. **미실행 사유**: 옆 동시 작업 세션(peer `3-l10n-ai-assistant-4b`)의 발열 부담으로 Ollama 호출 작업을 사용자 요청에 따라 일시 중단함. peer가 idle이 되면 재개.

프롬프트 실제 변경은 Baseline 1 결과를 본 뒤, 그 결과에서 나온 구체적 실패 사례를 근거로 시작한다 (섹션 6의 5가지 실패 유형 중 어느 것이 실제로 관찰되는지 먼저 파악).
