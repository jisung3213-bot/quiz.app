import streamlit as st
import pandas as pd
import json
import re
import os

RANKING_FILE = "rankings.json"

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="중간고사 복습용 quiz",
    layout="centered"
)

# =========================
# 기존 랭킹 보존 (로컬)
# =========================

def load_rankings_from_file():
    if os.path.exists(RANKING_FILE):
        with open(RANKING_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    return {
        "통계학": [],
        "선형대수학": [],
        "사회학": []
    }

def save_rankings_to_file():
    with open(RANKING_FILE, "w", encoding="utf-8") as file:
        json.dump(
            st.session_state.rankings,
            file,
            ensure_ascii=False,
            indent=4
        )

# =========================
# 세션 상태 초기화
# =========================
if "users" not in st.session_state:
    st.session_state.users = []

if "page" not in st.session_state:
    st.session_state.page = "home"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "last_score" not in st.session_state:
    st.session_state.last_score = None

if "last_subject" not in st.session_state:
    st.session_state.last_subject = None

if "last_total" not in st.session_state:
    st.session_state.last_total = None

if "rankings" not in st.session_state:
    st.session_state.rankings = load_rankings_from_file()


# =========================
# 유효성 검사 함수
# =========================
def validate_student_id(student_id):
    return bool(re.fullmatch(r"\d{10}", student_id))


def validate_birth_date(birth_date):
    if not re.fullmatch(r"\d{6}", birth_date):
        return False

    year = int(birth_date[0:2])
    month = int(birth_date[2:4])
    day = int(birth_date[4:6])

    return 0 <= year <= 99 and 1 <= month <= 12 and 1 <= day <= 31


def validate_phone(phone):
    return bool(re.fullmatch(r"010-\d{4}-\d{4}", phone))


def validate_password(password):
    return bool(re.fullmatch(r"[A-Za-z0-9]+", password))


def is_duplicate_student_id(student_id):
    for user in st.session_state.users:
        if user["student_id"] == student_id:
            return True
    return False


def find_user(student_id, password):
    for user in st.session_state.users:
        if user["student_id"] == student_id and user["password"] == password:
            return user
    return None

def find_user_by_student_id_and_phone(student_id, phone):
    for user in st.session_state.users:
        if user["student_id"] == student_id and user["phone"] == phone:
            return user
    return None


# =========================
# CSV 데이터 불러오기
# =========================
@st.cache_data
def load_quiz_data(file_path):
    return pd.read_csv(file_path)


# =========================
# 수식 출력 보조 함수
# =========================
def normalize_latex_text(text):
    """
    CSV에서 읽은 문자열을 수식 출력에 맞게 정리한다.
    특히 행렬 LaTeX의 줄바꿈 문제를 보정한다.
    """
    text = str(text).strip()

    if text == "" or text.lower() == "nan":
        return ""

    # CSV에 \n이 문자 그대로 들어간 경우 실제 줄바꿈으로 변환
    text = text.replace("\\n", "\n")

    # 과하게 이스케이프된 백슬래시 보정
    # 예: \\lambda → \lambda
    text = text.replace("\\\\lambda", "\\lambda")
    text = text.replace("\\\\frac", "\\frac")
    text = text.replace("\\\\binom", "\\binom")
    text = text.replace("\\\\sqrt", "\\sqrt")
    text = text.replace("\\\\mathrm", "\\mathrm")
    text = text.replace("\\\\operatorname", "\\operatorname")
    text = text.replace("\\\\le", "\\le")
    text = text.replace("\\\\ge", "\\ge")
    text = text.replace("\\\\sim", "\\sim")
    text = text.replace("\\\\pm", "\\pm")
    text = text.replace("\\\\quad", "\\quad")
    text = text.replace("\\\\cdot", "\\cdot")
    text = text.replace("\\\\times", "\\times")
    text = text.replace("\\\\left", "\\left")
    text = text.replace("\\\\right", "\\right")
    text = text.replace("\\\\begin", "\\begin")
    text = text.replace("\\\\end", "\\end")

    # 행렬 수식 보정
    if "\\begin{pmatrix}" in text and "\\end{pmatrix}" in text:
        # CSV 안에서 행렬이 여러 줄로 들어간 경우 공백으로 정리
        text = re.sub(r"\s+", " ", text)

        matrix_pattern = r"\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}"

        def fix_matrix_body(match):
            body = match.group(1).strip()

            # 4&0&1\ -2&1&0\ -2&0&1 같은 형태 보정
            body = re.sub(
                r"(?<=[0-9\)])\\\s*(?=-?[0-9\(])",
                r"\\\\",
                body
            )

            # 이미 \\가 아니라 \ 하나만 행 구분자로 들어간 경우 보정
            body = re.sub(
                r"(?<!\\)\\(?![A-Za-z])",
                r"\\\\",
                body
            )

            return r"\begin{pmatrix}" + body + r"\end{pmatrix}"

        text = re.sub(matrix_pattern, fix_matrix_body, text)

    return text


def is_single_latex_expression(text):
    """
    문자열 전체가 하나의 수식에 가까운지 판단한다.
    """
    text = text.strip()

    if text.startswith("$$") and text.endswith("$$") and text.count("$$") == 2:
        return True

    if text.startswith("$") and text.endswith("$") and text.count("$") == 2:
        return True

    latex_indicators = [
        "\\frac",
        "\\binom",
        "\\sqrt",
        "\\mathrm",
        "\\operatorname",
        "\\lambda",
        "\\mu",
        "\\sigma",
        "\\bar",
        "\\hat",
        "\\le",
        "\\ge",
        "\\sim",
        "\\pm",
        "\\quad",
        "\\cdot",
        "\\times",
        "\\left",
        "\\right",
        "\\begin",
        "\\end",
        "pmatrix",
        "^",
        "_"
    ]

    has_latex = any(indicator in text for indicator in latex_indicators)
    has_korean = bool(re.search(r"[가-힣]", text))

    return has_latex and not has_korean


def render_text_or_latex(text):
    """
    텍스트가 수식만 있으면 st.latex로 출력하고,
    문장과 수식이 섞여 있으면 st.markdown으로 출력한다.
    """
    text = normalize_latex_text(text)

    if text == "":
        return

    # $$ ... $$ 형태의 블록 수식
    if text.startswith("$$") and text.endswith("$$") and text.count("$$") == 2:
        latex_text = text[2:-2].strip()
        st.latex(latex_text)
        return

    # $ ... $ 형태의 단독 인라인 수식
    if text.startswith("$") and text.endswith("$") and text.count("$") == 2:
        latex_text = text[1:-1].strip()
        st.latex(latex_text)
        return

    # 단독 LaTeX 수식으로 보이는 경우
    if is_single_latex_expression(text):
        latex_text = text.strip("$").strip()
        st.latex(latex_text)
        return

    # 일반 문장 또는 문장 + $수식$ 혼합
    st.markdown(text)


# =========================
# 순위 저장 함수
# =========================
from datetime import datetime

def save_result(subject, name, student_id, score, total):
    ranking_list = st.session_state.rankings[subject]

    existing_record = None

    for record in ranking_list:
        if record["student_id"] == student_id:
            existing_record = record
            break

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if existing_record is None:
        ranking_list.append({
            "name": name,
            "student_id": student_id,
            "score": score,
            "total": total,
            "date": now
        })
    else:
        if score > existing_record["score"]:
            existing_record["score"] = score
            existing_record["total"] = total
            existing_record["date"] = now

    ranking_list.sort(key=lambda x: x["score"], reverse=True)

    save_rankings_to_file()

def delete_ranking_record(subject, student_id):
    records = st.session_state.rankings[subject]

    st.session_state.rankings[subject] = [
        record for record in records
        if record["student_id"] != student_id
    ]

    save_rankings_to_file()


# =========================
# 순위표 출력 함수
# =========================
def show_rankings():
    st.write("")
    st.subheader("순위표")

    col1, col2, col3 = st.columns(3)

    subjects = [
        ("통계학", col1),
        ("선형대수학", col2),
        ("사회학", col3)
    ]

    for subject, col in subjects:
        with col:
            st.markdown(f"### {subject}")

            records = st.session_state.rankings[subject]

            if len(records) == 0:
                st.write("저장된 결과가 없습니다.")
            else:
                for rank, record in enumerate(records, start=1):
                    st.write(
                        f"{rank}위. {record['name']} - "
                        f"{record['score']*5} / {record['total']*5}점"
                    )
                    st.caption(f"저장일: {record.get('date', '날짜 없음')}")

                    delete_key = f"delete_{subject}_{record['student_id']}"

                    if st.button("삭제", key=delete_key):
                        delete_ranking_record(subject, record["student_id"])
                        st.rerun()


# =========================
# 첫 페이지
# =========================
def home_page():
    st.title("2023204077 박지성")

    st.write("")
    st.write("")

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        if st.button("회원가입", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()

    with col2:
        if st.button("로그인", use_container_width=True):
            st.session_state.page = "login"
            st.rerun()

    show_rankings()


# =========================
# 회원가입 페이지
# =========================
def signup_page():
    st.title("2023204077 박지성")
    st.subheader("회원가입")

    name = st.text_input("이름을 입력하세요")
    student_id = st.text_input("학번을 입력하세요", placeholder="숫자 10자리")
    birth_date = st.text_input("생년월일을 입력하세요", placeholder="예: 041015")
    phone = st.text_input("전화번호를 입력하세요", placeholder="010-1234-5678")
    password = st.text_input(
        "비밀번호를 입력하세요",
        placeholder="특수문자 사용 불가",
        type="password"
    )

    if st.button("가입하기"):
        if name.strip() == "":
            st.error("이름을 입력")

        elif not validate_student_id(student_id):
            st.error("학번은 숫자 10자리")

        elif is_duplicate_student_id(student_id):
            st.error("이미 가입된 학번")

        elif not validate_birth_date(birth_date):
            st.error("생년월일은 YYMMDD 형식. 월은 01~12, 일은 01~31")

        elif not validate_phone(phone):
            st.error("전화번호는 010-xxxx-xxxx 형식.")

        elif not validate_password(password):
            st.error("비밀번호는 영어와 숫자만 사용.")

        else:
            st.session_state.users.append({
                "name": name.strip(),
                "student_id": student_id,
                "birth_date": birth_date,
                "phone": phone,
                "password": password
            })

            st.success("회원가입이 완료되었습니다.")

    if st.button("처음으로 돌아가기"):
        st.session_state.page = "home"
        st.rerun()


# =========================
# 로그인 페이지
# =========================
def login_page():
    st.title("2023204077 박지성")
    st.subheader("로그인")

    student_id = st.text_input("학번을 입력하세요", placeholder="숫자 10자리")
    password = st.text_input("비밀번호를 입력하세요", type="password")

    if st.button("로그인"):
        user = find_user(student_id, password)

        if user is not None:
            st.session_state.logged_in = True
            st.session_state.current_user = user
            st.session_state.page = "quiz"
            st.session_state.last_score = None
            st.session_state.last_subject = None
            st.session_state.last_total = None
            st.rerun()
        else:
            st.error("잘못된 로그인입니다.")

    st.divider()

    st.subheader("비밀번호 찾기")

    find_student_id = st.text_input(
        "비밀번호를 찾을 학번을 입력하세요",
        placeholder="숫자 10자리",
        key="find_password_student_id"
    )

    find_phone = st.text_input(
        "가입할 때 입력한 전화번호를 입력하세요",
        placeholder="010-1234-5678",
        key="find_password_phone"
    )

    if st.button("비밀번호 찾기"):
        if not validate_student_id(find_student_id):
            st.error("학번은 숫자 10자리여야 해.")

        elif not validate_phone(find_phone):
            st.error("전화번호는 010-xxxx-xxxx 형식이어야 해.")

        else:
            user = find_user_by_student_id_and_phone(find_student_id, find_phone)

            if user is not None:
                st.success(f"비밀번호는 {user['password']} 입니다.")
            else:
                st.error("일치하는 회원 정보가 없습니다.")

    if st.button("처음으로 돌아가기"):
        st.session_state.page = "home"
        st.rerun()


# =========================
# 퀴즈 페이지
# =========================
def quiz_page():
    st.title("퀴즈 - 시험이 끝나도 다시 복습하자")

    user = st.session_state.current_user

    if user is not None:
        st.success(f"{user['name']}님 환영합니다.")

    quiz_files = {
        "통계학": "quiz_data/probability.csv",
        "선형대수학": "quiz_data/linear_algebra.csv",
        "사회학": "quiz_data/sociology.csv"
    }

    selected_subject = st.selectbox(
        "문제 유형을 선택하세요",
        list(quiz_files.keys())
    )

    file_path = quiz_files[selected_subject]

    if not os.path.exists(file_path):
        st.error(f"{selected_subject} 파일이 존재하지 않습니다.")
        st.write(f"필요한 파일 경로: {file_path}")
        return

    quiz_data = load_quiz_data(file_path)

    required_columns = [
        "number",
        "title",
        "question",
        "choice1",
        "choice2",
        "choice3",
        "choice4",
        "choice5",
        "answer"
    ]

    if not all(column in quiz_data.columns for column in required_columns):
        st.error("CSV 파일 형식이 올바르지 않습니다.")
        st.write("필요한 열:", required_columns)
        return

    st.subheader(selected_subject)

    user_answers = []

    for i, row in quiz_data.iterrows():
        number = int(row["number"])
        title = str(row["title"])
        question = str(row["question"])

        st.markdown(f"### {number}번. {title}")

        render_text_or_latex(question)

        choices = {
            "1": str(row["choice1"]),
            "2": str(row["choice2"]),
            "3": str(row["choice3"]),
            "4": str(row["choice4"]),
            "5": str(row["choice5"])
        }

        st.write("")

        for choice_number, choice_text in choices.items():
            st.markdown(f"**{choice_number}.**")
            render_text_or_latex(choice_text)

        selected_answer = st.radio(
            "정답 번호를 선택하세요",
            options=["1", "2", "3", "4", "5"],
            key=f"{selected_subject}_{i}"
        )

        user_answers.append(selected_answer)

        st.divider()

    if st.button("제출하기"):
        score = 0

        for i, row in quiz_data.iterrows():
            correct_answer = str(row["answer"]).strip()

            if user_answers[i] == correct_answer:
                score += 1

        st.session_state.last_score = score
        st.session_state.last_subject = selected_subject
        st.session_state.last_total = len(quiz_data)

        st.success(f"점수: {score} / {len(quiz_data)}")

        st.subheader("채점 결과")

        cols = st.columns(3)

        for i, row in quiz_data.iterrows():
            number = int(row["number"])
            title = str(row["title"])
            correct_answer = str(row["answer"]).strip()
            selected_answer = user_answers[i]

            col = cols[i % 3]

            with col:
                st.markdown(f"**{number}번. {title}**")
                st.write(f"내 답: {selected_answer}")
                st.write(f"정답: {correct_answer}")

                if selected_answer == correct_answer:
                    st.success("정답")
                else:
                    st.error("오답")

    if st.session_state.last_score is not None:
        st.write("")
        st.subheader("결과저장")

        st.write(
            f"저장할 결과: "
            f"{st.session_state.last_subject} "
            f"{st.session_state.last_score} / {st.session_state.last_total}점"
        )

        if st.button("결과저장"):
            save_result(
                subject=st.session_state.last_subject,
                name=user["name"],
                student_id=user["student_id"],
                score=st.session_state.last_score,
                total=st.session_state.last_total
            )

            st.success("결과가 저장됐어. 첫 화면 순위표에 반영돼.")

    if st.button("처음 화면으로 이동"):
        st.session_state.page = "home"
        st.rerun()

    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.page = "home"
        st.session_state.last_score = None
        st.session_state.last_subject = None
        st.session_state.last_total = None
        st.rerun()


# =========================
# 페이지 이동 처리
# =========================
if st.session_state.page == "home":
    home_page()

elif st.session_state.page == "signup":
    signup_page()

elif st.session_state.page == "login":
    login_page()

elif st.session_state.page == "quiz":
    if st.session_state.logged_in:
        quiz_page()
    else:
        st.session_state.page = "login"
        st.rerun()