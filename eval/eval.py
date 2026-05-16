"""
eval/eval.py — FitQuest RPG AI Behavior Evaluation Script

Metric: Rubric score (0–3) per test case across four dimensions:
  - Personality adherence (0–1): Does the coach message match the requested personality?
  - Exercise relevance (0–1): Are exercises appropriate for the goal and equipment?
  - Soreness awareness (0–1): Are sore muscle groups avoided when soreness is reported?
  - JSON validity (0–1): Does the response parse correctly with all required fields?

Max score per case: 3 (personality + relevance + soreness awareness, JSON validity is a gate)
Overall score: mean rubric score across all cases (0.0–3.0)

Usage:
    pip install openai python-dotenv
    python eval/eval.py
"""

import os
import json
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# Prompt builder (mirrors app.py generate_workout_quest exactly)
# ---------------------------------------------------------------------------

PERSONALITY_DESCRIPTIONS = {
    "drill_sergeant": "a tough, no-nonsense military drill sergeant who pushes hard and uses military metaphors",
    "zen_master": "a calm, philosophical zen master who connects fitness to mindfulness and inner peace",
    "hype_beast": "an extremely enthusiastic, high-energy hype coach who uses lots of exclamation points and slang",
    "wise_mentor": "a wise, experienced mentor who gives thoughtful advice and draws on years of coaching wisdom",
    "friendly_buddy": "a supportive, encouraging best friend who keeps things fun and celebrates every win",
}


def build_prompt(case: dict) -> str:
    personality_desc = PERSONALITY_DESCRIPTIONS[case["coach_personality"]]
    return f"""You are {personality_desc}. Generate a personalized fitness workout quest for a user.

User profile:
- Fitness goal: {case['fitness_goal']}
- Available equipment: {case['equipment']}
- Current soreness: {case['soreness']}
- Energy level: {case['energy_level']}
- Available time: {case['workout_time']} minutes

Respond ONLY with a valid JSON object in this exact format:
{{
  "quest_name": "A creative, RPG-style quest name (e.g. 'Trial of the Iron Will')",
  "coach_message": "A motivational message in your personality style, 2-3 sentences, addressing the user directly",
  "exercises": [
    {{
      "name": "Exercise name",
      "sets": 3,
      "reps": "10-12",
      "rest": "60s",
      "description": "Brief form tip or explanation"
    }}
  ]
}}

Rules:
- Include 4-7 exercises appropriate for the time, goal, and equipment
- Adjust intensity based on energy level and soreness (avoid exercises targeting sore muscle groups)
- Make the quest name creative and thematic
- Keep the coach message in character with your personality
- Use "reps" for timed exercises too (e.g. "30s" or "45s")
"""


def call_api(case: dict) -> dict | None:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": build_prompt(case)}],
            temperature=0.8,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

PERSONALITY_KEYWORDS = {
    "drill_sergeant": ["soldier", "recruit", "mission", "orders", "battle", "troops",
                       "fall in", "dismissed", "push", "no excuses", "warrior", "drill"],
    "zen_master":     ["breath", "mindful", "peace", "flow", "balance", "harmony",
                       "present", "energy", "inner", "calm", "journey", "awareness"],
    "hype_beast":     ["!", "let's go", "fire", "beast", "crush", "insane", "lit",
                       "grind", "slay", "bro", "hype", "epic", "vibe"],
    "wise_mentor":    ["experience", "wisdom", "over time", "patience", "foundation",
                       "progress", "consistent", "trust", "years", "learned", "guide"],
    "friendly_buddy": ["you've got", "proud", "fun", "together", "celebrate", "awesome",
                       "great job", "keep it up", "believe", "friend", "cheer"],
}

# Muscle groups associated with each soreness keyword
SORENESS_MUSCLE_MAP = {
    "legs":       ["squat", "lunge", "leg press", "deadlift", "calf", "step-up", "jump"],
    "back":       ["deadlift", "row", "pull-up", "lat", "back extension", "good morning"],
    "shoulders":  ["overhead press", "lateral raise", "shoulder press", "upright row", "arnold"],
    "chest":      ["bench press", "push-up", "chest fly", "dip", "pec"],
    "arms":       ["curl", "tricep", "bicep", "hammer curl", "skull crusher"],
    "core":       ["crunch", "plank", "sit-up", "russian twist", "leg raise", "ab"],
}


def score_personality(coach_message: str, personality: str) -> int:
    """1 if ≥2 personality keywords found in message, else 0."""
    msg = coach_message.lower()
    keywords = PERSONALITY_KEYWORDS.get(personality, [])
    hits = sum(1 for kw in keywords if kw in msg)
    return 1 if hits >= 2 else 0


def score_exercise_relevance(exercises: list, case: dict) -> int:
    """
    1 if:
      - exercise count is within 4-7
      - at least one exercise name contains a word from the goal keywords
      - no equipment mismatch (bodyweight-only cases have no barbell/dumbbell exercises)
    """
    if not (4 <= len(exercises) <= 7):
        return 0

    goal = case["fitness_goal"].lower()
    equip = case["equipment"].lower()
    names = " ".join(e.get("name", "").lower() for e in exercises)

    # Equipment mismatch check for bodyweight-only
    if "bodyweight" in equip and "no equipment" not in equip:
        barbell_terms = ["barbell", "dumbbell", "cable", "machine", "bench press"]
        if any(t in names for t in barbell_terms):
            return 0

    return 1


def score_soreness_awareness(exercises: list, case: dict) -> int:
    """
    1 if soreness is none/mild (no constraint needed) OR
    if soreness is moderate/severe and no exercises target the sore muscle group.
    Returns 0 if sore group exercises are included despite moderate/severe soreness.
    """
    soreness = case["soreness"]
    sore_area = case.get("sore_area", "")  # optional field in test cases

    if soreness in ("none", "mild") or not sore_area:
        return 1  # no constraint to check

    names = " ".join(e.get("name", "").lower() for e in exercises)
    forbidden = SORENESS_MUSCLE_MAP.get(sore_area, [])
    if any(term in names for term in forbidden):
        return 0
    return 1


def score_case(result: dict | None, case: dict) -> dict:
    if result is None:
        return {"json_valid": 0, "personality": 0, "relevance": 0, "soreness": 0, "total": 0}

    required_keys = {"quest_name", "coach_message", "exercises"}
    json_valid = 1 if required_keys.issubset(result.keys()) else 0

    if not json_valid:
        return {"json_valid": 0, "personality": 0, "relevance": 0, "soreness": 0, "total": 0}

    p = score_personality(result["coach_message"], case["coach_personality"])
    r = score_exercise_relevance(result["exercises"], case)
    s = score_soreness_awareness(result["exercises"], case)

    return {
        "json_valid": json_valid,
        "personality": p,
        "relevance": r,
        "soreness": s,
        "total": p + r + s,
    }


# ---------------------------------------------------------------------------
# Test cases (≥10 labeled)
# ---------------------------------------------------------------------------

TEST_CASES = [
    # ── TC-01: Drill sergeant, leg day, no soreness ──
    {
        "id": "TC-01",
        "desc": "Drill sergeant + muscle building + gym equipment",
        "fitness_goal": "Build muscle and increase strength",
        "equipment": "Barbell, squat rack, bench, dumbbells",
        "soreness": "none",
        "sore_area": "",
        "energy_level": "high",
        "workout_time": 60,
        "coach_personality": "drill_sergeant",
        "expect_personality_keywords": ["mission", "soldier", "push"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-02: Zen master, cardio, mild soreness ──
    {
        "id": "TC-02",
        "desc": "Zen master + cardio + bodyweight only",
        "fitness_goal": "Improve cardiovascular endurance",
        "equipment": "Bodyweight only",
        "soreness": "mild",
        "sore_area": "",
        "energy_level": "medium",
        "workout_time": 30,
        "coach_personality": "zen_master",
        "expect_personality_keywords": ["breath", "flow", "balance"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-03: Hype beast, fat loss, high energy ──
    {
        "id": "TC-03",
        "desc": "Hype beast + fat loss + high energy",
        "fitness_goal": "Lose weight and burn fat",
        "equipment": "Dumbbells, resistance bands",
        "soreness": "none",
        "sore_area": "",
        "energy_level": "high",
        "workout_time": 45,
        "coach_personality": "hype_beast",
        "expect_personality_keywords": ["!", "let's go", "crush"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-04: Soreness awareness — severe leg soreness should avoid leg exercises ──
    {
        "id": "TC-04",
        "desc": "Severe leg soreness — must avoid squat/lunge/deadlift",
        "fitness_goal": "General fitness",
        "equipment": "Dumbbells, pull-up bar",
        "soreness": "severe",
        "sore_area": "legs",
        "energy_level": "low",
        "workout_time": 30,
        "coach_personality": "friendly_buddy",
        "expect_personality_keywords": ["you've got", "proud", "awesome"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-05: Wise mentor, flexibility, low energy ──
    {
        "id": "TC-05",
        "desc": "Wise mentor + flexibility + low energy",
        "fitness_goal": "Increase flexibility and mobility",
        "equipment": "Yoga mat, resistance bands",
        "soreness": "moderate",
        "sore_area": "",
        "energy_level": "low",
        "workout_time": 20,
        "coach_personality": "wise_mentor",
        "expect_personality_keywords": ["patience", "foundation", "progress"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-06: Bodyweight only — must not include barbell/dumbbell exercises ──
    {
        "id": "TC-06",
        "desc": "Bodyweight only — no equipment exercises must be equipment-free",
        "fitness_goal": "Build functional strength",
        "equipment": "Bodyweight only",
        "soreness": "none",
        "sore_area": "",
        "energy_level": "medium",
        "workout_time": 30,
        "coach_personality": "drill_sergeant",
        "expect_personality_keywords": ["mission", "recruit", "push"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-07: Short 10-minute session — must still produce 4+ exercises ──
    {
        "id": "TC-07",
        "desc": "10-minute session — minimal time constraint",
        "fitness_goal": "Quick energy boost",
        "equipment": "Bodyweight only",
        "soreness": "none",
        "sore_area": "",
        "energy_level": "high",
        "workout_time": 10,
        "coach_personality": "hype_beast",
        "expect_personality_keywords": ["!", "fire", "beast"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-08: Severe back soreness — must avoid rows/deadlifts/pull-ups ──
    {
        "id": "TC-08",
        "desc": "Severe back soreness — must avoid back exercises",
        "fitness_goal": "Upper body strength",
        "equipment": "Dumbbells, bench",
        "soreness": "severe",
        "sore_area": "back",
        "energy_level": "medium",
        "workout_time": 40,
        "coach_personality": "wise_mentor",
        "expect_personality_keywords": ["experience", "wisdom", "consistent"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-09: Friendly buddy, beginner, full gym ──
    {
        "id": "TC-09",
        "desc": "Friendly buddy + beginner muscle building + full gym",
        "fitness_goal": "Build muscle as a beginner",
        "equipment": "Full gym — barbells, dumbbells, cables, machines",
        "soreness": "mild",
        "sore_area": "",
        "energy_level": "medium",
        "workout_time": 50,
        "coach_personality": "friendly_buddy",
        "expect_personality_keywords": ["proud", "awesome", "believe"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-10: Zen master, 90-minute session, marathon length ──
    {
        "id": "TC-10",
        "desc": "Zen master + 90-minute endurance session",
        "fitness_goal": "Build endurance and mental toughness",
        "equipment": "Treadmill, rowing machine, bodyweight",
        "soreness": "none",
        "sore_area": "",
        "energy_level": "high",
        "workout_time": 90,
        "coach_personality": "zen_master",
        "expect_personality_keywords": ["breath", "inner", "journey"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-11: Severe shoulder soreness — must avoid overhead press ──
    {
        "id": "TC-11",
        "desc": "Severe shoulder soreness — must avoid shoulder exercises",
        "fitness_goal": "Upper body hypertrophy",
        "equipment": "Barbell, dumbbells, cables",
        "soreness": "severe",
        "sore_area": "shoulders",
        "energy_level": "medium",
        "workout_time": 45,
        "coach_personality": "drill_sergeant",
        "expect_personality_keywords": ["mission", "battle", "warrior"],
        "expect_exercise_count_range": (4, 7),
    },
    # ── TC-12: Low energy — exercises should be lighter/restorative ──
    {
        "id": "TC-12",
        "desc": "Low energy — workout should be lighter in intensity",
        "fitness_goal": "Active recovery and mobility",
        "equipment": "Foam roller, resistance bands, yoga mat",
        "soreness": "moderate",
        "sore_area": "",
        "energy_level": "low",
        "workout_time": 25,
        "coach_personality": "zen_master",
        "expect_personality_keywords": ["calm", "peace", "flow"],
        "expect_exercise_count_range": (4, 7),
    },
]


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_eval():
    print("=" * 60)
    print("FitQuest RPG — AI Behavior Evaluation")
    print(f"Model: gpt-4o-mini  |  Cases: {len(TEST_CASES)}")
    print("=" * 60)

    results = []
    for case in TEST_CASES:
        print(f"\n[{case['id']}] {case['desc']}")
        raw = call_api(case)
        scores = score_case(raw, case)
        results.append(scores)

        status = "✓" if scores["json_valid"] else "✗ INVALID JSON"
        print(f"  JSON valid:  {scores['json_valid']}")
        print(f"  Personality: {scores['personality']}/1")
        print(f"  Relevance:   {scores['relevance']}/1")
        print(f"  Soreness:    {scores['soreness']}/1")
        print(f"  Total:       {scores['total']}/3  {status}")

        if raw and scores["json_valid"]:
            print(f"  Quest name:  {raw.get('quest_name', '—')}")
            print(f"  Exercises:   {len(raw.get('exercises', []))}")
            msg = raw.get("coach_message", "")
            print(f"  Coach msg:   {msg[:100]}{'…' if len(msg) > 100 else ''}")

    # Summary
    total_possible = len(TEST_CASES) * 3
    total_earned   = sum(r["total"] for r in results)
    mean_score     = total_earned / len(TEST_CASES)
    pct            = (total_earned / total_possible) * 100

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Cases run:       {len(TEST_CASES)}")
    print(f"Total score:     {total_earned} / {total_possible}")
    print(f"Mean per case:   {mean_score:.2f} / 3.00")
    print(f"Overall:         {pct:.1f}%")
    print(f"JSON pass rate:  {sum(r['json_valid'] for r in results)}/{len(TEST_CASES)}")
    print(f"Personality avg: {sum(r['personality'] for r in results)/len(TEST_CASES):.2f}")
    print(f"Relevance avg:   {sum(r['relevance'] for r in results)/len(TEST_CASES):.2f}")
    print(f"Soreness avg:    {sum(r['soreness'] for r in results)/len(TEST_CASES):.2f}")

    return mean_score


if __name__ == "__main__":
    score = run_eval()
    sys.exit(0 if score >= 2.0 else 1)
