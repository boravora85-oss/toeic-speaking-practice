import random
import re
from difflib import SequenceMatcher

import streamlit as st
from streamlit_mic_recorder import speech_to_text


QUESTION_BANK = [
    {
        "part": "Part 3",
        "topic": "Shopping",
        "korean": "나는 온라인 쇼핑을 더 선호한다. 왜냐하면 편리하고 시간을 절약할 수 있기 때문이다.",
        "english": "I prefer shopping online because it is convenient and saves time.",
    },
    {
        "part": "Part 3",
        "topic": "Eating out",
        "korean": "나는 보통 주말에 가족과 외식을 한다. 우리는 다양한 음식을 먹을 수 있어서 외식을 좋아한다.",
        "english": "I usually eat out with my family on weekends because we can enjoy many kinds of food.",
    },
    {
        "part": "Part 3",
        "topic": "Travel",
        "korean": "나는 다른 사람들과 여행하는 것을 선호한다. 왜냐하면 같은 추억을 공유할 수 있기 때문이다.",
        "english": "I prefer traveling with other people because I can share the same memories with them.",
    },
    {
        "part": "Part 3",
        "topic": "Free time",
        "korean": "나는 여가 시간에 산책하는 것을 좋아한다. 스트레스를 줄이고 기분 전환에 도움이 된다.",
        "english": "I like taking a walk in my free time because it reduces stress and refreshes my mind.",
    },
    {
        "part": "Part 5",
        "topic": "Opinion",
        "korean": "나는 이 의견에 동의한다. 왜냐하면 이것은 사람들에게 더 많은 기회를 줄 수 있기 때문이다.",
        "english": "I agree with this opinion because it can give people more opportunities.",
    },
]


st.set_page_config(
    page_title="나만의 토익스피킹 연습 앱",
    page_icon="🎙️",
    layout="centered",
)


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


def pick_new_question():
    st.session_state.current_question = random.choice(QUESTION_BANK)
    st.session_state.answer_input = ""
    st.session_state.submitted = False
    st.session_state.similarity_score = None
    st.session_state.recorder_key_number += 1


def initialize_state():
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


initialize_state()

st.title("🎙️ 나만의 토익스피킹 연습 앱")
st.caption("2단계 MVP: 마이크로 말하면 영어 답변이 텍스트로 변환됩니다.")

current = st.session_state.current_question

with st.container(border=True):
    st.subheader("오늘의 문제")

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Part:** {current['part']}")

    with col2:
        st.write(f"**Topic:** {current['topic']}")

    st.markdown("### 🇰🇷 한국어 문장")
    st.info(current["korean"])


if st.button("🔄 새 문제 출제", use_container_width=True):
    pick_new_question()
    st.rerun()


st.divider()

st.subheader("1단계: 마이크로 영어 답변하기")

st.write(
    "아래 버튼을 눌러 녹음을 시작하고, 영어로 답변한 뒤 다시 버튼을 눌러 녹음을 종료하세요."
)

spoken_text = speech_to_text(
    language="en",
    start_prompt="🎙️ 녹음 시작",
    stop_prompt="⏹️ 녹음 종료",
    just_once=True,
    use_container_width=True,
    key=f"toeic_stt_{st.session_state.recorder_key_number}",
)

if spoken_text:
    st.session_state.answer_input = spoken_text
    st.session_state.submitted = False
    st.session_state.similarity_score = None
    st.success("음성 인식이 완료되었습니다. 아래 입력창에서 필요하면 문장을 수정하세요.")

st.text_area(
    "내 답변",
    key="answer_input",
    height=120,
    placeholder="마이크로 말하면 여기에 영어 문장이 자동으로 들어옵니다. 직접 타이핑하거나 수정해도 됩니다.",
)


st.divider()

st.subheader("2단계: 모범 답안과 비교하기")

if st.button("✅ 정답 확인", use_container_width=True):
    user_answer = st.session_state.answer_input.strip()

    if not user_answer:
        st.warning("먼저 마이크로 답변하거나 영어 문장을 입력해 주세요.")
    else:
        st.session_state.submitted = True
        st.session_state.similarity_score = calculate_similarity(
            user_answer,
            current["english"],
        )

        st.session_state.history.insert(
            0,
            {
                "part": current["part"],
                "topic": current["topic"],
                "korean": current["korean"],
                "model_answer": current["english"],
                "user_answer": user_answer,
                "score": st.session_state.similarity_score,
            },
        )

        st.session_state.history = st.session_state.history[:5]


if st.session_state.submitted:
    score = st.session_state.similarity_score or 0

    st.metric("모범 답안과의 유사도", f"{score}점 / 100점")

    if score >= 85:
        st.success("좋습니다. 모범 답안과 매우 비슷하게 말했습니다.")
    elif score >= 65:
        st.info("괜찮습니다. 핵심 표현은 맞지만, 문장 구조를 조금 더 다듬으면 좋습니다.")
    else:
        st.warning("아직 차이가 있습니다. 모범 답안을 보고 한 번 더 말해보세요.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### ✅ 모범 답안")
        st.write(current["english"])

    with col2:
        st.markdown("#### 🗣️ 내 답변")
        st.write(st.session_state.answer_input)

    with st.expander("복습 포인트 보기"):
        st.write("- 음성 인식 결과가 실제 발음과 다르게 나올 수 있습니다.")
        st.write("- 이 단계의 점수는 AI 채점이 아니라 단순 문장 유사도입니다.")
        st.write("- 다음 단계에서 AI 채점관을 연결하면 문법, 자연스러움, 답변 구조까지 평가할 수 있습니다.")


st.divider()

with st.expander("최근 연습 기록"):
    if not st.session_state.history:
        st.write("아직 연습 기록이 없습니다.")
    else:
        for idx, item in enumerate(st.session_state.history, start=1):
            st.markdown(f"**{idx}. {item['part']} / {item['topic']} / {item['score']}점**")
            st.write(f"🇰🇷 {item['korean']}")
            st.write(f"✅ 모범 답안: {item['model_answer']}")
            st.write(f"🗣️ 내 답변: {item['user_answer']}")
            st.divider()


st.caption(
    "현재 버전은 2단계 MVP입니다. 다음 단계에서는 AI 채점관을 연결해 10점 만점 채점과 교정 피드백을 추가할 수 있습니다."
)