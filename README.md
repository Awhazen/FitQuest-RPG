# FitQuest RPG

A Flask-powered fitness RPG web app that turns your daily workouts into epic quests. Earn XP, level up, maintain streaks, and get personalized coaching from an AI coach powered by the OpenAI API.

---

## Features

- **AI-generated workout quests** — unique quest names, exercises, and coach messages tailored to your inputs
- **5 coach personalities** — Drill Sergeant, Zen Master, Hype Beast, Wise Mentor, Friendly Buddy
- **XP & leveling system** — earn XP based on workout duration, energy, and soreness
- **Streak tracking** — consecutive daily workout streaks
- **Workout history** — all completed quests stored locally in SQLite
- **Dark RPG UI** — clean, responsive dark theme

---

## Setup

### 1. Clone / download the project

```bash
git clone <repo-url>
cd fitquest-rpg
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-your-actual-openai-api-key
FLASK_SECRET_KEY=some-random-secret-string
```

> Get your OpenAI API key at https://platform.openai.com/api-keys

### 5. Run the app

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## Project Structure

```
fitquest-rpg/
├── app.py              # Flask app - routes, DB logic, XP/reward system
├── schema.sql          # SQLite schema (auto applied on first run)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── README.md
├── REPORT.md           # Project report (What & why, Iterations, Walkthrough, Safety)
├── eval/
│   └── eval.py         # AI behavior evaluation script (12 labeled test cases)
├── static/
│   ├── style.css       # Dark RPG theme
│   └── app.js          # Loading states, quest completion, modal, hamburger nav
└── templates/
    ├── base.html       # Shared layout, nav, flash messages
    ├── login.html      # Login page
    ├── register.html   # Registration page
    ├── dashboard.html  # Main dashboard — stats, active quest, history
    ├── generate.html   # Workout generation form
    ├── workout.html    # Individual quest detail view
    └── achievements.html  # Achievement gallery
```

---

## How It Works

### OpenAI API (AI responsibilities)
- Generates a creative RPG-style quest name
- Writes a personalized coach message in the chosen personality
- Selects and describes exercises appropriate for the user's inputs

### Backend (Flask responsibilities)
- XP calculation based on workout time, energy level, and soreness
- Level-up logic with scaling XP thresholds
- Streak tracking (consecutive daily workouts)
- All data stored in local SQLite (`fitness_rpg.db`)

### XP Formula
```
base_xp = workout_time_minutes × 2
energy_multiplier = 0.8 (low) | 1.0 (medium) | 1.2 (high)
soreness_bonus = 0 (none) | 5 (mild) | 10 (moderate) | 15 (severe)

xp_reward = (base_xp × energy_multiplier) + soreness_bonus
```

### Level Scaling
Each level requires ~40% more XP than the previous:
- Level 1 -> 2: 100 XP
- Level 2 -> 3: 140 XP
- Level 3 -> 4: 196 XP
- ...and so on

---

## Notes

- The SQLite database (`fitness_rpg.db`) is created automatically on first run
- Multiple users are supported so each account has its own profile, XP, and history
- The app uses `gpt-4o-mini` by default (fast and cost-effective); change the model name in `app.py` if needed
- Sessions persist for 30 days so you won't need to log in again after restarting the server
