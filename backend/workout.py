"""
Workout Agent - Core Module
Tracks progress, generates mixed workouts, adapts to user needs.
In-memory storage with optional file persistence.
"""

import json
import logging
import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger('workout')


# ============ Enums ============

class MuscleGroup(str, Enum):
    CHEST = "chest"
    BACK = "back"
    SHOULDERS = "shoulders"
    BICEPS = "biceps"
    TRICEPS = "triceps"
    LEGS = "legs"
    CORE = "core"
    GLUTES = "glutes"
    FULL_BODY = "full_body"


class WorkoutType(str, Enum):
    STRENGTH = "strength"
    CARDIO = "cardio"
    HIIT = "hiit"
    FLEXIBILITY = "flexibility"
    MIXED = "mixed"


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class GoalType(str, Enum):
    LOSE_WEIGHT = "lose_weight"
    BUILD_MUSCLE = "build_muscle"
    IMPROVE_ENDURANCE = "improve_endurance"
    STAY_ACTIVE = "stay_active"
    INCREASE_FLEXIBILITY = "increase_flexibility"


# ============ Data Models ============

@dataclass
class Exercise:
    id: str
    name: str
    name_he: str
    muscle_groups: List[MuscleGroup]
    workout_type: WorkoutType
    difficulty: Difficulty
    default_sets: int
    default_reps: int  # or seconds for timed exercises
    is_timed: bool = False  # True = reps field means seconds
    equipment: Optional[str] = None
    description: str = ""
    calories_per_set: float = 5.0


@dataclass
class ExerciseEntry:
    """A single exercise within a workout session"""
    exercise_id: str
    exercise_name: str
    sets: int
    reps: int
    weight_kg: Optional[float] = None
    is_timed: bool = False
    completed: bool = False
    notes: str = ""


@dataclass
class WorkoutSession:
    """A completed or planned workout session"""
    id: str
    date: str  # ISO date
    workout_type: WorkoutType
    exercises: List[Dict[str, Any]]
    duration_minutes: int = 0
    calories_burned: float = 0
    completed: bool = False
    rating: Optional[int] = None  # 1-5 user satisfaction
    notes: str = ""
    created_at: str = ""


@dataclass
class UserProfile:
    """User fitness profile and preferences"""
    goal: GoalType = GoalType.STAY_ACTIVE
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    workouts_per_week: int = 3
    preferred_types: List[WorkoutType] = field(default_factory=lambda: [
        WorkoutType.STRENGTH, WorkoutType.CARDIO
    ])
    excluded_exercises: List[str] = field(default_factory=list)
    available_equipment: List[str] = field(default_factory=lambda: ["bodyweight"])


@dataclass
class WeeklySummary:
    """Weekly workout summary"""
    week_start: str
    week_end: str
    total_workouts: int
    total_duration_minutes: int
    total_calories: float
    workouts_by_type: Dict[str, int]
    muscle_groups_hit: Dict[str, int]
    avg_rating: Optional[float]
    streak_days: int
    goal_progress: str  # e.g., "3/4 workouts completed"


# ============ Exercise Library ============

EXERCISES: List[Exercise] = [
    # === CHEST ===
    Exercise("push_up", "Push-ups", "שכיבות סמיכה",
             [MuscleGroup.CHEST, MuscleGroup.TRICEPS], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 12, calories_per_set=8),
    Exercise("diamond_push_up", "Diamond Push-ups", "שכיבות סמיכה יהלום",
             [MuscleGroup.CHEST, MuscleGroup.TRICEPS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 10, calories_per_set=9),
    Exercise("decline_push_up", "Decline Push-ups", "שכיבות סמיכה משופעות",
             [MuscleGroup.CHEST, MuscleGroup.SHOULDERS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 10, calories_per_set=9),
    Exercise("bench_press", "Bench Press", "לחיצת חזה",
             [MuscleGroup.CHEST, MuscleGroup.TRICEPS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 4, 10, equipment="barbell", calories_per_set=12),
    Exercise("dumbbell_fly", "Dumbbell Fly", "פתיחות משקולות",
             [MuscleGroup.CHEST], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 12, equipment="dumbbells", calories_per_set=8),

    # === BACK ===
    Exercise("pull_up", "Pull-ups", "מתח",
             [MuscleGroup.BACK, MuscleGroup.BICEPS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 8, calories_per_set=10),
    Exercise("inverted_row", "Inverted Row", "חתירה הפוכה",
             [MuscleGroup.BACK], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 10, calories_per_set=7),
    Exercise("superman", "Superman Hold", "סופרמן",
             [MuscleGroup.BACK, MuscleGroup.GLUTES], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 30, is_timed=True, calories_per_set=5),
    Exercise("dumbbell_row", "Dumbbell Row", "חתירת משקולת",
             [MuscleGroup.BACK, MuscleGroup.BICEPS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 12, equipment="dumbbells", calories_per_set=9),

    # === SHOULDERS ===
    Exercise("pike_push_up", "Pike Push-ups", "שכיבות סמיכה פייק",
             [MuscleGroup.SHOULDERS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 10, calories_per_set=8),
    Exercise("lateral_raise", "Lateral Raise", "הרמה צידית",
             [MuscleGroup.SHOULDERS], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 15, equipment="dumbbells", calories_per_set=6),
    Exercise("shoulder_press", "Shoulder Press", "לחיצת כתפיים",
             [MuscleGroup.SHOULDERS, MuscleGroup.TRICEPS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 10, equipment="dumbbells", calories_per_set=10),

    # === ARMS ===
    Exercise("bicep_curl", "Bicep Curl", "כפיפת מרפק",
             [MuscleGroup.BICEPS], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 12, equipment="dumbbells", calories_per_set=6),
    Exercise("tricep_dip", "Tricep Dips", "שקיעות טרייספס",
             [MuscleGroup.TRICEPS], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 12, calories_per_set=7),
    Exercise("hammer_curl", "Hammer Curl", "כפיפה פטיש",
             [MuscleGroup.BICEPS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 12, equipment="dumbbells", calories_per_set=6),

    # === LEGS ===
    Exercise("squat", "Bodyweight Squat", "סקוואט",
             [MuscleGroup.LEGS, MuscleGroup.GLUTES], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 15, calories_per_set=10),
    Exercise("lunge", "Lunges", "לאנג'ים",
             [MuscleGroup.LEGS, MuscleGroup.GLUTES], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 12, calories_per_set=9),
    Exercise("jump_squat", "Jump Squats", "סקוואט קפיצה",
             [MuscleGroup.LEGS, MuscleGroup.GLUTES], WorkoutType.HIIT,
             Difficulty.INTERMEDIATE, 3, 12, calories_per_set=14),
    Exercise("wall_sit", "Wall Sit", "ישיבת קיר",
             [MuscleGroup.LEGS], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 45, is_timed=True, calories_per_set=8),
    Exercise("calf_raise", "Calf Raises", "הרמת עקבים",
             [MuscleGroup.LEGS], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 20, calories_per_set=5),
    Exercise("bulgarian_split_squat", "Bulgarian Split Squat", "סקוואט בולגרי",
             [MuscleGroup.LEGS, MuscleGroup.GLUTES], WorkoutType.STRENGTH,
             Difficulty.ADVANCED, 3, 10, calories_per_set=12),

    # === CORE ===
    Exercise("plank", "Plank", "פלאנק",
             [MuscleGroup.CORE], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 45, is_timed=True, calories_per_set=6),
    Exercise("crunch", "Crunches", "כפיפות בטן",
             [MuscleGroup.CORE], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 20, calories_per_set=5),
    Exercise("mountain_climber", "Mountain Climbers", "מטפסי הרים",
             [MuscleGroup.CORE, MuscleGroup.FULL_BODY], WorkoutType.HIIT,
             Difficulty.INTERMEDIATE, 3, 30, is_timed=True, calories_per_set=12),
    Exercise("russian_twist", "Russian Twist", "סיבוב רוסי",
             [MuscleGroup.CORE], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 20, calories_per_set=7),
    Exercise("leg_raise", "Leg Raises", "הרמת רגליים",
             [MuscleGroup.CORE], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 15, calories_per_set=7),
    Exercise("bicycle_crunch", "Bicycle Crunch", "אופניים",
             [MuscleGroup.CORE], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 20, calories_per_set=8),

    # === GLUTES ===
    Exercise("glute_bridge", "Glute Bridge", "גשר ישבן",
             [MuscleGroup.GLUTES], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 15, calories_per_set=6),
    Exercise("hip_thrust", "Hip Thrust", "דחיפת ירכיים",
             [MuscleGroup.GLUTES, MuscleGroup.LEGS], WorkoutType.STRENGTH,
             Difficulty.INTERMEDIATE, 3, 12, calories_per_set=10),
    Exercise("donkey_kick", "Donkey Kicks", "בעיטות חמור",
             [MuscleGroup.GLUTES], WorkoutType.STRENGTH,
             Difficulty.BEGINNER, 3, 15, calories_per_set=5),

    # === CARDIO ===
    Exercise("jumping_jack", "Jumping Jacks", "ג'מפינג ג'ק",
             [MuscleGroup.FULL_BODY], WorkoutType.CARDIO,
             Difficulty.BEGINNER, 3, 60, is_timed=True, calories_per_set=12),
    Exercise("high_knees", "High Knees", "הרמת ברכיים",
             [MuscleGroup.FULL_BODY, MuscleGroup.CORE], WorkoutType.CARDIO,
             Difficulty.BEGINNER, 3, 45, is_timed=True, calories_per_set=14),
    Exercise("burpee", "Burpees", "בורפי",
             [MuscleGroup.FULL_BODY], WorkoutType.HIIT,
             Difficulty.ADVANCED, 3, 10, calories_per_set=15),
    Exercise("running_in_place", "Running in Place", "ריצה במקום",
             [MuscleGroup.FULL_BODY, MuscleGroup.LEGS], WorkoutType.CARDIO,
             Difficulty.BEGINNER, 3, 60, is_timed=True, calories_per_set=10),
    Exercise("box_jump", "Box Jumps", "קפיצה על קופסה",
             [MuscleGroup.LEGS, MuscleGroup.GLUTES], WorkoutType.HIIT,
             Difficulty.ADVANCED, 3, 10, equipment="box", calories_per_set=12),
    Exercise("skater_jump", "Skater Jumps", "קפיצות גלשן",
             [MuscleGroup.LEGS, MuscleGroup.GLUTES], WorkoutType.HIIT,
             Difficulty.INTERMEDIATE, 3, 30, is_timed=True, calories_per_set=11),

    # === FLEXIBILITY ===
    Exercise("hamstring_stretch", "Hamstring Stretch", "מתיחת ירכיים אחוריות",
             [MuscleGroup.LEGS], WorkoutType.FLEXIBILITY,
             Difficulty.BEGINNER, 2, 30, is_timed=True, calories_per_set=2),
    Exercise("quad_stretch", "Quad Stretch", "מתיחת ירך קדמית",
             [MuscleGroup.LEGS], WorkoutType.FLEXIBILITY,
             Difficulty.BEGINNER, 2, 30, is_timed=True, calories_per_set=2),
    Exercise("shoulder_stretch", "Shoulder Stretch", "מתיחת כתפיים",
             [MuscleGroup.SHOULDERS], WorkoutType.FLEXIBILITY,
             Difficulty.BEGINNER, 2, 30, is_timed=True, calories_per_set=2),
    Exercise("cat_cow", "Cat-Cow Stretch", "חתול-פרה",
             [MuscleGroup.BACK, MuscleGroup.CORE], WorkoutType.FLEXIBILITY,
             Difficulty.BEGINNER, 2, 30, is_timed=True, calories_per_set=3),
    Exercise("child_pose", "Child's Pose", "תנוחת ילד",
             [MuscleGroup.BACK, MuscleGroup.SHOULDERS], WorkoutType.FLEXIBILITY,
             Difficulty.BEGINNER, 2, 45, is_timed=True, calories_per_set=2),
    Exercise("pigeon_pose", "Pigeon Pose", "תנוחת יונה",
             [MuscleGroup.GLUTES, MuscleGroup.LEGS], WorkoutType.FLEXIBILITY,
             Difficulty.INTERMEDIATE, 2, 45, is_timed=True, calories_per_set=3),
]

EXERCISE_MAP = {e.id: e for e in EXERCISES}


# ============ Workout Generator ============

class WorkoutGenerator:
    """Generates workouts based on user profile and history"""

    def __init__(self):
        self.exercises = EXERCISES
        self.exercise_map = EXERCISE_MAP

    def _filter_exercises(
        self,
        workout_type: Optional[WorkoutType] = None,
        muscle_groups: Optional[List[MuscleGroup]] = None,
        difficulty: Optional[Difficulty] = None,
        equipment: Optional[List[str]] = None,
        excluded: Optional[List[str]] = None
    ) -> List[Exercise]:
        """Filter exercises by criteria"""
        result = list(self.exercises)

        if workout_type and workout_type != WorkoutType.MIXED:
            result = [e for e in result if e.workout_type == workout_type]

        if muscle_groups:
            result = [e for e in result
                      if any(mg in e.muscle_groups for mg in muscle_groups)]

        if difficulty:
            diff_order = [Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.ADVANCED]
            max_idx = diff_order.index(difficulty)
            allowed = diff_order[:max_idx + 1]
            result = [e for e in result if e.difficulty in allowed]

        if equipment:
            result = [e for e in result
                      if e.equipment is None or e.equipment in equipment]

        if excluded:
            result = [e for e in result if e.id not in excluded]

        return result

    def generate_workout(
        self,
        profile: UserProfile,
        workout_type: Optional[WorkoutType] = None,
        target_muscles: Optional[List[MuscleGroup]] = None,
        duration_minutes: int = 30,
        history: Optional[List[WorkoutSession]] = None
    ) -> Dict[str, Any]:
        """Generate a workout plan based on profile and preferences"""

        w_type = workout_type or random.choice(profile.preferred_types)

        # For mixed workouts, combine multiple types
        if w_type == WorkoutType.MIXED:
            return self._generate_mixed_workout(profile, target_muscles, duration_minutes, history)

        available = self._filter_exercises(
            workout_type=w_type,
            muscle_groups=target_muscles,
            difficulty=profile.difficulty,
            equipment=profile.available_equipment,
            excluded=profile.excluded_exercises
        )

        if not available:
            # Fallback to any matching difficulty
            available = self._filter_exercises(
                difficulty=profile.difficulty,
                equipment=profile.available_equipment,
                excluded=profile.excluded_exercises
            )

        # Determine exercise count based on duration
        exercises_count = max(4, min(10, duration_minutes // 5))

        # Bias toward less-recently-used exercises
        recently_used = set()
        if history:
            for session in history[-3:]:
                for ex in session.exercises:
                    recently_used.add(ex.get("exercise_id", ""))

        # Weighted selection: prefer exercises not recently used
        weights = []
        for ex in available:
            w = 1.0
            if ex.id in recently_used:
                w = 0.3
            weights.append(w)

        selected = []
        pool = list(available)
        pool_weights = list(weights)

        for _ in range(min(exercises_count, len(pool))):
            if not pool:
                break
            total = sum(pool_weights)
            if total == 0:
                break
            normalized = [w / total for w in pool_weights]
            choice_idx = random.choices(range(len(pool)), weights=normalized, k=1)[0]
            selected.append(pool[choice_idx])
            pool.pop(choice_idx)
            pool_weights.pop(choice_idx)

        # Build exercise entries with appropriate sets/reps for goal
        exercises = []
        for ex in selected:
            sets, reps = self._adjust_for_goal(ex, profile.goal)
            entry = {
                "exercise_id": ex.id,
                "exercise_name": ex.name,
                "exercise_name_he": ex.name_he,
                "sets": sets,
                "reps": reps,
                "is_timed": ex.is_timed,
                "muscle_groups": [mg.value for mg in ex.muscle_groups],
                "equipment": ex.equipment,
                "completed": False
            }
            exercises.append(entry)

        # Estimate calories
        total_calories = sum(
            EXERCISE_MAP.get(e["exercise_id"], Exercise("", "", "", [], WorkoutType.STRENGTH, Difficulty.BEGINNER, 0, 0)).calories_per_set * e["sets"]
            for e in exercises
        )

        session_id = str(uuid.uuid4())[:8]
        return {
            "id": session_id,
            "date": date.today().isoformat(),
            "workout_type": w_type.value,
            "exercises": exercises,
            "duration_minutes": duration_minutes,
            "estimated_calories": round(total_calories),
            "difficulty": profile.difficulty.value,
            "completed": False,
            "created_at": datetime.now().isoformat()
        }

    def _generate_mixed_workout(
        self,
        profile: UserProfile,
        target_muscles: Optional[List[MuscleGroup]],
        duration_minutes: int,
        history: Optional[List[WorkoutSession]]
    ) -> Dict[str, Any]:
        """Generate a mixed workout combining strength, cardio, and flexibility"""

        exercises = []
        exercises_count = max(6, min(12, duration_minutes // 4))

        # Allocate: 50% strength, 30% cardio/HIIT, 20% flexibility
        strength_count = max(2, int(exercises_count * 0.5))
        cardio_count = max(2, int(exercises_count * 0.3))
        flex_count = max(1, exercises_count - strength_count - cardio_count)

        recently_used = set()
        if history:
            for session in history[-3:]:
                for ex in session.exercises:
                    recently_used.add(ex.get("exercise_id", ""))

        # Collect from each type
        for w_type, count in [
            (WorkoutType.STRENGTH, strength_count),
            (WorkoutType.CARDIO, cardio_count),
            (WorkoutType.FLEXIBILITY, flex_count)
        ]:
            pool = self._filter_exercises(
                workout_type=w_type,
                muscle_groups=target_muscles,
                difficulty=profile.difficulty,
                equipment=profile.available_equipment,
                excluded=profile.excluded_exercises
            )
            # Also include HIIT for cardio slot
            if w_type == WorkoutType.CARDIO:
                hiit = self._filter_exercises(
                    workout_type=WorkoutType.HIIT,
                    muscle_groups=target_muscles,
                    difficulty=profile.difficulty,
                    equipment=profile.available_equipment,
                    excluded=profile.excluded_exercises
                )
                pool.extend(hiit)

            random.shuffle(pool)
            # Prefer non-recently-used
            pool.sort(key=lambda e: 1 if e.id in recently_used else 0)

            used_ids = {e["exercise_id"] for e in exercises}
            for ex in pool:
                if len([e for e in exercises if EXERCISE_MAP.get(e["exercise_id"], ex).workout_type == w_type or
                        (w_type == WorkoutType.CARDIO and EXERCISE_MAP.get(e["exercise_id"], ex).workout_type == WorkoutType.HIIT)]) >= count:
                    break
                if ex.id not in used_ids:
                    sets, reps = self._adjust_for_goal(ex, profile.goal)
                    exercises.append({
                        "exercise_id": ex.id,
                        "exercise_name": ex.name,
                        "exercise_name_he": ex.name_he,
                        "sets": sets,
                        "reps": reps,
                        "is_timed": ex.is_timed,
                        "muscle_groups": [mg.value for mg in ex.muscle_groups],
                        "equipment": ex.equipment,
                        "completed": False
                    })
                    used_ids.add(ex.id)

        # Shuffle for variety but keep flexibility at end
        strength_ex = [e for e in exercises if EXERCISE_MAP.get(e["exercise_id"]) and EXERCISE_MAP[e["exercise_id"]].workout_type == WorkoutType.STRENGTH]
        cardio_ex = [e for e in exercises if EXERCISE_MAP.get(e["exercise_id"]) and EXERCISE_MAP[e["exercise_id"]].workout_type in (WorkoutType.CARDIO, WorkoutType.HIIT)]
        flex_ex = [e for e in exercises if EXERCISE_MAP.get(e["exercise_id"]) and EXERCISE_MAP[e["exercise_id"]].workout_type == WorkoutType.FLEXIBILITY]

        random.shuffle(strength_ex)
        random.shuffle(cardio_ex)
        # Interleave strength and cardio, end with flexibility
        ordered = []
        si, ci = 0, 0
        while si < len(strength_ex) or ci < len(cardio_ex):
            if si < len(strength_ex):
                ordered.append(strength_ex[si])
                si += 1
            if ci < len(cardio_ex):
                ordered.append(cardio_ex[ci])
                ci += 1
        ordered.extend(flex_ex)

        total_calories = sum(
            EXERCISE_MAP.get(e["exercise_id"], Exercise("", "", "", [], WorkoutType.STRENGTH, Difficulty.BEGINNER, 0, 0)).calories_per_set * e["sets"]
            for e in ordered
        )

        session_id = str(uuid.uuid4())[:8]
        return {
            "id": session_id,
            "date": date.today().isoformat(),
            "workout_type": WorkoutType.MIXED.value,
            "exercises": ordered,
            "duration_minutes": duration_minutes,
            "estimated_calories": round(total_calories),
            "difficulty": profile.difficulty.value,
            "completed": False,
            "created_at": datetime.now().isoformat()
        }

    def _adjust_for_goal(self, exercise: Exercise, goal: GoalType) -> tuple:
        """Adjust sets/reps based on fitness goal"""
        sets = exercise.default_sets
        reps = exercise.default_reps

        if goal == GoalType.BUILD_MUSCLE:
            sets = min(sets + 1, 5)
            if not exercise.is_timed:
                reps = max(6, reps - 4)  # heavier, fewer reps
        elif goal == GoalType.LOSE_WEIGHT:
            if not exercise.is_timed:
                reps = reps + 5  # more reps, lighter
            else:
                reps = int(reps * 1.3)  # longer duration
        elif goal == GoalType.IMPROVE_ENDURANCE:
            sets = max(sets, 4)
            if not exercise.is_timed:
                reps = reps + 3
            else:
                reps = int(reps * 1.5)
        elif goal == GoalType.INCREASE_FLEXIBILITY:
            if exercise.is_timed:
                reps = int(reps * 1.5)

        return sets, reps


# ============ Progress Tracker ============

class ProgressTracker:
    """Tracks workout history and progress"""

    def __init__(self, data_dir: str = "/tmp/workout_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: List[Dict[str, Any]] = []
        self.profile = UserProfile()
        self._load_data()

    def _load_data(self):
        """Load persisted data"""
        sessions_file = self.data_dir / "sessions.json"
        profile_file = self.data_dir / "profile.json"

        if sessions_file.exists():
            try:
                with open(sessions_file) as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} workout sessions")
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
                self.sessions = []

        if profile_file.exists():
            try:
                with open(profile_file) as f:
                    data = json.load(f)
                self.profile = UserProfile(
                    goal=GoalType(data.get("goal", "stay_active")),
                    difficulty=Difficulty(data.get("difficulty", "intermediate")),
                    workouts_per_week=data.get("workouts_per_week", 3),
                    preferred_types=[WorkoutType(t) for t in data.get("preferred_types", ["strength", "cardio"])],
                    excluded_exercises=data.get("excluded_exercises", []),
                    available_equipment=data.get("available_equipment", ["bodyweight"])
                )
                logger.info("Loaded user profile")
            except Exception as e:
                logger.error(f"Error loading profile: {e}")

    def _save_sessions(self):
        """Persist sessions to disk"""
        try:
            with open(self.data_dir / "sessions.json", "w") as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")

    def _save_profile(self):
        """Persist profile to disk"""
        try:
            data = {
                "goal": self.profile.goal.value,
                "difficulty": self.profile.difficulty.value,
                "workouts_per_week": self.profile.workouts_per_week,
                "preferred_types": [t.value for t in self.profile.preferred_types],
                "excluded_exercises": self.profile.excluded_exercises,
                "available_equipment": self.profile.available_equipment
            }
            with open(self.data_dir / "profile.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving profile: {e}")

    def update_profile(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile"""
        if "goal" in updates:
            self.profile.goal = GoalType(updates["goal"])
        if "difficulty" in updates:
            self.profile.difficulty = Difficulty(updates["difficulty"])
        if "workouts_per_week" in updates:
            self.profile.workouts_per_week = max(1, min(7, int(updates["workouts_per_week"])))
        if "preferred_types" in updates:
            self.profile.preferred_types = [WorkoutType(t) for t in updates["preferred_types"]]
        if "excluded_exercises" in updates:
            self.profile.excluded_exercises = updates["excluded_exercises"]
        if "available_equipment" in updates:
            self.profile.available_equipment = updates["available_equipment"]

        self._save_profile()
        return self.get_profile()

    def get_profile(self) -> Dict[str, Any]:
        """Get current user profile"""
        return {
            "goal": self.profile.goal.value,
            "difficulty": self.profile.difficulty.value,
            "workouts_per_week": self.profile.workouts_per_week,
            "preferred_types": [t.value for t in self.profile.preferred_types],
            "excluded_exercises": self.profile.excluded_exercises,
            "available_equipment": self.profile.available_equipment
        }

    def save_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Save a workout session"""
        session["created_at"] = datetime.now().isoformat()
        self.sessions.append(session)
        self._save_sessions()
        logger.info(f"Saved workout session {session.get('id', 'unknown')}")
        return session

    def complete_session(self, session_id: str, rating: Optional[int] = None,
                         notes: str = "", duration_minutes: Optional[int] = None,
                         exercise_updates: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Mark a session as completed with optional feedback"""
        for session in self.sessions:
            if session["id"] == session_id:
                session["completed"] = True
                session["completed_at"] = datetime.now().isoformat()
                if rating is not None:
                    session["rating"] = max(1, min(5, rating))
                if notes:
                    session["notes"] = notes
                if duration_minutes is not None:
                    session["duration_minutes"] = duration_minutes
                if exercise_updates:
                    for update in exercise_updates:
                        eid = update.get("exercise_id")
                        for ex in session["exercises"]:
                            if ex["exercise_id"] == eid:
                                ex["completed"] = update.get("completed", True)
                                if "weight_kg" in update:
                                    ex["weight_kg"] = update["weight_kg"]
                                if "notes" in update:
                                    ex["notes"] = update["notes"]
                                break

                self._save_sessions()
                return session

        return None

    def get_sessions(self, limit: int = 20, completed_only: bool = False) -> List[Dict]:
        """Get recent sessions"""
        result = self.sessions
        if completed_only:
            result = [s for s in result if s.get("completed")]
        return sorted(result, key=lambda s: s.get("date", ""), reverse=True)[:limit]

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a specific session"""
        for s in self.sessions:
            if s["id"] == session_id:
                return s
        return None

    def get_progress(self, days: int = 30) -> Dict[str, Any]:
        """Get progress summary for the last N days"""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        recent = [s for s in self.sessions
                  if s.get("completed") and s.get("date", "") >= cutoff]

        if not recent:
            return {
                "period_days": days,
                "total_workouts": 0,
                "total_duration_minutes": 0,
                "total_calories": 0,
                "workouts_by_type": {},
                "muscle_groups_frequency": {},
                "avg_rating": None,
                "current_streak": self._calculate_streak(),
                "best_streak": 0,
                "workouts_per_week_avg": 0
            }

        total_workouts = len(recent)
        total_duration = sum(s.get("duration_minutes", 0) for s in recent)
        total_calories = sum(s.get("estimated_calories", s.get("calories_burned", 0)) for s in recent)

        # By type
        by_type = {}
        for s in recent:
            t = s.get("workout_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        # Muscle groups
        muscle_freq = {}
        for s in recent:
            for ex in s.get("exercises", []):
                for mg in ex.get("muscle_groups", []):
                    muscle_freq[mg] = muscle_freq.get(mg, 0) + 1

        # Rating
        ratings = [s["rating"] for s in recent if s.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

        weeks = max(1, days / 7)

        return {
            "period_days": days,
            "total_workouts": total_workouts,
            "total_duration_minutes": total_duration,
            "total_calories": round(total_calories),
            "workouts_by_type": by_type,
            "muscle_groups_frequency": muscle_freq,
            "avg_rating": avg_rating,
            "current_streak": self._calculate_streak(),
            "workouts_per_week_avg": round(total_workouts / weeks, 1)
        }

    def _calculate_streak(self) -> int:
        """Calculate current consecutive workout days streak"""
        if not self.sessions:
            return 0

        completed_dates = sorted(set(
            s["date"] for s in self.sessions if s.get("completed")
        ), reverse=True)

        if not completed_dates:
            return 0

        streak = 0
        expected = date.today()

        for d_str in completed_dates:
            d = date.fromisoformat(d_str)
            if d == expected:
                streak += 1
                expected -= timedelta(days=1)
            elif d == expected - timedelta(days=1):
                # Allow one gap (rest day)
                expected = d
                streak += 1
                expected -= timedelta(days=1)
            else:
                break

        return streak

    def get_weekly_summary(self, week_offset: int = 0) -> Dict[str, Any]:
        """Get summary for a specific week (0 = current, 1 = last week, etc.)"""
        today = date.today()
        # Week starts on Monday
        current_monday = today - timedelta(days=today.weekday())
        target_monday = current_monday - timedelta(weeks=week_offset)
        target_sunday = target_monday + timedelta(days=6)

        week_start = target_monday.isoformat()
        week_end = target_sunday.isoformat()

        sessions = [
            s for s in self.sessions
            if s.get("completed") and week_start <= s.get("date", "") <= week_end
        ]

        total_workouts = len(sessions)
        total_duration = sum(s.get("duration_minutes", 0) for s in sessions)
        total_calories = sum(s.get("estimated_calories", s.get("calories_burned", 0)) for s in sessions)

        by_type = {}
        for s in sessions:
            t = s.get("workout_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        muscle_groups = {}
        for s in sessions:
            for ex in s.get("exercises", []):
                for mg in ex.get("muscle_groups", []):
                    muscle_groups[mg] = muscle_groups.get(mg, 0) + 1

        ratings = [s["rating"] for s in sessions if s.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

        goal_target = self.profile.workouts_per_week
        goal_progress = f"{total_workouts}/{goal_target}"

        # Workout days
        workout_dates = sorted(set(s["date"] for s in sessions))
        day_names = []
        for d_str in workout_dates:
            d = date.fromisoformat(d_str)
            day_names.append(d.strftime("%A"))

        return {
            "week_start": week_start,
            "week_end": week_end,
            "total_workouts": total_workouts,
            "total_duration_minutes": total_duration,
            "total_calories": round(total_calories),
            "workouts_by_type": by_type,
            "muscle_groups_hit": muscle_groups,
            "avg_rating": avg_rating,
            "streak_days": self._calculate_streak(),
            "goal_progress": goal_progress,
            "goal_met": total_workouts >= goal_target,
            "workout_days": day_names,
            "exercises_completed": sum(
                sum(1 for ex in s.get("exercises", []) if ex.get("completed"))
                for s in sessions
            )
        }

    def get_exercise_history(self, exercise_id: str, limit: int = 10) -> List[Dict]:
        """Get history for a specific exercise across sessions"""
        history = []
        for s in sorted(self.sessions, key=lambda x: x.get("date", ""), reverse=True):
            if not s.get("completed"):
                continue
            for ex in s.get("exercises", []):
                if ex.get("exercise_id") == exercise_id:
                    history.append({
                        "date": s["date"],
                        "session_id": s["id"],
                        "sets": ex.get("sets"),
                        "reps": ex.get("reps"),
                        "weight_kg": ex.get("weight_kg"),
                        "completed": ex.get("completed", False)
                    })
                    break
            if len(history) >= limit:
                break
        return history


# ============ Service Singleton ============

class WorkoutService:
    """Main workout service combining generation and tracking"""

    def __init__(self):
        self.generator = WorkoutGenerator()
        self.tracker = ProgressTracker()
        logger.info("WorkoutService initialized")

    def generate_workout(
        self,
        workout_type: Optional[str] = None,
        target_muscles: Optional[List[str]] = None,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Generate and save a new workout"""
        w_type = WorkoutType(workout_type) if workout_type else None
        muscles = [MuscleGroup(m) for m in target_muscles] if target_muscles else None

        history = self.tracker.get_sessions(limit=5, completed_only=True)
        workout = self.generator.generate_workout(
            profile=self.tracker.profile,
            workout_type=w_type,
            target_muscles=muscles,
            duration_minutes=duration_minutes,
            history=history
        )
        self.tracker.save_session(workout)
        return workout

    def get_exercises(self, workout_type: Optional[str] = None,
                      muscle_group: Optional[str] = None) -> List[Dict]:
        """Get exercise library"""
        result = EXERCISES
        if workout_type:
            result = [e for e in result if e.workout_type.value == workout_type]
        if muscle_group:
            result = [e for e in result
                      if any(mg.value == muscle_group for mg in e.muscle_groups)]

        return [
            {
                "id": e.id,
                "name": e.name,
                "name_he": e.name_he,
                "muscle_groups": [mg.value for mg in e.muscle_groups],
                "workout_type": e.workout_type.value,
                "difficulty": e.difficulty.value,
                "default_sets": e.default_sets,
                "default_reps": e.default_reps,
                "is_timed": e.is_timed,
                "equipment": e.equipment,
                "calories_per_set": e.calories_per_set
            }
            for e in result
        ]


# Module-level instance
workout_service = WorkoutService()
