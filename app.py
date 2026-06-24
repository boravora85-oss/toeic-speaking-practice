import csv
import io
import random
import re
import time
from difflib import SequenceMatcher
from io import BytesIO
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text


# =========================================================
# 1. 페이지 설정
# =========================================================
st.set_page_config(
    page_title="토익스피킹 카드 연습",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# =========================================================
# 2. 듀오링고형 모바일 스타일
# =========================================================
st.markdown(
    """
<style>
.stApp {
    background-color: #111f22;
    color: #f4f7f8;
}

.block-container {
    max-width: 760px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

h1, h2, h3, h4, p, span, label {
    color: #f4f7f8 !important;
}

div.stButton > button {
    width: 100%;
    border-radius: 18px;
    min-height: 3.4rem;
    font-size: 1.1rem;
    font-weight: 800;
    border: 2px solid #42535a;
    background-color: #152429;
    color: #70c8ff;
}

div.stButton > button:hover {
    border-color: #70c8ff;
    color: #ffffff;
}

div.stButton > button:disabled {
    background-color: #3b4a50;
    color: #172126;
    border-color: #3b4a50;
}

div[data-testid="stTextArea"] textarea {
    background-color: #1c2b30 !important;
    color: #f4f7f8 !important;
    border: 3px solid #42535a !important;
    border-radius: 24px !important;
    min-height: 150px !important;
    font-size: 1.15rem !important;
    line-height: 1.55 !important;
}

div[data-testid="stTextArea"] textarea:disabled {
    background-color: #1c2b30 !important;
    color: #f4f7f8 !important;
    opacity: 1 !important;
    -webkit-text-fill-color: #f4f7f8 !important;
}

div[data-testid="stTextArea"] textarea::placeholder {
    color: #6f7f86 !important;
    opacity: 1 !important;
}

div[data-testid="stProgress"] > div > div > div {
    background-color: #9be24e;
}

div[data-testid="stMetric"] {
    background-color: #17282d;
    border: 1px solid #34464d;
    border-radius: 18px;
    padding: 12px;
}

section[data-testid="stSidebar"] {
    background-color: #0f1a1d;
}

.stAlert {
    border-radius: 18px;
}

[data-testid="stCaptionContainer"] {
    color: #a9b6bb !important;
}

.card-box {
    background-color: #152429;
    border: 2px solid #34464d;
    border-radius: 26px;
    padding: 22px;
    margin: 16px 0;
}

.korean-prompt {
    font-size: 1.55rem;
    font-weight: 800;
    line-height: 1.55;
    color: #f4f7f8;
}

.sub-text {
    color: #a9b6bb;
    font-size: 1rem;
}

.heart-line {
    font-size: 2rem;
    letter-spacing: 0.25rem;
    text-align: right;
}

.close-x {
    font-size: 2.6rem;
    font-weight: 900;
    color: #6f7f86;
}

.big-title {
    font-size: 2.15rem;
    font-weight: 900;
    line-height: 1.25;
    margin-top: 1rem;
    margin-bottom: 1rem;
}

.answer-placeholder {
    border: 3px solid #42535a;
    border-radius: 28px;
    min-height: 170px;
    padding: 28px;
    color: #6f7f86;
    font-size: 1.35rem;
    font-weight: 800;
    background-color: #1c2b30;
}

.result-title {
    font-size: 2.1rem;
    font-weight: 900;
    margin-bottom: 0.5rem;
}

.model-answer {
    background-color: #1c2b30;
    border: 2px solid #42535a;
    border-radius: 22px;
    padding: 18px;
    color: #f4f7f8;
    font-size: 1.1rem;
    line-height: 1.6;
}
</style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 3. CSV 문제은행 읽기
# =========================================================
REQUIRED_COLUMNS = ["part", "category", "korean", "english", "time_limit_sec"]


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).replace("\ufeff", "").strip()


@st.cache_data(show_spinner=False)
def load_questions_from_csv(csv_path: str = "questions.csv") -> tuple[list[dict], list[str]]:
    path = Path(csv_path)
    errors = []

    if not path.exists():
        return [], [f"{csv_path} 파일을 찾을 수 없습니다. app.py와 같은 폴더에 questions.csv를 넣어주세요."]

    questions = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            if reader.fieldnames is None:
                return [], ["CSV 파일 첫 줄에 컬럼명이 없습니다."]

            fieldnames = [clean_text(name) for name in reader.fieldnames]
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in fieldnames]

            if missing_columns:
                return [], [
                    "CSV 컬럼명이 맞지 않습니다.",
                    f"필요한 컬럼: {REQUIRED_COLUMNS}",
                    f"현재 컬럼: {fieldnames}",
                    f"누락된 컬럼: {missing_columns}",
                ]

            for row_number, row in enumerate(reader, start=2):
                if None in row:
                    errors.append(
                        f"{row_number}행: 쉼표 때문에 컬럼이 깨졌을 수 있습니다. "
                        "영어/한국어 문장 안에 쉼표가 있으면 큰따옴표로 감싸야 합니다."
                    )
                    continue

                part = clean_text(row.get("part"))
                category = clean_text(row.get("category"))
                korean = clean_text(row.get("korean"))
                english = clean_text(row.get("english"))
                time_limit_raw = clean_text(row.get("time_limit_sec"))

                if not part or not category or not korean or not english:
                    errors.append(f"{row_number}행: part/category/korean/english 중 빈 값이 있습니다.")
                    continue

                try:
                    time_limit_sec = int(time_limit_raw)
                except ValueError:
                    time_limit_sec = 60 if part == "Part 5" else 30
                    errors.append(
                        f"{row_number}행: time_limit_sec 값이 숫자가 아니어서 {time_limit_sec}초로 자동 보정했습니다."
                    )

                questions.append(
                    {
                        "part": part,
                        "category": category,
                        "korean": korean,
                        "english": english,
                        "time_limit_sec": time_limit_sec,
                    }
                )

    except UnicodeDecodeError:
        return [], ["CSV 파일 인코딩 문제입니다. questions.csv를 UTF-8 형식으로 저장해 주세요."]
    except Exception as e:
        return [], [f"CSV를 읽는 중 오류가 발생했습니다: {e}"]

    if not questions:
        errors.append("정상적으로 읽힌 문제가 없습니다. questions.csv 내용을 확인해 주세요.")

    return questions, errors


# =========================================================
# 4. 채점 / TTS 함수
# =========================================================
def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_similarity(user_answer: str, model_answer: str) -> int:
    user_clean = normalize_text(user_answer)
    model_clean = normalize_text(model_answer)

    if not user_clean:
        return 0

    ratio = SequenceMatcher(None, user_clean, model_clean).ratio()
    return round(ratio * 100)


def get_score_message(score: int, within_time: bool) -> tuple[str, str]:
    if not within_time:
        return "시간 초과", "제한시간 안에 답변을 마무리하는 연습이 필요합니다."

    if score >= 85:
        return "훌륭해요", "모범답안과 매우 비슷하게 말했습니다."
    elif score >= 70:
        return "좋아요", "핵심 표현은 잘 말했습니다. 조금만 더 다듬으면 됩니다."
    elif score >= 50:
        return "괜찮아요", "문장의 큰 방향은 맞습니다. 모범문장을 듣고 다시 따라 해보세요."
    else:
        return "다시 연습해요", "이번 문장은 오답노트에 넣고 반복 연습하는 것이 좋습니다."


@st.cache_data(show_spinner=False)
def make_korean_tts_audio_bytes(text: str) -> bytes:
    fp = BytesIO()
    tts = gTTS(text=text, lang="ko", slow=False)
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()


@st.cache_data(show_spinner=False)
def make_english_tts_audio_bytes(text: str) -> bytes:
    fp = BytesIO()
    tts = gTTS(text=text, lang="en", slow=False)
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()


def make_result_id() -> str:
    return str(int(time.time() * 1000))


def make_review_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Part",
            "Category",
            "Korean",
            "Model Answer",
            "My Hidden Answer",
            "Score",
            "Within Time",
            "Duration Seconds",
        ]
    )

    for note in st.session_state.review_notes:
        writer.writerow(
            [
                note.get("part", ""),
                note.get("category", ""),
                note.get("korean", ""),
                note.get("model_answer", ""),
                note.get("user_answer", ""),
                note.get("score", ""),
                "Y" if note.get("within_time") else "N",
                note.get("duration_sec", ""),
            ]
        )

    return "\ufeff" + output.getvalue()


def render_countdown_timer(total_seconds: int, end_time: float):
    end_time_ms = int(end_time * 1000)
    total_ms = int(total_seconds * 1000)

    html = f"""
    <div style="
        border: 2px solid #42535a;
        border-radius: 18px;
        padding: 16px;
        background: #1c2b30;
        margin-bottom: 14px;
        font-family: Arial, sans-serif;
        color: #f4f7f8;
    ">
        <div style="font-size: 20px; font-weight: 800; margin-bottom: 10px;">
            ⏱️ 남은 시간 <span id="countdown">--</span>
        </div>

        <div style="
            width: 100%;
            height: 18px;
            background: #34464d;
            border-radius: 999px;
            overflow: hidden;
        ">
            <div id="bar" style="
                height: 18px;
                width: 100%;
                background: #9be24e;
                border-radius: 999px;
                transition: width 0.2s linear, background 0.2s linear;
            "></div>
        </div>

        <div id="status" style="font-size: 13px; color: #a9b6bb; margin-top: 8px;">
            제한시간 안에 답변을 마치고 녹음을 종료하세요.
        </div>
    </div>

    <script>
        const endTime = {end_time_ms};
        const totalTime = {total_ms};

        function updateTimer() {{
            const now = Date.now();
            const remaining = Math.max(0, endTime - now);
            const seconds = Math.ceil(remaining / 1000);
            const percent = Math.max(0, Math.min(100, (remaining / totalTime) * 100));

            const countdown = document.getElementById("countdown");
            const bar = document.getElementById("bar");
            const status = document.getElementById("status");

            countdown.innerText = seconds + "초";
            bar.style.width = percent + "%";

            if (seconds <= 5 && seconds > 0) {{
                bar.style.background = "#ffb020";
                status.innerText = "마무리하세요. 시간이 거의 끝났습니다.";
            }}

            if (seconds <= 0) {{
                bar.style.background = "#ff4d4f";
                status.innerText = "시간 종료! 녹음을 종료하고 결과를 확인하세요.";
            }}
        }}

        updateTimer();
        setInterval(updateTimer, 250);
    </script>
    """

    components.html(html, height=118)


# =========================================================
# 5. 상태 관리
# =========================================================
def initialize_state():
    defaults = {
        "review_notes": [],
        "recorder_key_number": 0,
        "selected_parts": ["Part 3", "Part 5"],
        "selected_categories": [],
        "all_questions": [],
        "session_questions": [],
        "phase": "ready",
        "current_index": 0,
        "session_results": [],
        "hidden_answer": "",
        "current_result": None,
        "exam_start_time": None,
        "exam_end_time": None,
        "answer_received_at": None,
        "answer_duration_sec": None,
        "answer_within_time": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def build_filtered_questions(all_questions: list[dict]) -> list[dict]:
    selected_parts = st.session_state.get("selected_parts", ["Part 3", "Part 5"])
    selected_categories = st.session_state.get("selected_categories", [])

    filtered = [q for q in all_questions if q["part"] in selected_parts]

    if selected_categories:
        filtered = [q for q in filtered if q["category"] in selected_categories]

    return filtered


def start_new_session():
    all_questions = st.session_state.all_questions
    questions = build_filtered_questions(all_questions)

    if not questions:
        st.session_state.session_questions = []
        st.session_state.phase = "empty"
        return

    random.shuffle(questions)

    st.session_state.session_questions = questions
    st.session_state.current_index = 0
    st.session_state.phase = "ready"
    st.session_state.hidden_answer = ""
    st.session_state.current_result = None
    st.session_state.session_results = []
    st.session_state.exam_start_time = None
    st.session_state.exam_end_time = None
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.recorder_key_number += 1


def reset_current_answer():
    st.session_state.phase = "ready"
    st.session_state.hidden_answer = ""
    st.session_state.current_result = None
    st.session_state.exam_start_time = None
    st.session_state.exam_end_time = None
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.recorder_key_number += 1


def get_current_question():
    return st.session_state.session_questions[st.session_state.current_index]


def start_answering():
    current = get_current_question()
    now = time.time()

    st.session_state.phase = "answering"
    st.session_state.hidden_answer = ""
    st.session_state.current_result = None
    st.session_state.exam_start_time = now
    st.session_state.exam_end_time = now + current["time_limit_sec"]
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.recorder_key_number += 1


def score_answer_automatically(spoken_text: str):
    current = get_current_question()
    user_answer = clean_text(spoken_text)

    now = time.time()
    received_at = now

    st.session_state.hidden_answer = user_answer
    st.session_state.answer_received_at = received_at

    if st.session_state.exam_start_time:
        duration_sec = round(received_at - st.session_state.exam_start_time, 1)
    else:
        duration_sec = None

    if st.session_state.exam_end_time:
        within_time = received_at <= st.session_state.exam_end_time
    else:
        within_time = True

    score = calculate_similarity(user_answer, current["english"])
    title, message = get_score_message(score, within_time)

    result = {
        "id": make_result_id(),
        "part": current["part"],
        "category": current["category"],
        "korean": current["korean"],
        "model_answer": current["english"],
        "user_answer": user_answer,
        "score": score,
        "within_time": within_time,
        "duration_sec": duration_sec,
        "time_limit_sec": current["time_limit_sec"],
        "feedback_title": title,
        "feedback_message": message,
    }

    st.session_state.current_result = result
    st.session_state.session_results.append(result)
    st.session_state.phase = "scored"


def go_next_question():
    if st.session_state.current_index >= len(st.session_state.session_questions) - 1:
        st.session_state.phase = "finished"
    else:
        st.session_state.current_index += 1
        reset_current_answer()


def is_in_review_notes(result_id: str) -> bool:
    return any(note["id"] == result_id for note in st.session_state.review_notes)


def add_review_note(result: dict):
    if result and not is_in_review_notes(result["id"]):
        st.session_state.review_notes.insert(0, result)


def remove_review_note(result_id: str):
    st.session_state.review_notes = [
        note for note in st.session_state.review_notes if note["id"] != result_id
    ]


# =========================================================
# 6. 앱 시작
# =========================================================
initialize_state()

loaded_questions, csv_errors = load_questions_from_csv("questions.csv")

if not loaded_questions:
    st.title("🎙️ 토익스피킹 카드 연습")
    st.error("questions.csv에서 문제를 불러오지 못했습니다.")
    for error in csv_errors:
        st.write(f"- {error}")
    st.stop()

st.session_state.all_questions = loaded_questions

if not st.session_state.session_questions:
    start_new_session()


# =========================================================
# 7. 사이드바 설정
# =========================================================
all_parts = sorted(set(q["part"] for q in st.session_state.all_questions))
all_categories = sorted(set(q["category"] for q in st.session_state.all_questions))

default_parts = [p for p in st.session_state.selected_parts if p in all_parts] or all_parts
default_categories = [
    c for c in st.session_state.selected_categories if c in all_categories
]

with st.sidebar:
    st.header("⚙️ 연습 설정")

    st.success(f"문제은행 로드 완료: {len(st.session_state.all_questions)}문장")

    selected_parts = st.multiselect(
        "Part 선택",
        options=all_parts,
        default=default_parts,
    )

    selected_categories = st.multiselect(
        "카테고리 선택",
        options=all_categories,
        default=default_categories,
        help="비워두면 전체 카테고리에서 출제됩니다.",
    )

    if st.button("설정 적용 후 새 세션 시작", use_container_width=True):
        st.session_state.selected_parts = selected_parts or all_parts
        st.session_state.selected_categories = selected_categories
        start_new_session()
        st.rerun()

    if csv_errors:
        with st.expander("CSV 경고 보기"):
            for error in csv_errors[:20]:
                st.write(f"- {error}")

    st.divider()

    st.header("⭐ 오답노트")

    if not st.session_state.review_notes:
        st.caption("아직 저장한 문장이 없습니다.")
    else:
        st.success(f"{len(st.session_state.review_notes)}개 저장됨")

        csv_data = make_review_csv()

        st.download_button(
            label="CSV 다운로드",
            data=csv_data,
            file_name="toeic_speaking_review_notes.csv",
            mime="text/csv",
            use_container_width=True,
        )

        show_hidden_answer = st.checkbox(
            "오답노트에서 내 인식 문장 보기",
            value=False,
        )

        for idx, note in enumerate(st.session_state.review_notes, start=1):
            with st.expander(f"{idx}. {note.get('category', '')} / {note['score']}점"):
                st.write(f"**KR:** {note['korean']}")
                st.write(f"**모범:** {note['model_answer']}")

                if show_hidden_answer:
                    st.write(f"**내 인식 문장:** {note.get('user_answer', '')}")

                if st.button(
                    "삭제",
                    key=f"delete_review_{note['id']}",
                    use_container_width=True,
                ):
                    remove_review_note(note["id"])
                    st.rerun()


# =========================================================
# 8. 빈 세션 처리
# =========================================================
if st.session_state.phase == "empty" or not st.session_state.session_questions:
    st.warning("선택한 조건에 맞는 문장이 없습니다. 왼쪽 설정에서 Part 또는 카테고리를 다시 선택해 주세요.")
    st.stop()


# =========================================================
# 9. 상단 진행 UI
# =========================================================
total_questions = len(st.session_state.session_questions)
current_number = st.session_state.current_index + 1
progress_value = st.session_state.current_index / total_questions

if st.session_state.phase != "finished":
    col_close, col_progress, col_hearts = st.columns([1, 3, 4])

    with col_close:
        if st.button("✕", key="top_close"):
            start_new_session()
            st.rerun()

    with col_progress:
        st.progress(progress_value)

    with col_hearts:
        st.markdown(
            '<div class="heart-line">🧡🧡🧡🧡🧡</div>',
            unsafe_allow_html=True,
        )


# =========================================================
# 10. 완료 화면
# =========================================================
if st.session_state.phase == "finished":
    results = st.session_state.session_results

    if results:
        avg_score = round(sum(r["score"] for r in results) / len(results))
        timeout_count = sum(1 for r in results if not r["within_time"])
        saved_count = len(st.session_state.review_notes)
    else:
        avg_score = 0
        timeout_count = 0
        saved_count = len(st.session_state.review_notes)

    st.markdown("## 🏁 오늘의 연습 완료")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("평균 점수", f"{avg_score}점")

    with col2:
        st.metric("연습 문장", f"{len(results)}개")

    with col3:
        st.metric("시간 초과", f"{timeout_count}개")

    st.info(f"현재 오답노트에는 {saved_count}개 문장이 저장되어 있습니다.")

    if st.button("🔁 다시 연습하기", use_container_width=True):
        start_new_session()
        st.rerun()

    st.stop()


# =========================================================
# 11. 현재 문제
# =========================================================
current = get_current_question()

st.caption(f"{current_number} / {total_questions} · {current['part']} · {current['category']} · {current['time_limit_sec']}초")

st.markdown('<div class="big-title">다음 문장을 영어로 말하세요</div>', unsafe_allow_html=True)

st.markdown(
    f"""
<div class="korean-prompt">
{current["korean"]}
</div>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 12. READY 단계
# =========================================================
if st.session_state.phase == "ready":
    st.markdown(
        """
<div class="answer-placeholder">
영어 답변 대기 중
</div>
""",
        unsafe_allow_html=True,
    )

    st.write("")
    st.write("")
    st.write("")

    if st.button("🎙️ 탭하여 말하기", use_container_width=True):
        start_answering()
        st.rerun()

    st.button("확인", disabled=True, use_container_width=True)

    with st.expander("다른 기능"):
        if st.button("⏭️ 이 문장 건너뛰기", use_container_width=True):
            go_next_question()
            st.rerun()

        if st.button("🔄 새 세션 시작", use_container_width=True):
            start_new_session()
            st.rerun()


# =========================================================
# 13. ANSWERING 단계
# =========================================================
elif st.session_state.phase == "answering":
    render_countdown_timer(
        total_seconds=current["time_limit_sec"],
        end_time=st.session_state.exam_end_time,
    )

    st.markdown(
        """
<div class="answer-placeholder">
듣고 있습니다.<br>답변을 마치면 녹음 종료를 누르세요.
</div>
""",
        unsafe_allow_html=True,
    )

    st.caption("녹음 종료 후 인식이 완료되면 자동으로 채점됩니다. 내가 말한 영어 문장은 기본 화면에 표시하지 않습니다.")

    spoken_text = speech_to_text(
        language="en",
        start_prompt="🎙️ 녹음 시작",
        stop_prompt="⏹️ 녹음 종료",
        just_once=True,
        use_container_width=True,
        key=f"toeic_stt_{st.session_state.recorder_key_number}",
    )

    if spoken_text:
        score_answer_automatically(spoken_text)
        st.rerun()

    if st.button("↩️ 다시 시작하기", use_container_width=True):
        start_answering()
        st.rerun()

    st.button("확인", disabled=True, use_container_width=True)


# =========================================================
# 14. SCORED 단계
# =========================================================
elif st.session_state.phase == "scored":
    result = st.session_state.current_result

    title = result["feedback_title"]
    message = result["feedback_message"]

    st.markdown(f'<div class="result-title">🎯 {result["score"]}점</div>', unsafe_allow_html=True)

    if result["within_time"]:
        st.success(f"{title} - {message}")
    else:
        st.error(f"{title} - {message}")

    if result["duration_sec"] is not None:
        st.caption(f"소요 시간: 약 {result['duration_sec']}초 / 제한 {result['time_limit_sec']}초")

    st.markdown("### 🔊 점수 안내 듣기")

    time_sentence = "제한시간 안에 답변했습니다." if result["within_time"] else "제한시간을 초과했습니다."

    korean_feedback_text = (
        f"점수는 {result['score']}점입니다. "
        f"{time_sentence} "
        f"{title}. {message} "
        f"이제 모범 답안을 듣고 따라 해보세요."
    )

    try:
        feedback_audio = make_korean_tts_audio_bytes(korean_feedback_text)
        st.audio(feedback_audio, format="audio/mp3")
    except Exception:
        st.warning("점수 안내 음성을 불러오지 못했습니다. 인터넷 연결 상태를 확인해 주세요.")

    st.markdown("### ✅ 모범 답안")

    st.markdown(
        f"""
<div class="model-answer">
{result["model_answer"]}
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### 🔊 모범 문장 듣기")

    try:
        model_audio = make_english_tts_audio_bytes(result["model_answer"])
        st.audio(model_audio, format="audio/mp3")
    except Exception:
        st.warning("모범 문장 음성을 불러오지 못했습니다. 인터넷 연결 상태를 확인해 주세요.")

    with st.expander("내가 말한 문장 확인하기"):
        st.caption("STT가 제대로 인식됐는지 확인하고 싶을 때만 열어보세요.")
        st.text_area(
            "내 인식 문장",
            value=result["user_answer"],
            height=100,
            disabled=True,
        )

    already_saved = is_in_review_notes(result["id"])

    review_checked = st.checkbox(
        "⭐ 이 문장을 오답노트에 저장하기",
        value=already_saved,
        key=f"review_checkbox_{result['id']}",
    )

    if review_checked:
        add_review_note(result)
        st.caption("오답노트에 저장되었습니다.")
    else:
        remove_review_note(result["id"])
        st.caption("오답노트에 저장하지 않았습니다.")

    col_next_1, col_next_2 = st.columns(2)

    with col_next_1:
        if st.button("🔁 다시하기", use_container_width=True):
            reset_current_answer()
            st.rerun()

    with col_next_2:
        if st.button("다음 문장 →", use_container_width=True):
            go_next_question()
            st.rerun()


# =========================================================
# 15. 하단 안내
# =========================================================
st.caption("문제은행은 questions.csv에서 불러옵니다. 현재 점수는 모범답안과의 문장 유사도 기준입니다.")
