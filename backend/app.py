import os
import sys
import json
import uuid
import hashlib
import hmac
from datetime import datetime
from functools import wraps

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from flask import (
    Flask, jsonify, request, send_from_directory,
    session, redirect, url_for
)
from flask_cors import CORS
from dotenv import load_dotenv

# ── path setup ───────────────────────────────────────────────────────────────
ROOT_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
DATA_DIR     = os.path.join(ROOT_DIR, "data")
USERS_FILE   = os.path.join(DATA_DIR, "users.json")

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv(os.path.join(ROOT_DIR, ".env"))

os.makedirs(DATA_DIR, exist_ok=True)

# ── AI engine ────────────────────────────────────────────────────────────────
from ai_engine.vector_memory import VectorMemory
from ai_engine.rag import RAGAssistant
from ai_engine.sample_data import (
    seed_documents, SAMPLE_TASKS, SAMPLE_REMINDERS,
    SAMPLE_MEALS, SAMPLE_SAFETY,
)

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=FRONTEND_DIR)
app.secret_key = os.environ.get("SECRET_KEY", "maasathi-super-secret-change-in-prod-2024")
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5000", "http://localhost:5000"])

# ── vector memory + RAG ──────────────────────────────────────────────────────
memory    = VectorMemory(persist_dir=os.path.join(DATA_DIR, "vector_memory"))
assistant = RAGAssistant(memory)

if memory.is_empty():
    memory.add_documents(seed_documents)

# ── in-memory data stores ────────────────────────────────────────────────────
TASKS          = [dict(t) for t in SAMPLE_TASKS]
REMINDERS      = [dict(r) for r in SAMPLE_REMINDERS]
MEALS          = [dict(m) for m in SAMPLE_MEALS]
SAFETY_LOGS    = [dict(s) for s in SAMPLE_SAFETY]
NEXT_TASK_ID   = max(t["id"] for t in TASKS)     + 1
NEXT_REM_ID    = max(r["id"] for r in REMINDERS) + 1
NEXT_MEAL_ID   = max(m["id"] for m in MEALS)     + 1
NEXT_SAFETY_ID = max(s["id"] for s in SAFETY_LOGS) + 1


# ══════════════════════════════════════════════════════════════════════════════
#  USER STORE  (flat-file JSON)
# ══════════════════════════════════════════════════════════════════════════════

def _load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_users(users: dict) -> None:
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str) -> str:
    salt = "maasathi-salt-v1"
    return hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH DECORATOR
# ══════════════════════════════════════════════════════════════════════════════

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required.", "redirect": "/login.html"}), 401
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC FILE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(FRONTEND_DIR, path)


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/auth/register", methods=["POST"])
def register():
    payload  = request.json or {}
    name     = payload.get("name", "").strip()
    email    = payload.get("email", "").strip().lower()
    password = payload.get("password", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    users = _load_users()
    if email in users:
        return jsonify({"error": "An account with this email already exists."}), 409

    user_id = str(uuid.uuid4())
    users[email] = {
        "id":         user_id,
        "name":       name,
        "email":      email,
        "password":   _hash_password(password),
        "created_at": datetime.utcnow().isoformat(),
        "avatar":     name[0].upper(),
    }
    _save_users(users)

    session["user_id"]    = user_id
    session["user_email"] = email
    session["user_name"]  = name
    session["user_avatar"]= users[email]["avatar"]

    return jsonify({
        "message": "Account created successfully.",
        "user": {"id": user_id, "name": name, "email": email, "avatar": users[email]["avatar"]},
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    payload  = request.json or {}
    email    = payload.get("email", "").strip().lower()
    password = payload.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    users = _load_users()
    user  = users.get(email)
    if not user or user["password"] != _hash_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["user_id"]    = user["id"]
    session["user_email"] = email
    session["user_name"]  = user["name"]
    session["user_avatar"]= user.get("avatar", user["name"][0].upper())

    return jsonify({
        "message": "Logged in successfully.",
        "user": {
            "id":     user["id"],
            "name":   user["name"],
            "email":  email,
            "avatar": user.get("avatar", user["name"][0].upper()),
        },
    })


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


@app.route("/api/auth/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 401
    return jsonify({
        "authenticated": True,
        "user": {
            "id":     session["user_id"],
            "name":   session["user_name"],
            "email":  session["user_email"],
            "avatar": session.get("user_avatar", "M"),
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def push_memory(text, metadata=None):
    memory.add_documents([{"text": text, "metadata": metadata or {}}])


def summarize_chat_memory(question, answer):
    clean_question = " ".join(question.split())[:120]
    clean_answer = " ".join(answer.split())[:180]
    return f"Chat topic: {clean_question} | Reply summary: {clean_answer}"


def build_task_text(tasks):
    return "\n".join(
        f"- {t['title']} (priority={t['priority']}, assigned={t['assigned_to']}, status={t['status']})"
        for t in tasks
    )


# ══════════════════════════════════════════════════════════════════════════════
#  DATA ROUTES  (all protected by login_required)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/overview", methods=["GET"])
@login_required
def overview():
    open_tasks   = [t for t in TASKS if t["status"] == "open"]
    high_rem     = [r for r in REMINDERS if r["priority"] == "high"]
    return jsonify({
        "taskCount":     len(TASKS),
        "reminderCount": len(REMINDERS),
        "mealCount":     len(MEALS),
        "openTasks":     len(open_tasks),
        "urgentReminders": len(high_rem),
        "nextAction":    "Review urgent reminders, then use Energy-Smart Day Plan to match your routine to today's energy.",
        "safetyTip":     "Keep emergency contacts updated, feeding essentials ready, and one low-effort meal backup available.",
        "userName":      session.get("user_name", "User"),
    })


# ── TASKS ────────────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET", "POST"])
@login_required
def tasks_route():
    global NEXT_TASK_ID
    if request.method == "GET":
        return jsonify(TASKS)

    payload  = request.json or {}
    title    = payload.get("title", "").strip()
    priority = payload.get("priority", "medium")
    assigned = payload.get("assigned_to", "Mom")

    if not title:
        return jsonify({"error": "Task title is required."}), 400

    task = {
        "id":          NEXT_TASK_ID,
        "title":       title,
        "priority":    priority,
        "assigned_to": assigned,
        "status":      "open",
        "created_at":  datetime.utcnow().isoformat(),
    }
    NEXT_TASK_ID += 1
    TASKS.append(task)
    push_memory(f"New task added: {title}", {"type": "task"})
    return jsonify(task), 201


@app.route("/api/tasks/<int:task_id>", methods=["PATCH", "DELETE"])
@login_required
def task_detail(task_id):
    task = next((t for t in TASKS if t["id"] == task_id), None)
    if not task:
        return jsonify({"error": "Task not found."}), 404

    if request.method == "DELETE":
        TASKS.remove(task)
        return jsonify({"message": "Task deleted."})

    payload = request.json or {}
    for field in ("title", "priority", "assigned_to", "status"):
        if field in payload:
            task[field] = payload[field]
    return jsonify(task)


# ── REMINDERS ────────────────────────────────────────────────────────────────

@app.route("/api/reminders", methods=["GET", "POST"])
@login_required
def reminders_route():
    global NEXT_REM_ID
    if request.method == "GET":
        return jsonify(REMINDERS)

    payload = request.json or {}
    note    = payload.get("note", "").strip()
    due     = payload.get("due", "today")
    if not note:
        return jsonify({"error": "Reminder note is required."}), 400

    priority = "high" if any(w in note.lower() for w in ("urgent", "today", "now", "asap")) else "medium"
    reminder = {
        "id":         NEXT_REM_ID,
        "note":       note,
        "due":        due,
        "priority":   priority,
        "created_at": datetime.utcnow().isoformat(),
    }
    NEXT_REM_ID += 1
    REMINDERS.append(reminder)
    push_memory(f"Reminder: {note}", {"type": "reminder"})
    return jsonify(reminder), 201


@app.route("/api/reminders/<int:rem_id>", methods=["DELETE"])
@login_required
def reminder_detail(rem_id):
    rem = next((r for r in REMINDERS if r["id"] == rem_id), None)
    if not rem:
        return jsonify({"error": "Reminder not found."}), 404
    REMINDERS.remove(rem)
    return jsonify({"message": "Reminder deleted."})


# ── MEALS ─────────────────────────────────────────────────────────────────────

@app.route("/api/meals", methods=["GET", "POST"])
@login_required
def meals_route():
    global NEXT_MEAL_ID
    if request.method == "GET":
        return jsonify(MEALS)

    payload     = request.json or {}
    description = payload.get("description", "").strip()
    tags        = payload.get("tags", [])
    if not description:
        return jsonify({"error": "Meal description is required."}), 400

    meal = {"id": NEXT_MEAL_ID, "description": description, "tags": tags}
    NEXT_MEAL_ID += 1
    MEALS.append(meal)
    push_memory(f"Meal preference: {description}", {"type": "meal_preference"})
    return jsonify(meal), 201


# ── SAFETY ────────────────────────────────────────────────────────────────────

@app.route("/api/safety", methods=["GET"])
@login_required
def safety_info():
    return jsonify(SAFETY_LOGS)


@app.route("/api/safety/alert", methods=["POST"])
@login_required
def safety_alert():
    global NEXT_SAFETY_ID
    payload = request.json or {}
    message = payload.get("message", "SOS alert requested.").strip()

    log = {
        "id":           NEXT_SAFETY_ID,
        "note":         message,
        "last_checked": datetime.utcnow().strftime("%H:%M %d %b %Y"),
    }
    NEXT_SAFETY_ID += 1
    SAFETY_LOGS.append(log)
    push_memory(f"Safety alert: {message}", {"type": "safety"})

    advice = assistant.generate(
        "Please provide immediate, practical safety guidance for an SOS alert.",
        purpose="safety",
        extra={"message": message},
    )
    return jsonify({"alert": advice})


# ── AI ASSIST ─────────────────────────────────────────────────────────────────

@app.route("/api/assist/task_balance", methods=["POST"])
@login_required
def task_balance():
    tasks_text = build_task_text(TASKS)
    advice     = assistant.generate(
        "How should we fairly share household responsibilities this week?",
        purpose="task_balance",
        extra={"tasks_text": tasks_text},
    )
    return jsonify({"advice": advice})


@app.route("/api/assist/meal_planner", methods=["POST"])
@login_required
def meal_planner():
    payload     = request.json or {}
    ingredients = payload.get("ingredients", "vegetables, rice, lentils")
    plan        = assistant.generate(
        "What should we cook today and tomorrow for the family?",
        purpose="meal_planner",
        extra={"ingredients": ingredients},
    )
    return jsonify({"plan": plan})


@app.route("/api/assist/day_plan", methods=["POST"])
@login_required
def day_plan():
    payload = request.json or {}
    energy_level = payload.get("energy_level", "medium").strip().lower() or "medium"
    available_minutes = str(payload.get("available_minutes", "90")).strip() or "90"
    focus_area = payload.get("focus_area", "home rhythm").strip() or "home rhythm"

    advice = assistant.generate(
        "Help me plan a realistic motherhood day without overload.",
        purpose="day_plan",
        extra={
            "energy_level": energy_level,
            "available_minutes": available_minutes,
            "focus_area": focus_area,
        },
    )
    push_memory(
        (
            f"Energy-smart day plan requested: energy={energy_level}, "
            f"time={available_minutes} min, focus={focus_area}"
        ),
        {"type": "day_plan"},
    )
    return jsonify({"plan": advice})


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    payload = request.json or {}
    message = payload.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    user_name = session.get("user_name", "User")
    answer    = assistant.generate(
        message,
        purpose="chat",
        extra={"user_name": user_name},
    )
    push_memory(summarize_chat_memory(message, answer), {"type": "chat_history"})
    return jsonify({"answer": answer})


@app.route("/api/ai/status", methods=["GET"])
@login_required
def ai_status():
    """Check if Groq primary and Ollama backup are ready."""
    return jsonify(assistant.status())


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
