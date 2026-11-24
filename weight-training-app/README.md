# Weight Training App

A small Flask web app that plans four weight-training workouts each week and tracks the ones you complete. It has a library of exercises for seven body parts: back, chest, legs, biceps, triceps, abdominals and shoulders. Each body part has dumbbell, barbell, body weight and kettlebell options. Every Monday the app picks a new set of exercises for the week's four routines: Push, Pull, Legs & Abs, and Full Body. You can check off exercises as you finish them, swap a routine for a different one, add your own exercises, and look back at everything you've completed on the History page.

The app was built for the CIS 2020 Capstone. It uses Flask, Jinja templates, and Bootstrap 5 with the [Lux theme from Bootswatch](https://bootswatch.com/lux/). There is no database: all data is stored in JSON files.

## Features

- **This Week (home page):** shows the week's 4 routines (Monday, Tuesday, Thursday, Friday) with suggested sets and reps, plus a progress bar for the week.
  - Click **Mark done** to complete an exercise, or click **Done ✓** again to undo it.
  - Use **Replace** to swap any routine for a different one. There are 9 routine types to choose from.
- **New exercises every week:** the exercises are picked at random using the week number. The plan stays the same all week and changes every Monday.
- **Exercises:** lists all 7 body parts. Click one to see its exercises, and filter them by equipment type.
- **Add Exercise:** a form for adding a new exercise to any body part. It checks your input, such as missing fields or duplicate names. Exercises you add can be deleted later. The built-in ones can't.
- **History:** lists every completed exercise grouped by date, with totals for all time, this week, days trained, and each body part.

## Project structure

```
weight-training-app/
├── app.py                  # Flask app: routes, weekly planning, reading/writing JSON
├── requirements.txt        # Python packages: Flask and gunicorn
├── README.md               # This file
├── data/
│   ├── exercises.json      # Exercise library, grouped by body part
│   └── progress.json       # Created automatically: this week's routines + history
└── templates/
    ├── base.html           # Shared layout: navbar, messages, footer
    ├── index.html          # This Week (home page)
    ├── categories.html     # All body parts
    ├── category.html       # Exercises for one body part
    ├── add_exercise.html   # Add Exercise form
    ├── history.html        # Completed workouts
    └── 404.html            # Page not found
```

## Pages and routes

| URL | Page / action |
|---|---|
| `/` | This Week: the 4 routines for the current week |
| `/exercises` | All exercise categories |
| `/exercises/<body-part>` | Exercises for one body part (add `?equipment=Barbell` to filter) |
| `/add` | Add Exercise form |
| `/history` | Completed workouts |
| `/complete/<routine>/<exercise>` | (form action) Mark an exercise done or undone |
| `/replace/<routine>` | (form action) Replace a routine |
| `/delete/<body-part>` | (form action) Delete an exercise you added |

## Running the app on your computer

You need Python 3.9 or newer.

```
cd weight-training-app
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000> in your browser. Press **Ctrl+C** in the terminal to stop the server.

## How the data is stored

- **`data/exercises.json`** holds the exercise library. Each exercise has a name, equipment type, suggested sets and reps, and a short description. Exercises added through the form also have `"custom": true`, which is what allows them to be deleted.
- **`data/progress.json`** is created the first time the app runs. It stores the current week, the 4 routines (including which exercises are done), and your workout history. Delete this file to start over with an empty history.

## Changing the default routines

The routine types and the four default routines are defined near the top of `app.py`:

```python
ROUTINE_TEMPLATES = {
    "Push": {"chest": 2, "shoulders": 2, "triceps": 1},
    ...
}
DEFAULT_WEEK = ["Push", "Pull", "Legs & Abs", "Full Body"]
```

Each routine lists how many exercises to pick from each body part. Changes take effect at the start of the next week, or right away if you delete `data/progress.json`.

## Deploying

When you put the app online, set a `SECRET_KEY` environment variable on the hosting service. Flask uses the key to sign the pop-up messages. To generate one:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Most hosts (such as Render or Railway) run the app with gunicorn:

```
gunicorn app:app
```

gunicorn only runs on Linux and macOS, so use `python app.py` when working on Windows.

Many hosting services reset their files whenever the app restarts or is redeployed. If that happens, exercises you added and your workout history will be lost. A database would fix this, but this project keeps its data in JSON files on purpose.
