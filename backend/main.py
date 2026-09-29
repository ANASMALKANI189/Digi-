from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime, timedelta
from google import genai
from dotenv import load_dotenv

import json
import uuid
import os

# =========================================================
# ENVIRONMENT
# =========================================================

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set in .env")

client = genai.Client(api_key=api_key)

# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="Digiमन API",
    description="Personal AI Assistant Backend",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# DATA PATHS
# =========================================================

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONVERSATION_FILE = DATA_DIR / "conversation.json"
ACADEMIC_FILE = DATA_DIR / "academic_record.json"
ACADEMIC_CONTEXT_FILE = DATA_DIR / "academics_context.json"
BODY_FILE = DATA_DIR / "body.json"
FINANCE_FILE = DATA_DIR / "finance.json"
MIND_FILE = DATA_DIR / "mind.json"
HABITS_FILE = DATA_DIR / "habits.json"
LEARNINGS_FILE = DATA_DIR / "learning.json"
RULEBOOK_FILE = DATA_DIR / "digiman_rulebook.json"

# =========================================================
# REQUEST MODEL - KEEP THIS SHAPE COMPATIBLE WITH FRONTEND
# =========================================================

class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str

# =========================================================
# GENERIC JSON HELPERS
# =========================================================

def read_json(file_path: Path, default_data):
    if not file_path.exists():
        save_json(file_path, default_data)
        return default_data

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON file: {file_path.name}",
        )


def save_json(file_path: Path, data):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, file_path)

# =========================================================
# DEFAULT STRUCTURES
# =========================================================

def empty_body():
    return {
        "profile": {
            "height_cm": None,
            "height_updated_at": None,
        },
        "daily_records": {},
    }


def empty_finance():
    return {
        "profile": {
            "currency": "INR",
            "monthly_budget": None,
            "budget_updated_at": None,
        },
        "daily_records": {},
    }


def empty_mind():
    return {
        "daily_records": {},
    }


def empty_habits():
    return {
        "habits": {},
        "daily_records": {},
    }


def empty_learnings():
    return {
        "entries": [],
    }


def read_conversations():
    return read_json(CONVERSATION_FILE, {"conversations": []})


def save_conversations(data):
    save_json(CONVERSATION_FILE, data)


def read_rulebook():
    return read_json(RULEBOOK_FILE, {"system": {"name": "Digiमन"}})


def read_academic_record():
    return read_json(ACADEMIC_FILE, {})


def read_academic_context():
    return read_json(ACADEMIC_CONTEXT_FILE, {})


def read_body():
    return read_json(BODY_FILE, empty_body())


def read_finance():
    return read_json(FINANCE_FILE, empty_finance())


def read_mind():
    return read_json(MIND_FILE, empty_mind())


def read_habits():
    return read_json(HABITS_FILE, empty_habits())


def read_learnings():
    return read_json(LEARNINGS_FILE, empty_learnings())

# =========================================================
# DATE / TIME
# =========================================================

# Uses the OS-local timezone, exactly like the working version.
# No ZoneInfo/tzdata dependency is required.

def now_local():
    return datetime.now().astimezone()


def today_string():
    return now_local().strftime("%Y-%m-%d")


def current_timestamp():
    return now_local().isoformat()

# =========================================================
# CONVERSATION MEMORY
# =========================================================

def create_conversation(data, message):
    now = now_local()
    conversation = {
        "conversation_id": f"conv_{uuid.uuid4().hex[:8]}",
        "date": now.strftime("%Y-%m-%d"),
        "start_time": now.strftime("%H:%M:%S"),
        "title": message,
        "summary": "",
        "messages": [],
    }
    data.setdefault("conversations", []).append(conversation)
    return conversation


def find_conversation(data, conversation_id):
    if not conversation_id:
        return None
    for conversation in data.get("conversations", []):
        if conversation.get("conversation_id") == conversation_id:
            return conversation
    return None


def build_memory(data, max_chars=60000):
    parts = []
    for conversation in data.get("conversations", []):
        for message in conversation.get("messages", []):
            timestamp = message.get("timestamp", "")
            parts.append(
                f"[{timestamp}] User: {message.get('user_message', '')}"
            )
            parts.append(
                f"[{timestamp}] Assistant: {message.get('assistant_response', '')}"
            )

    text = "\n".join(parts)
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]

# =========================================================
# SAFE PATH HELPERS
# =========================================================

def get_value_at_path(data, path):
    if not path:
        return data

    current = data
    try:
        for key in path.split("."):
            if isinstance(current, dict):
                current = current[key]
            elif isinstance(current, list):
                current = current[int(key)]
            else:
                return None
        return current
    except (KeyError, IndexError, ValueError, TypeError):
        return None


def set_value_at_path(data, path, value):
    if not path:
        return False

    parts = path.split(".")
    current = data

    for key in parts[:-1]:
        if not isinstance(current, dict):
            return False
        if key not in current:
            current[key] = {}
        if not isinstance(current[key], dict):
            return False
        current = current[key]

    current[parts[-1]] = value
    return True


def append_value_at_path(data, path, value):
    target = get_value_at_path(data, path)
    if target is None:
        if not set_value_at_path(data, path, []):
            return False
        target = get_value_at_path(data, path)

    if not isinstance(target, list):
        return False

    target.append(value)
    return True

# =========================================================
# BODY DOMAIN
# =========================================================

def create_daily_body_record(date_string):
    return {
        "date": date_string,
        "status": "open",
        "body_measurements": {
            "weight_kg": None,
            "weight_recorded_at": None,
        },
        "hydration": {
            "total_intake_ml": 0,
            "entries": [],
        },
        "nutrition": {
            "total_calories_consumed": 0,
            "meals": [],
        },
        "activity": {
            "steps": {
                "count": 0,
                "status": "not_recorded",
                "last_updated_at": None,
            },
            "distance": {
                "value": 0,
                "unit": "km",
                "last_updated_at": None,
                "calculation": "estimated_from_steps",
            },
        },
        "workouts": {
            "total_sessions": 0,
            "total_duration_minutes": 0,
            "sessions": [],
        },
        "daily_summary": {
            "water_intake_ml": 0,
            "calories_consumed": 0,
            "steps": 0,
            "distance_km": 0,
            "workout_duration_minutes": 0,
            "workout_sessions": 0,
        },
        "notes": [],
    }


def ensure_today_body(body_data):
    body_data.setdefault("profile", {"height_cm": None, "height_updated_at": None})
    body_data.setdefault("daily_records", {})
    today = today_string()

    for record_date, record in body_data["daily_records"].items():
        if record_date < today:
            record["status"] = "locked"

    if today not in body_data["daily_records"]:
        body_data["daily_records"][today] = create_daily_body_record(today)

    return body_data


def calculate_distance_km(steps, height_cm=None):
    try:
        steps = max(0, float(steps or 0))
    except (ValueError, TypeError):
        return 0

    if height_cm:
        try:
            stride_meters = float(height_cm) * 0.415 / 100
        except (ValueError, TypeError):
            stride_meters = 0.762
    else:
        stride_meters = 0.762

    return round((steps * stride_meters) / 1000, 2)


def recalculate_body_distance(body_data, record_date):
    record = body_data.get("daily_records", {}).get(record_date)
    if not record:
        return

    steps = record["activity"]["steps"]["count"]
    height = body_data.get("profile", {}).get("height_cm")
    distance = calculate_distance_km(steps, height)

    record["activity"]["distance"]["value"] = distance
    record["activity"]["distance"]["last_updated_at"] = current_timestamp()
    record["daily_summary"]["distance_km"] = distance


def update_body_summary(record):
    record["daily_summary"]["water_intake_ml"] = record["hydration"]["total_intake_ml"]
    record["daily_summary"]["calories_consumed"] = record["nutrition"]["total_calories_consumed"]
    record["daily_summary"]["steps"] = record["activity"]["steps"]["count"]
    record["daily_summary"]["distance_km"] = record["activity"]["distance"]["value"]
    record["daily_summary"]["workout_duration_minutes"] = record["workouts"]["total_duration_minutes"]
    record["daily_summary"]["workout_sessions"] = record["workouts"]["total_sessions"]


def apply_body_update(body_data, action):
    ensure_today_body(body_data)
    action_date = action.get("date") or today_string()
    if action_date == "today":
        action_date = today_string()

    try:
        datetime.strptime(action_date, "%Y-%m-%d")
    except ValueError:
        return {"success": False, "file": "body.json", "message": "Invalid date format. Use YYYY-MM-DD."}

    if action_date not in body_data["daily_records"]:
        body_data["daily_records"][action_date] = create_daily_body_record(action_date)

    record = body_data["daily_records"][action_date]

    if action_date < today_string() and record.get("status") == "locked":
        return {"success": False, "file": "body.json", "date": action_date, "message": "This day's body record is locked."}

    payload = action.get("data", {})
    if not isinstance(payload, dict):
        return {"success": False, "file": "body.json", "message": "Body update data must be an object."}

    if payload.get("height_cm") is not None:
        try:
            height = float(payload["height_cm"])
            if height > 0:
                body_data["profile"]["height_cm"] = height
                body_data["profile"]["height_updated_at"] = current_timestamp()
        except (ValueError, TypeError):
            pass

    if payload.get("weight_kg") is not None:
        try:
            weight = float(payload["weight_kg"])
            if weight > 0:
                record["body_measurements"]["weight_kg"] = weight
                record["body_measurements"]["weight_recorded_at"] = current_timestamp()
        except (ValueError, TypeError):
            pass

    water_entries = payload.get("water_entries", [])
    if isinstance(water_entries, dict):
        water_entries = [water_entries]
    for water in water_entries:
        if not isinstance(water, dict):
            continue
        try:
            amount_ml = round(float(water.get("amount_ml", 0)))
        except (ValueError, TypeError):
            continue
        if amount_ml <= 0:
            continue
        record["hydration"]["entries"].append({
            "timestamp": water.get("timestamp") or current_timestamp(),
            "amount_ml": amount_ml,
            "source": "user_reported",
        })
        record["hydration"]["total_intake_ml"] += amount_ml

    if payload.get("steps") is not None:
        try:
            steps = int(float(payload["steps"]))
            if steps >= 0:
                record["activity"]["steps"]["count"] = steps
                record["activity"]["steps"]["status"] = payload.get("steps_status", "recording")
                record["activity"]["steps"]["last_updated_at"] = current_timestamp()
                recalculate_body_distance(body_data, action_date)
        except (ValueError, TypeError):
            pass

    meals = payload.get("meals", [])
    if isinstance(meals, dict):
        meals = [meals]
    for meal in meals:
        if not isinstance(meal, dict):
            continue
        foods = meal.get("foods", [])
        if isinstance(foods, dict):
            foods = [foods]
        cleaned_foods = []
        meal_total = 0
        for food in foods:
            if not isinstance(food, dict):
                continue
            try:
                calories = max(0, float(food.get("estimated_calories", 0)))
            except (ValueError, TypeError):
                calories = 0
            cleaned_foods.append({
                "name": food.get("name", "Unknown food"),
                "quantity": food.get("quantity", ""),
                "estimated_calories": round(calories),
            })
            meal_total += calories
        record["nutrition"]["meals"].append({
            "meal_id": f"meal_{uuid.uuid4().hex[:8]}",
            "meal_type": meal.get("meal_type", "other"),
            "timestamp": meal.get("timestamp") or current_timestamp(),
            "foods": cleaned_foods,
            "meal_total_calories": round(meal_total),
        })

    record["nutrition"]["total_calories_consumed"] = round(sum(
        meal.get("meal_total_calories", 0) for meal in record["nutrition"]["meals"]
    ))

    workouts = payload.get("workouts", [])
    if isinstance(workouts, dict):
        workouts = [workouts]
    for workout in workouts:
        if not isinstance(workout, dict):
            continue
        try:
            duration = max(0, float(workout.get("duration_minutes", 0)))
        except (ValueError, TypeError):
            duration = 0
        start_time = workout.get("start_time") or current_timestamp()
        end_time = workout.get("end_time")
        if not end_time and duration > 0:
            try:
                end_time = (datetime.fromisoformat(start_time) + timedelta(minutes=duration)).isoformat()
            except Exception:
                end_time = None
        exercises = workout.get("exercises", [])
        if not isinstance(exercises, list):
            exercises = [exercises]
        record["workouts"]["sessions"].append({
            "session_id": f"workout_{uuid.uuid4().hex[:8]}",
            "start_time": start_time,
            "end_time": end_time,
            "duration_minutes": round(duration, 2),
            "exercises": exercises,
        })

    record["workouts"]["total_sessions"] = len(record["workouts"]["sessions"])
    record["workouts"]["total_duration_minutes"] = round(sum(
        session.get("duration_minutes", 0) for session in record["workouts"]["sessions"]
    ), 2)

    notes = payload.get("notes", [])
    if isinstance(notes, str):
        notes = [notes]
    for note in notes:
        if isinstance(note, str) and note.strip():
            record["notes"].append({"timestamp": current_timestamp(), "text": note.strip()})

    recalculate_body_distance(body_data, action_date)
    update_body_summary(record)
    save_json(BODY_FILE, body_data)

    return {
        "success": True,
        "operation": "body_update",
        "file": "body.json",
        "date": action_date,
        "data": record,
        "message": "Body data updated successfully.",
    }

# =========================================================
# FINANCE DOMAIN
# =========================================================

def create_daily_finance_record(date_string):
    return {
        "date": date_string,
        "status": "open",
        "summary": {
            "total_expenses": 0,
            "expense_count": 0,
        },
        "expenses": [],
        "income": [],
        "notes": [],
    }


def ensure_today_finance(data):
    data.setdefault("profile", {"currency": "INR", "monthly_budget": None, "budget_updated_at": None})
    data.setdefault("daily_records", {})
    today = today_string()
    for record_date, record in data["daily_records"].items():
        if record_date < today:
            record["status"] = "locked"
    if today not in data["daily_records"]:
        data["daily_records"][today] = create_daily_finance_record(today)
    return data


def apply_finance_update(data, action):
    ensure_today_finance(data)
    action_date = action.get("date") or today_string()
    if action_date == "today":
        action_date = today_string()
    try:
        datetime.strptime(action_date, "%Y-%m-%d")
    except ValueError:
        return {"success": False, "file": "finance.json", "message": "Invalid date format. Use YYYY-MM-DD."}

    if action_date not in data["daily_records"]:
        data["daily_records"][action_date] = create_daily_finance_record(action_date)
    record = data["daily_records"][action_date]
    if action_date < today_string() and record.get("status") == "locked":
        return {"success": False, "file": "finance.json", "date": action_date, "message": "This day's finance record is locked."}

    payload = action.get("data", {})
    if not isinstance(payload, dict):
        return {"success": False, "file": "finance.json", "message": "Finance update data must be an object."}

    if payload.get("monthly_budget") is not None:
        try:
            budget = float(payload["monthly_budget"])
            if budget >= 0:
                data["profile"]["monthly_budget"] = budget
                data["profile"]["budget_updated_at"] = current_timestamp()
        except (ValueError, TypeError):
            pass

    expenses = payload.get("expenses", [])
    if isinstance(expenses, dict):
        expenses = [expenses]
    for expense in expenses:
        if not isinstance(expense, dict):
            continue
        try:
            amount = float(expense.get("amount", 0))
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue
        record["expenses"].append({
            "expense_id": f"exp_{uuid.uuid4().hex[:8]}",
            "timestamp": expense.get("timestamp") or current_timestamp(),
            "amount": round(amount, 2),
            "currency": expense.get("currency", data["profile"].get("currency", "INR")),
            "category": expense.get("category", "other"),
            "description": expense.get("description", ""),
            "payment_method": expense.get("payment_method"),
        })

    incomes = payload.get("income", [])
    if isinstance(incomes, dict):
        incomes = [incomes]
    for income in incomes:
        if not isinstance(income, dict):
            continue
        try:
            amount = float(income.get("amount", 0))
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue
        record["income"].append({
            "income_id": f"inc_{uuid.uuid4().hex[:8]}",
            "timestamp": income.get("timestamp") or current_timestamp(),
            "amount": round(amount, 2),
            "currency": income.get("currency", data["profile"].get("currency", "INR")),
            "source": income.get("source", "other"),
            "description": income.get("description", ""),
        })

    for note in payload.get("notes", []) if isinstance(payload.get("notes", []), list) else [payload.get("notes")]:
        if isinstance(note, str) and note.strip():
            record["notes"].append({"timestamp": current_timestamp(), "text": note.strip()})

    record["summary"]["total_expenses"] = round(sum(e.get("amount", 0) for e in record["expenses"]), 2)
    record["summary"]["expense_count"] = len(record["expenses"])
    save_json(FINANCE_FILE, data)
    return {"success": True, "operation": "finance_update", "file": "finance.json", "date": action_date, "data": record, "message": "Finance data updated successfully."}

# =========================================================
# MIND DOMAIN
# =========================================================

def create_daily_mind_record(date_string):
    return {
        "date": date_string,
        "status": "open",
        "mood": None,
        "mood_history": [],
        "feelings": [],
        "stress_level": None,
        "energy_level": None,
        "notes": [],
    }


def ensure_today_mind(data):
    data.setdefault("daily_records", {})
    today = today_string()
    for record_date, record in data["daily_records"].items():
        if record_date < today:
            record["status"] = "locked"
    if today not in data["daily_records"]:
        data["daily_records"][today] = create_daily_mind_record(today)
    return data


def apply_mind_update(data, action):
    ensure_today_mind(data)
    action_date = action.get("date") or today_string()
    if action_date == "today":
        action_date = today_string()
    if action_date not in data["daily_records"]:
        data["daily_records"][action_date] = create_daily_mind_record(action_date)
    record = data["daily_records"][action_date]
    if action_date < today_string() and record.get("status") == "locked":
        return {"success": False, "file": "mind.json", "date": action_date, "message": "This day's mind record is locked."}

    payload = action.get("data", {})
    if not isinstance(payload, dict):
        return {"success": False, "file": "mind.json", "message": "Mind update data must be an object."}

    timestamp = payload.get("timestamp") or current_timestamp()
    if payload.get("mood") is not None:
        mood = str(payload["mood"])
        record["mood"] = mood
        record["mood_history"].append({"timestamp": timestamp, "mood": mood})
    if payload.get("stress_level") is not None:
        record["stress_level"] = payload["stress_level"]
    if payload.get("energy_level") is not None:
        record["energy_level"] = payload["energy_level"]

    feelings = payload.get("feelings", [])
    if isinstance(feelings, str):
        feelings = [feelings]
    for feeling in feelings:
        if isinstance(feeling, str) and feeling.strip():
            record["feelings"].append({"timestamp": timestamp, "text": feeling.strip()})

    notes = payload.get("notes", [])
    if isinstance(notes, str):
        notes = [notes]
    for note in notes:
        if isinstance(note, str) and note.strip():
            record["notes"].append({"timestamp": timestamp, "text": note.strip()})

    save_json(MIND_FILE, data)
    return {"success": True, "operation": "mind_update", "file": "mind.json", "date": action_date, "data": record, "message": "Mind data updated successfully."}

# =========================================================
# HABITS DOMAIN
# =========================================================

def ensure_habits(data):
    data.setdefault("habits", {})
    data.setdefault("daily_records", {})
    today = today_string()
    for record_date, record in data["daily_records"].items():
        if record_date < today:
            record["status"] = "locked"
    data["daily_records"].setdefault(today, {"date": today, "status": "open", "habits": {}, "notes": []})
    return data


def apply_habits_update(data, action):
    ensure_habits(data)
    action_date = action.get("date") or today_string()
    if action_date == "today":
        action_date = today_string()
    data["daily_records"].setdefault(action_date, {"date": action_date, "status": "open", "habits": {}, "notes": []})
    record = data["daily_records"][action_date]
    if action_date < today_string() and record.get("status") == "locked":
        return {"success": False, "file": "habits.json", "date": action_date, "message": "This day's habit record is locked."}

    payload = action.get("data", {})
    if not isinstance(payload, dict):
        return {"success": False, "file": "habits.json", "message": "Habit update data must be an object."}

    habit_name = payload.get("habit") or payload.get("name")
    if habit_name:
        habit_name = str(habit_name).strip()
        key = habit_name.lower().replace(" ", "_")
        data["habits"].setdefault(key, {
            "name": habit_name,
            "created_at": current_timestamp(),
            "target": payload.get("target"),
        })
        record["habits"][key] = {
            "name": habit_name,
            "completed": bool(payload.get("completed", True)),
            "value": payload.get("value"),
            "timestamp": payload.get("timestamp") or current_timestamp(),
            "notes": payload.get("notes", ""),
        }

    for item in payload.get("habits", []) if isinstance(payload.get("habits", []), list) else []:
        if not isinstance(item, dict):
            continue
        name = item.get("habit") or item.get("name")
        if not name:
            continue
        name = str(name).strip()
        key = name.lower().replace(" ", "_")
        data["habits"].setdefault(key, {"name": name, "created_at": current_timestamp(), "target": item.get("target")})
        record["habits"][key] = {
            "name": name,
            "completed": bool(item.get("completed", True)),
            "value": item.get("value"),
            "timestamp": item.get("timestamp") or current_timestamp(),
            "notes": item.get("notes", ""),
        }

    notes = payload.get("notes", [])
    if isinstance(notes, str):
        notes = [notes]
    for note in notes:
        if isinstance(note, str) and note.strip():
            record["notes"].append({"timestamp": current_timestamp(), "text": note.strip()})

    save_json(HABITS_FILE, data)
    return {"success": True, "operation": "habit_update", "file": "habits.json", "date": action_date, "data": record, "message": "Habit data updated successfully."}

# =========================================================
# LEARNINGS DOMAIN
# =========================================================

def apply_learning_update(data, action):
    data.setdefault("entries", [])
    payload = action.get("data", {})
    if not isinstance(payload, dict):
        return {"success": False, "file": "learning.json", "message": "Learning data must be an object."}

    entry = {
        "learning_id": f"learn_{uuid.uuid4().hex[:8]}",
        "timestamp": payload.get("timestamp") or current_timestamp(),
        "topic": payload.get("topic", "General"),
        "title": payload.get("title", ""),
        "content": payload.get("content", ""),
        "source": payload.get("source"),
        "tags": payload.get("tags", []),
    }
    if not entry["content"] and not entry["title"]:
        return {"success": False, "file": "learning.json", "message": "Learning entry needs content or title."}
    data["entries"].append(entry)
    save_json(LEARNINGS_FILE, data)
    return {"success": True, "operation": "learning_update", "file": "learning.json", "data": entry, "message": "Learning stored successfully."}

# =========================================================
# FILE MAP
# =========================================================

ALLOWED_FILES = {
    "academic_record.json": ACADEMIC_FILE,
    "academics_context.json": ACADEMIC_CONTEXT_FILE,
    "body.json": BODY_FILE,
    "finance.json": FINANCE_FILE,
    "mind.json": MIND_FILE,
    "habits.json": HABITS_FILE,
    "learning.json": LEARNINGS_FILE,
}

# =========================================================
# ACTION EXECUTION
# =========================================================

def execute_actions(actions):
    results = []
    for action in actions:
        if not isinstance(action, dict):
            continue

        operation = action.get("operation")
        file_name = action.get("file")
        path = action.get("path") or ""
        action_data = action.get("data")

        if file_name not in ALLOWED_FILES:
            results.append({"success": False, "reason": f"File '{file_name}' is not allowed."})
            continue

        try:
            if file_name == "body.json" and operation == "body_update":
                results.append(apply_body_update(read_body(), action))
                continue

            if file_name == "finance.json" and operation == "finance_update":
                results.append(apply_finance_update(read_finance(), action))
                continue

            if file_name == "mind.json" and operation == "mind_update":
                results.append(apply_mind_update(read_mind(), action))
                continue

            if file_name == "habits.json" and operation == "habit_update":
                results.append(apply_habits_update(read_habits(), action))
                continue

            if file_name == "learning.json" and operation == "learning_update":
                results.append(apply_learning_update(read_learnings(), action))
                continue

            file_path = ALLOWED_FILES[file_name]

            if operation == "read":
                data = read_json(file_path, {})
                results.append({
                    "success": True,
                    "operation": "read",
                    "file": file_name,
                    "path": path,
                    "data": get_value_at_path(data, path),
                })
                continue

            if operation == "update":
                if file_name != "academic_record.json":
                    results.append({"success": False, "operation": "update", "file": file_name, "message": "This file does not support generic update."})
                    continue
                data = read_json(file_path, {})
                success = set_value_at_path(data, path, action_data)
                if success:
                    save_json(file_path, data)
                results.append({"success": success, "operation": "update", "file": file_name, "path": path, "data": action_data, "message": "Academic record updated." if success else "Could not update path."})
                continue

            if operation == "append":
                if file_name != "academic_record.json":
                    results.append({"success": False, "operation": "append", "file": file_name, "message": "This file does not support generic append."})
                    continue
                data = read_json(file_path, {})
                success = append_value_at_path(data, path, action_data)
                if success:
                    save_json(file_path, data)
                results.append({"success": success, "operation": "append", "file": file_name, "path": path, "data": action_data, "message": "Data appended successfully." if success else "Could not append data."})
                continue

            results.append({"success": False, "operation": operation, "file": file_name, "message": "Unknown operation."})

        except Exception as error:
            results.append({"success": False, "operation": operation, "file": file_name, "error": str(error)})

    return results

# =========================================================
# GEMINI PLANNER
# =========================================================

def ask_gemini_planner(message, conversation_memory, rulebook):
    today = today_string()

    prompt = f"""
You are the PLANNING ENGINE of Digiमन.
You do NOT generate the final answer.
You decide what memory must be READ and what important persistent data must be STORED.

CURRENT DATE: {today}

RULEBOOK:
{json.dumps(rulebook, indent=2, ensure_ascii=False)}

AVAILABLE MEMORY SOURCES:
1. conversation.json - previous user messages, assistant replies and timestamps.
2. academic_record.json - marks, practicals, assignments, projects, academic progress.
3. academics_context.json - semester calendar, timetable, subjects, exam dates and academic reference data.
4. body.json - height, weight, water, food/calories, steps, distance, workouts and daily body history.
5. finance.json - daily expenses, income, budget and money-management history.
6. mind.json - mood, feelings, stress, energy and mental notes.
7. habits.json - user habits, completion/value and daily habit history.
8. learning.json - things the user explicitly learned, notes and concepts worth remembering.

CURRENT USER MESSAGE:
{message}

CONVERSATION MEMORY:
{conversation_memory}

=========================================================
CORE RULES
=========================================================

1. RETRIEVAL IS MANDATORY WHEN THE USER ASKS ABOUT STORED PERSONAL INFORMATION.
Always create read actions for the relevant domain. Do not answer from general knowledge when the requested fact may exist in memory.

2. ACADEMICS:
For academic questions, consider BOTH academic_record.json and academics_context.json, plus conversation memory.
If the user asks dates/schedules such as ISE/ESE, read academics_context.json.
If the user asks marks/progress, read academic_record.json.
If unclear, read both.

3. CONVERSATION MEMORY:
Use conversation memory for follow-ups such as "practical 2 mein?", "aur kal wala?", "kitna tha?" etc. If the answer depends on a previous personal statement, read conversation.json through the memory supplied here or create a read action for the relevant domain.

4. STORE ONLY REAL USER FACTS.
Do not store wishes, hypothetical statements, generic questions or casual conversation as personal records.
Example: "I should drink more water" -> do not store.
Example: "I drank 1 litre of water" -> store.

5. If a message both reports new personal data and asks a question, STORE first and READ the relevant memory needed for the answer.

=========================================================
BODY
=========================================================

Store when user reports:
- height
- weight
- water intake
- food/meals
- steps
- workout sessions
- exercises
- workout duration
- workout timestamps
- body notes

Height is profile-level. Weight is daily.
Water must be appended as a new timestamped entry; never replace previous intake.
Convert litres to ml: 1 litre = 1000 ml.
Steps are the CURRENT total for the day. If user says 5000 then later 8000, set steps to 8000, do not add them.
Distance is NEVER supplied by the planner; backend calculates it automatically from steps and height.

Calories: when user reports food, estimate calories from food and quantity and store each food under a meal with estimated_calories. Never claim estimated calories are exact.

Workout sessions are flexible. Users can do ANY activity. Do not assume a fixed exercise list. Every session should have duration_minutes, start_time if known, end_time if known, and an exercises array. Morning and evening sessions must remain separate.

BODY STORAGE EXAMPLE:
{{
  "operation": "body_update",
  "file": "body.json",
  "date": "{today}",
  "data": {{
    "water_entries": [{{"amount_ml": 1000}}],
    "steps": 5000,
    "steps_status": "recording",
    "workouts": [{{
      "duration_minutes": 40,
      "exercises": [
        {{"name": "pushups", "sets": 3, "reps": 30}},
        {{"name": "squats", "reps": 100}}
      ]
    }}]
  }}
}}

=========================================================
FINANCE
=========================================================

Store real money events.
Expense example: "I spent 250 on lunch" -> finance_update with an expense amount 250, category food, description lunch.
"I spent 500 on Uber" -> category transport.
"I received 10000 salary" -> income.
Never invent amounts.
If category is obvious, classify it; otherwise use other.
Multiple expense statements in one message should become multiple expense entries.
For retrieval, read finance.json for totals, category breakdowns, daily/monthly spending, recent expenses and budget.

FINANCE STORAGE FORMAT:
{{
  "operation": "finance_update",
  "file": "finance.json",
  "date": "{today}",
  "data": {{
    "expenses": [{{
      "amount": 250,
      "category": "food",
      "description": "lunch"
    }}]
  }}
}}

=========================================================
MIND
=========================================================

Store genuine mood/feeling reports.
Examples:
"I feel happy today" -> mood update.
"I am stressed because of exams" -> mood/feeling plus note.
"My energy is 7/10" -> energy_level 7.
Do not diagnose the user and do not invent mental-health information.
For retrieval, read mind.json.

MIND STORAGE FORMAT:
{{
  "operation": "mind_update",
  "file": "mind.json",
  "date": "{today}",
  "data": {{
    "mood": "happy",
    "feelings": ["excited"]
  }}
}}

=========================================================
HABITS
=========================================================

Store actual habit completion or measurable habit activity.
Examples:
"I completed my morning meditation" -> habit meditation completed.
"I studied for 2 hours today" can be stored as a study habit/activity if the user is clearly reporting it as a habit.
Do not turn a one-off unrelated event into a habit unless the user frames it as a habit/routine.
For retrieval, read habits.json.

HABIT STORAGE FORMAT:
{{
  "operation": "habit_update",
  "file": "habits.json",
  "date": "{today}",
  "data": {{
    "habit": "morning meditation",
    "completed": true
  }}
}}

=========================================================
LEARNINGS
=========================================================

Store things the user explicitly says they learned, understood, studied, discovered or wants permanently remembered as knowledge.
Examples:
"Today I learned that PostgreSQL stores rows in heap pages" -> learning_update.
"Remember that my project uses React and FastAPI" -> learning_update if it is a persistent project fact.
Do NOT store every assistant explanation as a learning automatically. The user's explicit learning/remember intent is the trigger.
For retrieval, read learning.json.

LEARNING STORAGE FORMAT:
{{
  "operation": "learning_update",
  "file": "learning.json",
  "data": {{
    "topic": "PostgreSQL",
    "title": "Storage model",
    "content": "PostgreSQL stores table data in heap pages."
  }}
}}

=========================================================
READ EXAMPLES
=========================================================

User: "mere ISE aur ESE kab hain?"
-> read academics_context.json path ""

User: "WAD practical 1 mein kitne aaye?"
-> read academic_record.json path ""

User: "aaj maine kitna paani piya?"
-> read body.json path "daily_records.{today}"

User: "mere last 7 days ka expense bata"
-> read finance.json path ""

User: "mera mood kal kaisa tha?"
-> read mind.json path ""

User: "maine is week kaunse habits complete kiye?"
-> read habits.json path ""

User: "maine PostgreSQL ke baare mein kya seekha tha?"
-> read learning.json path ""

For broad/analytical questions, read the complete relevant file so the final engine can calculate from stored history.

=========================================================
OUTPUT
=========================================================

Return ONLY valid JSON:
{{
  "intent": "store | retrieve | chat",
  "actions": [
    {{
      "operation": "read | update | append | body_update | finance_update | mind_update | habit_update | learning_update",
      "file": "academic_record.json | academics_context.json | body.json | finance.json | mind.json | habits.json | learning.json",
      "path": "",
      "date": "{today}",
      "data": null
    }}
  ]
}}

For read actions, data MUST be null.
Do not create storage actions for casual conversation.
Do not generate the final answer.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Gemini planner returned invalid JSON.",
                "raw_response": response.text,
            },
        )

# =========================================================
# GEMINI FINAL ANSWER
# =========================================================

def ask_gemini_final(
    message,
    conversation_memory,
    rulebook,
    academic_record,
    academic_context,
    body_data,
    finance_data,
    mind_data,
    habits_data,
    learning_data,
    retrieval_results,
    planner_decision,
):
    prompt = f"""
You are Digiमन, the user's personal digital-memory assistant.

Answer the CURRENT USER MESSAGE using ONLY the supplied personal memory and retrieved data.
General knowledge may be used only for harmless explanation/calculation, never to invent a personal fact.

=========================================================
RULEBOOK
=========================================================
{json.dumps(rulebook, indent=2, ensure_ascii=False)}

=========================================================
ACADEMIC RECORD
=========================================================
{json.dumps(academic_record, indent=2, ensure_ascii=False)}

=========================================================
ACADEMIC CONTEXT
=========================================================
{json.dumps(academic_context, indent=2, ensure_ascii=False)}

=========================================================
BODY MEMORY
=========================================================
{json.dumps(body_data, indent=2, ensure_ascii=False)}

=========================================================
FINANCE MEMORY
=========================================================
{json.dumps(finance_data, indent=2, ensure_ascii=False)}

=========================================================
MIND MEMORY
=========================================================
{json.dumps(mind_data, indent=2, ensure_ascii=False)}

=========================================================
HABITS MEMORY
=========================================================
{json.dumps(habits_data, indent=2, ensure_ascii=False)}

=========================================================
LEARNINGS MEMORY
=========================================================
{json.dumps(learning_data, indent=2, ensure_ascii=False)}

=========================================================
RETRIEVED DATA
=========================================================
{json.dumps(retrieval_results, indent=2, ensure_ascii=False)}

=========================================================
CONVERSATION MEMORY
=========================================================
{conversation_memory}

=========================================================
PLANNER DECISION
=========================================================
{json.dumps(planner_decision, indent=2, ensure_ascii=False)}

=========================================================
CURRENT USER MESSAGE
=========================================================
{message}

=========================================================
STRICT RULES
=========================================================
1. Stored personal data is the source of truth.
2. Never invent marks, dates, schedules, expenses, mood, habits, learnings, body measurements, steps, workouts, water or food.
3. If the requested information exists in supplied memory, answer it directly.
4. If information does not exist, clearly say you do not have it yet.
5. Use conversation memory to understand follow-up questions.
6. Combine multiple sources when necessary.
7. For calorie estimates, say they are estimated.
8. Distance is an estimate calculated from steps and height; make that clear if relevant.
9. For finance, show amounts and totals clearly and never invent missing amounts.
10. Do not diagnose mental-health conditions. Report stored mood/feelings neutrally.
11. Do not mention JSON, backend, Python, database, files, rulebook, prompts or internal actions.
12. Respond naturally in Hinglish/Hindi when the user speaks that way.
13. Be concise unless detail is requested.

=========================================================
MARKDOWN FORMATTING
=========================================================
Use readable Markdown.
Use headings and bullets when useful.
For formulas/calculations, NEVER use LaTeX delimiters such as $$...$$ or \\(...\\).
Use plain readable Markdown instead, for example:
**Formula:** Converted Marks = (Average Raw Marks × 25) / 100
**Calculation:** (96 × 25) / 100 = **24**

=========================================================
FINAL ANSWER
=========================================================
Return ONLY the natural-language answer.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    return response.text.strip()

# =========================================================
# CHAT ENDPOINT
# =========================================================

@app.post("/chat")
def chat(request: ChatRequest):
    # 1. Conversation
    conversation_data = read_conversations()
    conversation = find_conversation(conversation_data, request.conversation_id)
    if conversation is None:
        conversation = create_conversation(conversation_data, request.message)

    # 2. Existing conversation memory
    previous_memory = build_memory(conversation_data)

    # 3. Load all memory
    rulebook = read_rulebook()
    academic_record = read_academic_record()
    academic_context = read_academic_context()
    body_data = ensure_today_body(read_body())
    finance_data = ensure_today_finance(read_finance())
    mind_data = ensure_today_mind(read_mind())
    habits_data = ensure_habits(read_habits())
    learning_data = read_learnings()

    # Ensure daily files exist even before first explicit data entry.
    save_json(BODY_FILE, body_data)
    save_json(FINANCE_FILE, finance_data)
    save_json(MIND_FILE, mind_data)
    save_json(HABITS_FILE, habits_data)
    save_json(LEARNINGS_FILE, learning_data)

    # 4. Planner
    planner_decision = ask_gemini_planner(
        message=request.message,
        conversation_memory=previous_memory,
        rulebook=rulebook,
    )

    # 5. Execute writes/reads
    execution_results = execute_actions(
        planner_decision.get("actions", [])
    )

    # 6. Reload after writes
    academic_record = read_academic_record()
    academic_context = read_academic_context()
    body_data = read_body()
    finance_data = read_finance()
    mind_data = read_mind()
    habits_data = read_habits()
    learning_data = read_learnings()

    # 7. Final answer
    assistant_response = ask_gemini_final(
        message=request.message,
        conversation_memory=previous_memory,
        rulebook=rulebook,
        academic_record=academic_record,
        academic_context=academic_context,
        body_data=body_data,
        finance_data=finance_data,
        mind_data=mind_data,
        habits_data=habits_data,
        learning_data=learning_data,
        retrieval_results=execution_results,
        planner_decision=planner_decision,
    )

    # 8. Save conversation
    now = now_local()
    conversation["messages"].append({
        "message_id": f"msg_{uuid.uuid4().hex[:8]}",
        "timestamp": now.isoformat(),
        "user_message": request.message,
        "assistant_response": assistant_response,
    })
    save_conversations(conversation_data)

    # 9. Response shape remains compatible with existing frontend
    return {
        "conversation_id": conversation["conversation_id"],
        "response": assistant_response,
        "intent": planner_decision.get("intent", "chat"),
        "actions": execution_results,
    }

# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "Digiमन backend is running",
        "status": "online",
    }
