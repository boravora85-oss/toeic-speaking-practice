import csv
import io
import random
import re
import time
from difflib import SequenceMatcher
from io import BytesIO

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from streamlit_mic_recorder import speech_to_text


# =========================================================
# 1. 문제 데이터
# =========================================================
QUESTION_BANK = [
    {
        "part": "Part 3",
        "topic": "Shopping",
        "time_limit_sec": 30,
        "korean": "나는 온라인 쇼핑을 더 선호한다. 왜냐하면 편리하고 시간을 절약할 수 있기 때문이다.",
        "english": "I prefer shopping online because it is convenient and saves time.",
    },
    {
        "part": "Part 3",
        "topic": "Eating out",
        "time_limit_sec": 30,
        "korean": "나는 보통 주말에 가족과 외식을 한다. 우리는 다양한 음식을 먹을 수 있어서 외식을 좋아한다.",
        "english": "I usually eat out with my family on weekends because we can enjoy many kinds of food.",
    },
    {
        "part": "Part 3",
        "topic": "Travel",
        "time_limit_sec": 30,
        "korean": "나는 다른 사람들과 여행하는 것을 선호한다. 왜냐하면 같은 추억을 공유할 수 있기 때문이다.",
        "english": "I prefer traveling with other people because I can share the same memories with them.",
    },
    {
        "part": "Part 3",
        "topic": "Free time",
        "time_limit_sec": 30,
        "korean": "나는 여가 시간에 산책하는 것을 좋아한다. 스트레스를 줄이고 기분 전환에 도움이 된다.",
        "english": "I like taking a walk in my free time because it reduces stress and refreshes my mind.",
    },
    {
        "part": "Part 3",
        "topic": "Family",
        "time_limit_sec": 30,
        "korean": "나는 보통 주말에 가족과 시간을 보낸다. 가족과 이야기하면 마음이 편해진다.",
        "english": "I usually spend time with my family on weekends because talking with them makes me feel relaxed.",
    },
    {
        "part": "Part 3",
        "topic": "Exercise",
        "time_limit_sec": 30,
        "korean": "나는 건강을 위해 일주일에 두세 번 운동한다. 운동은 스트레스를 줄이는 데 도움이 된다.",
        "english": "I exercise two or three times a week because it helps me reduce stress.",
    },
    {
        "part": "Part 3",
        "topic": "Movies",
        "time_limit_sec": 30,
        "korean": "나는 집에서 영화를 보는 것을 선호한다. 편안하고 비용도 절약할 수 있기 때문이다.",
        "english": "I prefer watching movies at home because it is comfortable and saves money.",
    },
    {
        "part": "Part 3",
        "topic": "Restaurant",
        "time_limit_sec": 30,
        "korean": "나는 조용한 식당을 선호한다. 친구들과 편하게 대화할 수 있기 때문이다.",
        "english": "I prefer quiet restaurants because I can talk with my friends comfortably.",
    },
    {
        "part": "Part 5",
        "topic": "Opinion",
        "time_limit_sec": 60,
        "korean": "나는 이 의견에 동의한다. 왜냐하면 이것은 사람들에게 더 많은 기회를 줄 수 있기 때문이다.",
        "english": "I agree with this opinion because it can give people more opportunities.",
    },
    {
        "part": "Part 5",
        "topic": "Work",
        "time_limit_sec": 60,
        "korean": "나는 재택근무가 좋은 선택이라고 생각한다. 시간을 절약하고 일과 삶의 균형을 지킬 수 있기 때문이다.",
        "english": "I think working from home is a good option because it saves time and helps people keep a work-life balance.",
    },
]


# =========================================================
# 2. 페이지 설정
# =========================================================
st.set_page_config(
    page_title="나만의 토익스피킹 연습 앱",
    page_icon="🎙️",
    layout="centered",
)


# =========================================================
# 3. 스타일
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 720px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .app-title {
        text-align: center;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .app-subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    .question-card {
        border: 1px solid #e5e7eb;
        border-radius: 24px;
        padding: 28px;
        background: #ffffff;
        box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
        margin-bottom: 18px;
    }

    .small-label {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #eff6ff;
        color: #2563eb;
        font-size: 0.82rem;
        font-weight: 700;
        margin-right: 6px;
    }

    .korean-sentence {
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1.55;
        color: #111827;
        margin-top: 18px;
        margin-bottom: 12px;
    }

    .hint-text {
        color: #6b7280;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    .result-card {
        border: 1px solid #e5e7eb;
        border-radius: 24px;
        padding: 24px;
        background: #f9fafb;
        margin-top: 12px;
    }

    .answer-box {
        border-radius: 16px;
        padding: 16px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        margin-bottom: 12px;
    }

    .center-text {
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 4. 보조 함수
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


@st.cache_data(show_spinner=False)
def make_tts_audio_bytes(text: str) -> bytes:
    fp = BytesIO()
    tts = gTTS(text=text, lang="en", slow=False)
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()


def make_result_id() -> str:
    return str(int(time.time() * 1000))


def get_score_message(score: int, within_time: bool) -> tuple[str, str]:
    if not within_time:
        return "시간 초과", "시간 안에 말하는 연습이 필요합니다."

    if score >= 85:
        return "훌륭해요", "모범답안과 매우 비슷하게 말했습니다."
    elif score >= 70:
        return "좋아요", "핵심 표현은 잘 말했습니다. 조금만 더 다듬으면 됩니다."
    elif score >= 50:
        return "괜찮아요", "문장의 큰 방향은 맞습니다. 모범문장을 듣고 다시 따라 해보세요."
    else:
        return "다시 연습해요", "이번 문장은 오답노트에 넣고 반복 연습하는 게 좋습니다."


def make_review_csv() -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Part",
            "Topic",
            "Korean",
            "Model Answer",
            "My Answer",
            "Score",
            "Within Time",
            "Duration Seconds",
        ]
    )

    for note in st.session_state.review_notes:
        writer.writerow(
            [
                note.get("part", ""),
                note.get("topic", ""),
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
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 16px;
        background: #ffffff;
        margin-bottom: 14px;
        font-family: Arial, sans-serif;
    ">
        <div style="font-size: 20px; font-weight: 800; margin-bottom: 10px;">
            ⏱️ 남은 시간 <span id="countdown">--</span>
        </div>

        <div style="
            width: 100%;
            height: 16px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
        ">
            <div id="bar" style="
                height: 16px;
                width: 100%;
                background: #22c55e;
                border-radius: 999px;
                transition: width 0.2s linear, background 0.2s linear;
            "></div>
        </div>

        <div id="status" style="font-size: 13px; color: #6b7280; margin-top: 8px;">
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
                bar.style.background = "#f97316";
                status.innerText = "마무리하세요. 시간이 거의 끝났습니다.";
            }}

            if (seconds <= 0) {{
                bar.style.background = "#ef4444";
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
def reset_current_answer():
    st.session_state.phase = "ready"
    st.session_state.answer_input = ""
    st.session_state.exam_start_time = None
    st.session_state.exam_end_time = None
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.current_result = None
    st.session_state.recorder_key_number += 1


def start_new_session():
    questions = QUESTION_BANK.copy()
    random.shuffle(questions)

    st.session_state.session_questions = questions
    st.session_state.current_index = 0
    st.session_state.phase = "ready"
    st.session_state.answer_input = ""
    st.session_state.exam_start_time = None
    st.session_state.exam_end_time = None
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.current_result = None
    st.session_state.session_results = []
    st.session_state.recorder_key_number = st.session_state.get("recorder_key_number", 0) + 1


def initialize_state():
    if "review_notes" not in st.session_state:
        st.session_state.review_notes = []

    if "recorder_key_number" not in st.session_state:
        st.session_state.recorder_key_number = 0

    if "session_questions" not in st.session_state:
        start_new_session()


def get_current_question():
    return st.session_state.session_questions[st.session_state.current_index]


def start_answering():
    current = get_current_question()
    now = time.time()

    st.session_state.phase = "answering"
    st.session_state.answer_input = ""
    st.session_state.exam_start_time = now
    st.session_state.exam_end_time = now + current["time_limit_sec"]
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.current_result = None
    st.session_state.recorder_key_number += 1


def score_current_answer():
    current = get_current_question()
    user_answer = st.session_state.answer_input.strip()

    if not user_answer:
        st.warning("먼저 영어로 답변하거나 문장을 입력해 주세요.")
        return

    now = time.time()

    if st.session_state.answer_received_at is not None:
        check_time = st.session_state.answer_received_at
    else:
        check_time = now

    if st.session_state.exam_end_time is not None:
        within_time = check_time <= st.session_state.exam_end_time
    else:
        within_time = True

    if st.session_state.answer_duration_sec is not None:
        duration_sec = st.session_state.answer_duration_sec
    elif st.session_state.exam_start_time is not None:
        duration_sec = round(now - st.session_state.exam_start_time, 1)
    else:
        duration_sec = None

    score = calculate_similarity(user_answer, current["english"])

    result = {
        "id": make_result_id(),
        "part": current["part"],
        "topic": current["topic"],
        "korean": current["korean"],
        "model_answer": current["english"],
        "user_answer": user_answer,
        "score": score,
        "within_time": within_time,
        "duration_sec": duration_sec,
        "time_limit_sec": current["time_limit_sec"],
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

total_questions = len(st.session_state.session_questions)
current_number = st.session_state.current_index + 1

st.markdown('<div class="app-title">🎙️ 토익스피킹 카드 연습</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">한 문장씩 말하고, 듣고, 저장하면서 연습하세요</div>',
    unsafe_allow_html=True,
)


# =========================================================
# 7. 사이드바: 오답노트
# =========================================================
with st.sidebar:
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

        for idx, note in enumerate(st.session_state.review_notes, start=1):
            with st.expander(f"{idx}. {note['topic']} / {note['score']}점"):
                st.write(f"**KR:** {note['korean']}")
                st.write(f"**모범:** {note['model_answer']}")
                st.write(f"**내 답변:** {note['user_answer']}")

                if st.button(
                    "삭제",
                    key=f"delete_review_{note['id']}",
                    use_container_width=True,
                ):
                    remove_review_note(note["id"])
                    st.rerun()

    st.divider()

    if st.button("🔁 새 세션 시작", use_container_width=True):
        start_new_session()
        st.rerun()


# =========================================================
# 8. 진행률
# =========================================================
if st.session_state.phase != "finished":
    progress_value = st.session_state.current_index / total_questions
    st.progress(progress_value)

    st.markdown(
        f"""
        <div class="center-text">
            <b>{current_number} / {total_questions}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 9. 완료 화면
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

    st.markdown(
        f"""
        <div class="question-card center-text">
            <div style="font-size: 3rem;">🏁</div>
            <h2>오늘의 연습 완료!</h2>
            <p class="hint-text">한 세션을 끝까지 진행했습니다.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
# 10. 현재 문제 카드
# =========================================================
current = get_current_question()

st.markdown(
    f"""
    <div class="question-card">
        <span class="small-label">{current['part']}</span>
        <span class="small-label">{current['topic']}</span>
        <span class="small-label">{current['time_limit_sec']}초</span>

        <div class="korean-sentence">
            {current['korean']}
        </div>

        <div class="hint-text">
            위 문장을 영어로 자연스럽게 말해보세요.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 11. READY 단계
# =========================================================
if st.session_state.phase == "ready":
    st.markdown("### 준비되면 시작하세요")

    st.write("버튼을 누르면 제한시간이 시작됩니다.")

    if st.button("▶️ 시작하기", use_container_width=True):
        start_answering()
        st.rerun()

    col_skip_1, col_skip_2 = st.columns(2)

    with col_skip_1:
        if st.button("⏭️ 이 문장 건너뛰기", use_container_width=True):
            go_next_question()
            st.rerun()

    with col_skip_2:
        if st.button("🔄 문장 다시 섞기", use_container_width=True):
            start_new_session()
            st.rerun()


# =========================================================
# 12. ANSWERING 단계
# =========================================================
elif st.session_state.phase == "answering":
    render_countdown_timer(
        total_seconds=current["time_limit_sec"],
        end_time=st.session_state.exam_end_time,
    )

    st.markdown("### 영어로 답변하세요")

    spoken_text = speech_to_text(
        language="en",
        start_prompt="🎙️ 녹음 시작",
        stop_prompt="⏹️ 녹음 종료",
        just_once=True,
        use_container_width=True,
        key=f"toeic_stt_{st.session_state.recorder_key_number}",
    )

    if spoken_text:
        received_at = time.time()

        st.session_state.answer_input = spoken_text
        st.session_state.answer_received_at = received_at

        if st.session_state.exam_start_time:
            st.session_state.answer_duration_sec = round(
                received_at - st.session_state.exam_start_time,
                1,
            )

        if st.session_state.exam_end_time:
            st.session_state.answer_within_time = received_at <= st.session_state.exam_end_time
        else:
            st.session_state.answer_within_time = True

        if st.session_state.answer_within_time:
            st.success("답변이 인식되었습니다. 시간 안에 들어왔습니다.")
        else:
            st.error("답변은 인식되었지만 제한시간을 초과했습니다.")

    st.text_area(
        "내 답변",
        key="answer_input",
        height=110,
        placeholder="마이크로 말하면 여기에 영어 문장이 들어옵니다. 필요하면 직접 수정해도 됩니다.",
    )

    if st.session_state.answer_duration_sec is not None:
        st.caption(f"답변 인식 시점: 시작 후 약 {st.session_state.answer_duration_sec}초")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("✅ 채점하기", use_container_width=True):
            score_current_answer()
            st.rerun()

    with col_b:
        if st.button("↩️ 다시 말하기", use_container_width=True):
            start_answering()
            st.rerun()


# =========================================================
# 13. SCORED 단계
# =========================================================
elif st.session_state.phase == "scored":
    result = st.session_state.current_result

    title, message = get_score_message(
        result["score"],
        result["within_time"],
    )

    st.markdown(
        f"""
        <div class="result-card center-text">
            <div style="font-size: 2.6rem;">🎯</div>
            <h2>{title}</h2>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_score_1, col_score_2 = st.columns(2)

    with col_score_1:
        st.metric("점수", f"{result['score']}점 / 100점")

    with col_score_2:
        if result["within_time"]:
            st.metric("시간", "시간 내 답변")
        else:
            st.metric("시간", "시간 초과")

    if result["duration_sec"] is not None:
        st.caption(f"소요 시간: 약 {result['duration_sec']}초 / 제한 {result['time_limit_sec']}초")

    st.markdown("### 답변 비교")

    st.markdown(
        f"""
        <div class="answer-box">
            <b>🗣️ 내 답변</b><br>
            {result['user_answer']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="answer-box">
            <b>✅ 모범 답안</b><br>
            {result['model_answer']}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🔊 모범 문장 듣기")

    try:
        audio_bytes = make_tts_audio_bytes(result["model_answer"])
        st.audio(audio_bytes, format="audio/mp3")
    except Exception:
        st.warning("모범 문장 음성을 불러오지 못했습니다. 인터넷 연결 상태를 확인해 주세요.")

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
        if st.button("🔁 같은 문장 다시하기", use_container_width=True):
            reset_current_answer()
            st.rerun()

    with col_next_2:
        if st.button("다음 문장 →", use_container_width=True):
            go_next_question()
            st.rerun()


# =========================================================
# 14. 하단 안내
# =========================================================
st.caption(
    "현재 점수는 AI 채점이 아니라 모범답안과의 문장 유사도입니다. 다음 단계에서 Gemini API를 붙이면 실제 피드백형 채점으로 확장할 수 있습니다."
)
