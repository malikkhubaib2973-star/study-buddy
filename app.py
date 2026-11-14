import os
import uuid

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

SUBJECTS = {
    "Math": "math",
    "Science": "science",
    "English": "english",
    "Computer Science": "computer_science",
}

st.set_page_config(page_title="Study Buddy", page_icon="📚")
st.title("📚 Study Buddy")

# session_id, messages aur quiz state mein
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quiz" not in st.session_state:
    st.session_state.quiz = []

# Sidebar
with st.sidebar:
    st.header("Settings")
    subject_label = st.selectbox("Subject chuno", list(SUBJECTS.keys()))
    subject = SUBJECTS[subject_label]

    if st.button("New conversation"):
        try:
            httpx.post(
                f"{BACKEND_URL}/reset",
                json={"session_id": st.session_state.session_id},
                timeout=10,
            )
        except Exception:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.quiz = []
        st.rerun()

    if st.button("Quiz me"):
        with st.spinner("Quiz ban raha hai..."):
            try:
                r = httpx.post(
                    f"{BACKEND_URL}/quiz",
                    json={"subject": subject_label},
                    timeout=60,
                )
                r.raise_for_status()
                st.session_state.quiz = r.json()["questions"]
            except httpx.ConnectError:
                st.error("⚠️ Server se connection nahi ho raha.")
            except Exception:
                st.error("⚠️ Quiz nahi ban saka. Dobara koshish karo.")

# Quiz dikhao
if st.session_state.quiz:
    st.subheader("📝 Quiz")
    for i, q in enumerate(st.session_state.quiz):
        st.radio(q["question"], q["options"], index=None, key=f"quiz_{i}")

    if st.button("Check answers"):
        score = 0
        for i, q in enumerate(st.session_state.quiz):
            picked = st.session_state.get(f"quiz_{i}")
            correct = q["answer"].strip().upper()[0]
            if picked and picked.strip().upper().startswith(correct):
                score += 1
                st.success(f"Q{i+1}: Sahi ✅")
            else:
                st.error(f"Q{i+1}: Galat ❌ (sahi jawab: {correct})")
        st.info(f"Score: {score} / {len(st.session_state.quiz)}")
    st.divider()

# Purani chat dikhao
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Naya message
user_input = st.chat_input("Apna sawal likho...")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Soch raha hoon..."):
            try:
                response = httpx.post(
                    f"{BACKEND_URL}/chat",
                    json={
                        "session_id": st.session_state.session_id,
                        "subject": subject,
                        "message": user_input,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                reply = response.json()["reply"]
            except httpx.ConnectError:
                reply = "⚠️ Server se connection nahi ho raha. Thori der baad try karo."
            except Exception:
                reply = "⚠️ Kuch masla aa gaya. Dobara koshish karo."
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})