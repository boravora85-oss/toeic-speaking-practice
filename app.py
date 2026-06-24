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
# 1. 토익스피킹 연습용 문장 데이터
#    time_limit_sec: 실제 시험처럼 답변 시간을 제한하기 위한 값입니다.
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
        "part": "Part 5",
        "topic": "Opinion",
        "time_limit_sec": 60,
        "korean": "나는 이 의견에 동의한다. 왜냐하면 이것은 사람들에게 더 많은 기회를 줄 수 있기 때문이다.",
        "english": "I agree with this opinion because it can give people more opportunities.",
    },
]


# =========================================================
# 2. 페이지 기본 설정
# =========================================================
st.set_page_config(
    page_title="나만의 토익스피킹 연습 앱",
    page_icon="🎙️",
    layout="centered",
)


# =========================================================
# 3. 보조 함수
# =========================================================
def normalize_text(text: str) -> str:
    """문장 비교를 위해 소문자, 공백, 특수문자를 정리합니다."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_similarity(user_answer: str, model_answer: str) -> int:
    """사용자 답변과 모범 답안의 유사도를 0~100점으로 계산합니다."""
    user_clean = normalize_text(user_answer)
    model_clean = normalize_text(model_answer)

    if not user_clean:
        return 0

    ratio = SequenceMatcher(None, user_clean, model_clean).ratio()
    return round(ratio * 100)


def initialize_state():
    """앱에서 사용할 상태값을 초기화합니다."""
    if "recorder_key_number" not in st.session_state:
        st.session_state.recorder_key_number = 0

    if "current_question" not in st.session_state:
        st.session_state.current_question = random.choice(QUESTION_BANK)

    if "answer_input" not in st.session_state:
        st.session_state.answer_input = ""

    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if "similarity_score" not in st.session_state:
        st.session_state.similarity_score = None

    if "history" not in st.session_state:
        st.session_state.history = []

    if "review_notes" not in st.session_state:
        st.session_state.review_notes = []

    if "exam_started" not in st.session_state:
        st.session_state.exam_started = False

    if "exam_start_time" not in st.session_state:
        st.session_state.exam_start_time = None

    if "exam_end_time" not in st.session_state:
        st.session_state.exam_end_time = None

    if "answer_received_at" not in st.session_state:
        st.session_state.answer_received_at = None

    if "answer_duration_sec" not in st.session_state:
        st.session_state.answer_duration_sec = None

    if "answer_within_time" not in st.session_state:
        st.session_state.answer_within_time = None

    if "last_result" not in st.session_state:
        st.session_state.last_result = None


def reset_answer_state():
    """현재 문제의 답변 상태를 초기화합니다."""
    st.session_state.answer_input = ""
    st.session_state.submitted = False
    st.session_state.similarity_score = None
    st.session_state.exam_started = False
    st.session_state.exam_start_time = None
    st.session_state.exam_end_time = None
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.last_result = None
    st.session_state.recorder_key_number += 1


def pick_new_question():
    """새 문제를 랜덤으로 뽑습니다."""
    st.session_state.current_question = random.choice(QUESTION_BANK)
    reset_answer_state()


def start_exam_timer():
    """제한시간 타이머를 시작합니다."""
    current = st.session_state.current_question
    now = time.time()
    st.session_state.exam_started = True
    st.session_state.exam_start_time = now
    st.session_state.exam_end_time = now + current["time_limit_sec"]
    st.session_state.answer_received_at = None
    st.session_state.answer_duration_sec = None
    st.session_state.answer_within_time = None
    st.session_state.submitted = False
    st.session_state.similarity_score = None
    st.session_state.recorder_key_number += 1


def get_remaining_seconds() -> int:
    """남은 시간을 계산합니다."""
    if not st.session_state.exam_started or st.session_state.exam_end_time is None:
        return st.session_state.current_question["time_limit_sec"]

    remaining = int(st.session_state.exam_end_time - time.time())
    return max(0, remaining)


def render_countdown_timer(total_seconds: int, end_time: float):
    """브라우저 화면에서 움직이는 카운트다운 타이머를 보여줍니다."""
    end_time_ms = int(end_time * 1000)
    total_ms = int(total_seconds * 1000)

    html = f"""
    <div style="
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0 16px 0;
        background: #fafafa;
        font-family: Arial, sans-serif;
    ">
        <div style="font-size: 18px; font-weight: 700; margin-bottom: 8px;">
            ⏱️ 남은 시간: <span id="countdown">--</span>
        </div>
        <div style="
            width: 100%;
            height: 14px;
            background: #e5e7eb;
            border-radius: 999px;
            overflow: hidden;
        ">
            <div id="bar" style="
                height: 14px;
                width: 100%;
                background: #2563eb;
                border-radius: 999px;
                transition: width 0.2s linear, background 0.2s linear;
            "></div>
        </div>
        <div id="status" style="font-size: 13px; color: #666; margin-top: 8px;">
            시간 안에 답변을 마치고 녹음을 종료하세요.
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
                bar.style.background = "#dc2626";
                status.innerText = "시간 종료! 녹음을 종료하고 결과를 확인하세요.";
            }}
        }}

        updateTimer();
        setInterval(updateTimer, 250);
    </script>
    """

    components.html(html, height=120)


@st.cache_data(show_spinner=False)
def make_tts_audio_bytes(text: str) -> bytes:
    """모범 답안을 영어 음성 mp3로 변환합니다."""
    fp = BytesIO()
    tts = gTTS(text=text, lang="en", slow=False)
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp.read()


def make_result_id() -> str:
    """오답노트 저장용 고유 ID를 만듭니다."""
    return str(int(time.time() * 1000))


def is_in_review_notes(result_id: str) -> bool:
    """해당 결과가 복습노트에 이미 들어 있는지 확인합니다."""
    return any(note["id"] == result_id for note in st.session_state.review_notes)


def add_review_note(result: dict):
    """복습노트에 결과를 추가합니다."""
    if not result:
        return

    if not is_in_review_notes(result["id"]):
        st.session_state.review_notes.insert(0, result)


def remove_review_note(result_id: str):
    """복습노트에서 결과를 제거합니다."""
    st.session_state.review_notes = [
        note for note in st.session_state.review_notes if note["id"] != result_id
    ]


def make_review_csv() -> str:
    """복습노트를 CSV 문자열로 만듭니다."""
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

    # 엑셀에서 한글이 깨지지 않도록 BOM을 붙입니다.
    return "\ufeff" + output.getvalue()


# =========================================================
# 4. 앱 시작
# =========================================================
initialize_state()

st.title("🎙️ 나만의 토익스피킹 연습 앱")
st.caption("실전 시간 제한 + 음성 인식 + 모범답안 듣기 + 오답노트")

current = st.session_state.current_question


# =========================================================
# 5. 문제 영역
# =========================================================
with st.container(border=True):
    st.subheader("오늘의 문제")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**Part:** {current['part']}")

    with col2:
        st.write(f"**Topic:** {current['topic']}")

    with col3:
        st.write(f"**제한시간:** {current['time_limit_sec']}초")

    st.markdown("### KR 한국어 문장")
    st.info(current["korean"])


col_new_1, col_new_2 = st.columns(2)

with col_new_1:
    if st.button("🔄 새 문제 출제", use_container_width=True):
        pick_new_question()
        st.rerun()

with col_new_2:
    if st.button("🧹 현재 답변 초기화", use_container_width=True):
        reset_answer_state()
        st.rerun()


st.divider()


# =========================================================
# 6. 실전 녹음 영역
# =========================================================
st.subheader("1단계: 실전 시간 안에 영어로 답변하기")

if not st.session_state.exam_started:
    st.write("아래 버튼을 누르면 제한시간이 시작됩니다. 그다음 바로 녹음 버튼을 눌러 답변하세요.")

    if st.button("⏱️ 시험처럼 시작하기", use_container_width=True):
        start_exam_timer()
        st.rerun()

else:
    if not st.session_state.submitted:
        render_countdown_timer(
            total_seconds=current["time_limit_sec"],
            end_time=st.session_state.exam_end_time,
        )

    st.write("녹음 시작 버튼을 누르고 영어로 답변한 뒤, 제한시간 안에 녹음을 종료하세요.")

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
        else:
            st.session_state.answer_duration_sec = None

        if st.session_state.exam_end_time:
            st.session_state.answer_within_time = received_at <= st.session_state.exam_end_time
        else:
            st.session_state.answer_within_time = True

        st.session_state.submitted = False
        st.session_state.similarity_score = None

        if st.session_state.answer_within_time:
            st.success("음성 인식 완료! 제한시간 안에 답변이 들어왔습니다.")
        else:
            st.error("음성 인식은 되었지만 제한시간을 초과했습니다.")

st.text_area(
    "내 답변",
    key="answer_input",
    height=120,
    placeholder="마이크로 말하면 여기에 영어 문장이 자동으로 들어옵니다. 필요하면 직접 수정해도 됩니다.",
)

if st.session_state.answer_duration_sec is not None:
    st.caption(f"답변 인식 시점: 시작 후 약 {st.session_state.answer_duration_sec}초")


st.divider()


# =========================================================
# 7. 정답 확인 및 채점
# =========================================================
st.subheader("2단계: 점수 확인하기")

if st.button("✅ 정답 확인", use_container_width=True):
    user_answer = st.session_state.answer_input.strip()

    if not user_answer:
        st.warning("먼저 시험처럼 시작하고, 마이크로 답변하거나 영어 문장을 입력해 주세요.")
    else:
        st.session_state.submitted = True

        score = calculate_similarity(
            user_answer,
            current["english"],
        )

        st.session_state.similarity_score = score

        # 음성 인식 시점이 있으면 그 시점을 기준으로 시간 내 답변 여부 판단
        # 직접 타이핑한 경우에는 정답 확인 버튼을 누른 시간을 기준으로 판단
        if st.session_state.exam_started and st.session_state.exam_end_time:
            if st.session_state.answer_received_at is not None:
                within_time = st.session_state.answer_received_at <= st.session_state.exam_end_time
            else:
                within_time = time.time() <= st.session_state.exam_end_time
        else:
            within_time = True

        if st.session_state.answer_duration_sec is not None:
            duration_sec = st.session_state.answer_duration_sec
        elif st.session_state.exam_start_time is not None:
            duration_sec = round(time.time() - st.session_state.exam_start_time, 1)
        else:
            duration_sec = None

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

        st.session_state.last_result = result

        st.session_state.history.insert(0, result)
        st.session_state.history = st.session_state.history[:10]


if st.session_state.submitted and st.session_state.last_result:
    result = st.session_state.last_result
    score = result["score"]

    col_score_1, col_score_2 = st.columns(2)

    with col_score_1:
        st.metric("모범 답안과의 유사도", f"{score}점 / 100점")

    with col_score_2:
        if result["within_time"]:
            st.metric("시간 판정", "시간 내 답변")
        else:
            st.metric("시간 판정", "시간 초과")

    if not result["within_time"]:
        st.error("실전 모드 기준으로는 시간 초과입니다. 같은 문장을 다시 제한시간 안에 말해보세요.")
    elif score >= 85:
        st.success("좋습니다. 시간 안에 모범 답안과 매우 비슷하게 말했습니다.")
    elif score >= 65:
        st.info("괜찮습니다. 핵심 표현은 맞지만, 문장 구조를 조금 더 다듬으면 좋습니다.")
    else:
        st.warning("아직 차이가 있습니다. 모범 답안을 듣고 한 번 더 연습해보세요.")

    col_answer_1, col_answer_2 = st.columns(2)

    with col_answer_1:
        st.markdown("#### ✅ 모범 답안")
        st.write(result["model_answer"])

    with col_answer_2:
        st.markdown("#### 🗣️ 내 답변")
        st.write(result["user_answer"])

    st.markdown("#### 🔊 모범 문장 듣기")

    try:
        with st.spinner("모범 문장 음성을 만드는 중입니다..."):
            audio_bytes = make_tts_audio_bytes(result["model_answer"])
        st.audio(audio_bytes, format="audio/mp3")
    except Exception:
        st.warning("현재 모범 문장 음성을 불러오지 못했습니다. 인터넷 연결이나 gTTS 상태를 확인해 주세요.")

    st.markdown("#### ⭐ 오답노트 저장")

    already_checked = is_in_review_notes(result["id"])

    review_checked = st.checkbox(
        "이 문장을 복습노트에 보관하기",
        value=already_checked,
        key=f"review_check_{result['id']}",
    )

    if review_checked:
        add_review_note(result)
        st.caption("복습노트에 보관 중입니다.")
    else:
        remove_review_note(result["id"])
        st.caption("복습노트에 보관하지 않습니다.")

    with st.expander("복습 포인트 보기"):
        st.write("- 점수는 아직 AI 채점이 아니라 모범 답안과의 문장 유사도입니다.")
        st.write("- 제한시간 안에 말하는 습관을 만들기 위해 시간 초과 여부를 따로 표시합니다.")
        st.write("- 다음 단계에서 Gemini API를 붙이면 문법, 발음 추정, 자연스러운 표현까지 피드백할 수 있습니다.")


st.divider()


# =========================================================
# 8. 오답노트 영역
# =========================================================
st.subheader("3단계: 나만의 오답노트")

if not st.session_state.review_notes:
    st.info("아직 오답노트에 저장한 문장이 없습니다. 채점 후 '복습노트에 보관하기'를 체크해 보세요.")
else:
    st.success(f"현재 {len(st.session_state.review_notes)}개 문장이 오답노트에 저장되어 있습니다.")

    csv_data = make_review_csv()

    st.download_button(
        label="📥 오답노트 CSV 다운로드",
        data=csv_data,
        file_name="toeic_speaking_review_notes.csv",
        mime="text/csv",
        use_container_width=True,
    )

    for idx, note in enumerate(st.session_state.review_notes, start=1):
        with st.container(border=True):
            st.markdown(f"### {idx}. {note['part']} / {note['topic']}")

            col_note_1, col_note_2 = st.columns(2)

            with col_note_1:
                st.write(f"**점수:** {note['score']}점 / 100점")

            with col_note_2:
                if note["within_time"]:
                    st.write("**시간:** 시간 내 답변")
                else:
                    st.write("**시간:** 시간 초과")

            st.write(f"**KR:** {note['korean']}")
            st.write(f"**✅ 모범 답안:** {note['model_answer']}")
            st.write(f"**🗣️ 내 답변:** {note['user_answer']}")

            try:
                note_audio = make_tts_audio_bytes(note["model_answer"])
                st.audio(note_audio, format="audio/mp3")
            except Exception:
                st.caption("음성을 불러오지 못했습니다.")

            if st.button(
                "🗑️ 이 문장 오답노트에서 삭제",
                key=f"delete_note_{note['id']}",
                use_container_width=True,
            ):
                remove_review_note(note["id"])
                st.rerun()


st.divider()


# =========================================================
# 9. 최근 연습 기록
# =========================================================
with st.expander("최근 연습 기록 보기"):
    if not st.session_state.history:
        st.write("아직 연습 기록이 없습니다.")
    else:
        for idx, item in enumerate(st.session_state.history, start=1):
            time_label = "시간 내" if item.get("within_time") else "시간 초과"

            st.markdown(
                f"**{idx}. {item['part']} / {item['topic']} / {item['score']}점 / {time_label}**"
            )
            st.write(f"🇰🇷 {item['korean']}")
            st.write(f"✅ 모범 답안: {item['model_answer']}")
            st.write(f"🗣️ 내 답변: {item['user_answer']}")
            st.divider()


st.caption(
    "현재 오답노트는 브라우저 세션 기준으로 저장됩니다. 새로고침이나 서버 재시작 시 사라질 수 있으므로 중요한 문장은 CSV로 다운로드하세요."
)
