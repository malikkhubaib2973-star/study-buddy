import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from groq import Groq
from pydantic import BaseModel

from backend import db
from backend.prompts import get_prompt

load_dotenv()

app = FastAPI(title="Study Buddy API")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "openai/gpt-oss-20b"

db.init_db()

# Memory: dictionary (SQLite se restart ke baad wapas load hoti hai)
histories: Dict[str, List[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str
    subject: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


class QuizRequest(BaseModel):
    subject: str


def get_history(session_id: str) -> List[dict]:
    if session_id not in histories:
        histories[session_id] = db.load_history(session_id)
    return histories[session_id]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    history = get_history(req.session_id)
    history.append({"role": "user", "content": req.message})

    # Sirf aakhri 10 messages LLM ko bhejte hain
    messages = [{"role": "system", "content": get_prompt(req.subject)}] + history[-10:]

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        history.pop()  # fail hua to user ka message history se hata do
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    history.append({"role": "assistant", "content": reply})

    # Dono messages database mein save
    db.save_message(req.session_id, "user", req.message)
    db.save_message(req.session_id, "assistant", reply)

    return {"reply": reply, "turns": len(history) // 2}


@app.post("/reset")
def reset(req: ResetRequest):
    histories.pop(req.session_id, None)
    db.delete_history(req.session_id)
    return {"status": "reset"}


@app.post("/quiz")
def quiz(req: QuizRequest):
    prompt = (
        f"Create 3 multiple-choice questions for a student studying {req.subject}. "
        "Return ONLY valid JSON, no extra text, in this format: "
        '[{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "answer": "A"}]. '
        "Write math in plain text, no LaTeX."
    )
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = completion.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        questions = json.loads(text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Quiz error: {e}")
    return {"questions": questions}