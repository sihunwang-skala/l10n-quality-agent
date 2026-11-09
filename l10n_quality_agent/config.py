"""MVP 설정 상수."""

from pathlib import Path

# 프로젝트 루트 기준 데이터 경로 - flores_data.py, tm.py, terminology.py 등
# FLORES+와 파생 자료를 찾아야 하는 곳에서 경로를 하드코딩하지 않고 공유한다.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data" / "flores_plus"
FLORES_RAW_DIR = DATA_ROOT / "raw"
FLORES_PROCESSED_DIR = DATA_ROOT / "processed"
FLORES_RESOURCES_DIR = DATA_ROOT / "resources"
TM_DIR = FLORES_RESOURCES_DIR / "tm"
TERMINOLOGY_DIR = FLORES_RESOURCES_DIR / "terminology"
DNE_DIR = FLORES_RESOURCES_DIR / "dne"

MODEL_NAME = "qwen3.5:4b"
TEMPERATURE = 0
SEED = 42
# qwen3.5:4b는 기본 "thinking" 모드에서 JSON 본문을 내기 전에 숨겨진 추론
# 토큰을 수천 개씩 태운다. num_predict를 작게 두면 그 도중에 끊겨서 구조화
# 출력 파싱이 실패한다. 실측: reasoning on이면 MQM 호출 하나에 ~3200 토큰(88초)
# 쓰고도 못 끝냈고, off면 같은 호출이 ~400-900 토큰이면 끝난다.
REASONING = False
# 1536은 reasoning off 상태에서 오류 5개짜리 MQM 응답에 실측된 ~900 토큰보다
# 여유를 두면서도, 멈추거나 장황해지는 호출은 잘라내는 값이다.
NUM_PREDICT = 1536
# 한 Workflow 실행이 Ollama를 연속으로 여러 번 호출하므로, 기본 5분 unload로
# 매번 느리게 재로딩되지 않도록 모델을 메모리에 계속 띄워둔다.
KEEP_ALIVE = "30m"
MAX_ATTEMPTS_PER_CATEGORY = 2
MAX_TOTAL_ATTEMPTS = 12

PRIORITY = {
    "accuracy": 1,
    "terminology": 2,
    "spelling": 3,
    "grammar": 4,
    "style": 5,
    "fluency": 6,
}

PROMPT_VERSIONS = {
    "translation": "translation-v1",
    "mqm": "mqm-v1",
    "revision": "revision-v1",
}

# 지원하는 국가는 각각 언어 하나에 1:1로 대응해서, 국가 하나만 고르면
# TranslationRequest의 target_country와 target_language가 같이 채워진다.
# ui.py와 FLORES+ 평가 스크립트가 공유한다.
# "United States"/English는 FLORES+ Wikivoyage 실험(KO->EN 전용)을 위해
# 추가했다 - FLORES+ 영어 참조문은 *언어* 단위 번역으로 채점할 뿐, 미국
# 로케일에 특화됐다고 보는 건 아니다.
COUNTRY_LANGUAGE = {
    "United States": "English",
    "Japan": "Japanese",
    "Italy": "Italian",
    "France": "French",
    "Germany": "German",
}

