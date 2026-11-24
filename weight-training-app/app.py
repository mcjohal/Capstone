"""Weight Training App - plan four workouts a week, track them, and add exercises.

Data lives in two JSON files (no database):
  data/exercises.json - every exercise, grouped by body part
  data/progress.json  - this week's 4 routines and your workout history
                        (created automatically the first time the app runs)
"""
import json
import os
import random
import uuid
from datetime import date, timedelta

from flask import Flask, abort, flash, redirect, render_template, request, url_for

app = Flask(__name__)
# flash() messages need a secret key. Read it from the SECRET_KEY environment
# variable; the fallback is only for running on your own computer.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-not-secret")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXERCISES_FILE = os.path.join(BASE_DIR, "data", "exercises.json")
PROGRESS_FILE = os.path.join(BASE_DIR, "data", "progress.json")

EQUIPMENT_TYPES = ["Dumbbell", "Barbell", "Body Weight", "Kettlebell"]

# Each routine says how many exercises to pick from each body part.
ROUTINE_TEMPLATES = {
    "Push": {"chest": 2, "shoulders": 2, "triceps": 1},
    "Pull": {"back": 3, "biceps": 2},
    "Legs & Abs": {"legs": 3, "abdominals": 2},
    "Full Body": {"legs": 2, "chest": 1, "back": 1, "shoulders": 1, "abdominals": 1},
    # Extra routines you can swap in with the "Replace" button:
    "Chest & Triceps": {"chest": 3, "triceps": 2},
    "Back & Biceps": {"back": 3, "biceps": 2},
    "Shoulders & Abs": {"shoulders": 3, "abdominals": 2},
    "Upper Body Mix": {"chest": 1, "back": 1, "shoulders": 1, "biceps": 1, "triceps": 1},
    "Arms Day": {"biceps": 3, "triceps": 3},
}
# The 4 routines every new week starts with (Monday, Tuesday, Thursday, Friday).
DEFAULT_WEEK = ["Push", "Pull", "Legs & Abs", "Full Body"]
DAY_LABELS = ["Monday", "Tuesday", "Thursday", "Friday"]


# ---------- helper functions ----------

def load_json(path, default):
    """Read a JSON file, or return `default` if the file doesn't exist yet."""
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_exercises():
    return load_json(EXERCISES_FILE, {})


def current_week_key():
    """A label like '2026-W48' that changes every Monday."""
    year, week, _ = date.today().isocalendar()
    return f"{year}-W{week:02d}"


def week_date_range():
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def build_routine(template_name, rng, exercises):
    """Pick random exercises for one routine using the template's counts."""
    picked = []
    for slug, count in ROUTINE_TEMPLATES[template_name].items():
        category = exercises.get(slug)
        if not category:
            continue
        options = category["exercises"]
        for ex in rng.sample(options, min(count, len(options))):
            picked.append({
                "name": ex["name"],
                "category": category["name"],
                "equipment": ex["equipment"],
                "sets": ex["sets"],
                "reps": ex["reps"],
                "completed": False,
                "history_id": None,
            })
    return {"template": template_name, "exercises": picked}


def build_week(week_key, exercises):
    # Seeding with the week key means the plan is the same all week
    # but different every new week.
    rng = random.Random(week_key)
    return [build_routine(name, rng, exercises) for name in DEFAULT_WEEK]


def load_progress():
    """Load progress, creating a fresh set of routines when a new week starts."""
    progress = load_json(PROGRESS_FILE, {"week": None, "routines": [], "history": []})
    week_key = current_week_key()
    if progress["week"] != week_key:
        progress["week"] = week_key
        progress["routines"] = build_week(week_key, load_exercises())
        save_json(PROGRESS_FILE, progress)
    return progress


# ---------- pages ----------

@app.route("/")
def index():
    progress = load_progress()
    routines = progress["routines"]
    total = sum(len(r["exercises"]) for r in routines)
    done = sum(1 for r in routines for ex in r["exercises"] if ex["completed"])
    week_start, week_end = week_date_range()
    return render_template(
        "index.html",
        routines=routines,
        days=DAY_LABELS,
        templates=ROUTINE_TEMPLATES,
        week_start=week_start,
        week_end=week_end,
        total=total,
        done=done,
    )


@app.route("/exercises")
def categories():
    exercises = load_exercises()
    return render_template("categories.html", categories=exercises, equipment_types=EQUIPMENT_TYPES)


@app.route("/exercises/<slug>")
def category_detail(slug):
    exercises = load_exercises()
    if slug not in exercises:
        abort(404)
    category = exercises[slug]
    equipment = request.args.get("equipment", "")  # optional filter, e.g. ?equipment=Barbell
    shown = category["exercises"]
    if equipment in EQUIPMENT_TYPES:
        shown = [ex for ex in shown if ex["equipment"] == equipment]
    return render_template(
        "category.html",
        slug=slug,
        category=category,
        exercises=shown,
        equipment=equipment,
        equipment_types=EQUIPMENT_TYPES,
    )


@app.route("/add", methods=["GET", "POST"])
def add_exercise():
    exercises = load_exercises()
    form = {
        "category": request.args.get("category", ""),
        "name": "",
        "equipment": "",
        "sets": "3",
        "reps": "10",
        "description": "",
    }
    errors = []

    if request.method == "POST":
        form = {key: request.form.get(key, "").strip() for key in form}

        if form["category"] not in exercises:
            errors.append("Choose a body part.")
        if not form["name"]:
            errors.append("Enter an exercise name.")
        elif form["category"] in exercises:
            existing = [ex["name"].lower() for ex in exercises[form["category"]]["exercises"]]
            if form["name"].lower() in existing:
                errors.append(f"{form['name']} is already in that category.")
        if form["equipment"] not in EQUIPMENT_TYPES:
            errors.append("Choose the equipment type.")
        if not form["sets"].isdigit() or not 1 <= int(form["sets"]) <= 10:
            errors.append("Sets must be a whole number from 1 to 10.")
        if not form["reps"]:
            errors.append("Enter reps, for example 10 or 30 sec.")

        if not errors:
            exercises[form["category"]]["exercises"].append({
                "name": form["name"],
                "equipment": form["equipment"],
                "sets": int(form["sets"]),
                "reps": form["reps"],
                "description": form["description"],
                "custom": True,  # marks exercises the user added, so they can be deleted
            })
            save_json(EXERCISES_FILE, exercises)
            flash(f"Added {form['name']} to {exercises[form['category']]['name']}.", "success")
            return redirect(url_for("category_detail", slug=form["category"]))

    return render_template(
        "add_exercise.html",
        categories=exercises,
        equipment_types=EQUIPMENT_TYPES,
        form=form,
        errors=errors,
    )


@app.route("/history")
def history():
    progress = load_progress()
    entries = sorted(progress["history"], key=lambda h: h["completed_at"], reverse=True)

    by_date = {}  # {"2026-11-23": [entry, entry], ...}
    for entry in entries:
        by_date.setdefault(entry["completed_at"][:10], []).append(entry)

    by_category = {}
    for entry in entries:
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1

    this_week = sum(1 for e in entries if e["week"] == progress["week"])
    return render_template(
        "history.html",
        by_date=by_date,
        by_category=by_category,
        total=len(entries),
        this_week=this_week,
        workout_days=len(by_date),
    )


# ---------- form actions (they change data, then go back to a page) ----------

@app.route("/complete/<int:routine_index>/<int:exercise_index>", methods=["POST"])
def toggle_complete(routine_index, exercise_index):
    progress = load_progress()
    try:
        routine = progress["routines"][routine_index]
        exercise = routine["exercises"][exercise_index]
    except IndexError:
        abort(404)

    if exercise["completed"]:
        # Undo: remove the matching history entry.
        progress["history"] = [h for h in progress["history"] if h["id"] != exercise["history_id"]]
        exercise["completed"] = False
        exercise["history_id"] = None
    else:
        entry_id = uuid.uuid4().hex
        progress["history"].append({
            "id": entry_id,
            "completed_at": date.today().isoformat(),
            "week": progress["week"],
            "day": DAY_LABELS[routine_index],
            "routine": routine["template"],
            "name": exercise["name"],
            "category": exercise["category"],
            "equipment": exercise["equipment"],
            "sets": exercise["sets"],
            "reps": exercise["reps"],
        })
        exercise["completed"] = True
        exercise["history_id"] = entry_id

    save_json(PROGRESS_FILE, progress)
    return redirect(url_for("index") + f"#routine-{routine_index}")


@app.route("/replace/<int:routine_index>", methods=["POST"])
def replace_routine(routine_index):
    progress = load_progress()
    new_template = request.form.get("template", "")
    if routine_index >= len(progress["routines"]) or new_template not in ROUTINE_TEMPLATES:
        flash("Please choose a valid routine.", "danger")
        return redirect(url_for("index"))

    old_template = progress["routines"][routine_index]["template"]
    progress["routines"][routine_index] = build_routine(new_template, random.Random(), load_exercises())
    save_json(PROGRESS_FILE, progress)
    flash(
        f"{DAY_LABELS[routine_index]}: replaced {old_template} with {new_template}. "
        "Exercises you already finished stay in your history.",
        "success",
    )
    return redirect(url_for("index") + f"#routine-{routine_index}")


@app.route("/delete/<slug>", methods=["POST"])
def delete_exercise(slug):
    exercises = load_exercises()
    if slug not in exercises:
        abort(404)
    name = request.form.get("name", "")
    category = exercises[slug]

    # Keep every exercise except the user-added one with this name.
    kept = [ex for ex in category["exercises"] if not (ex["name"] == name and ex.get("custom"))]
    if len(kept) == len(category["exercises"]):
        flash("Only exercises you added can be deleted.", "danger")
    else:
        category["exercises"] = kept
        save_json(EXERCISES_FILE, exercises)
        flash(f"Deleted {name}. It won't be picked for future weeks; your history still shows it.", "success")
    return redirect(url_for("category_detail", slug=slug))


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
