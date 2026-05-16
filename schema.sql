-- Fitness RPG Database Schema

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    xp_to_next_level INTEGER NOT NULL DEFAULT 100,
    streak INTEGER NOT NULL DEFAULT 0,
    last_workout_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quest_name TEXT NOT NULL,
    coach_message TEXT NOT NULL,
    exercises TEXT NOT NULL,         -- JSON array of exercise objects
    fitness_goal TEXT NOT NULL,
    equipment TEXT NOT NULL,
    soreness TEXT NOT NULL,
    energy_level TEXT NOT NULL,
    workout_time INTEGER NOT NULL,   -- minutes
    coach_personality TEXT NOT NULL,
    xp_reward INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,  -- 0 = pending, 1 = completed
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_key TEXT NOT NULL,   -- unique identifier e.g. "first_quest"
    unlocked_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, achievement_key),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
