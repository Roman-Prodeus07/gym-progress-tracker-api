from typing import TypedDict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise


class ExerciseSeed(TypedDict):
    name: str
    slug: str
    description: str
    primary_muscle_group: str
    equipment: str


EXERCISE_SEEDS: tuple[ExerciseSeed, ...] = (
    {
        "name": "Barbell Back Squat",
        "slug": "barbell-back-squat",
        "description": "Compound squat for the quadriceps and glutes.",
        "primary_muscle_group": "quadriceps",
        "equipment": "barbell",
    },
    {
        "name": "Barbell Bench Press",
        "slug": "barbell-bench-press",
        "description": "Compound horizontal press for the chest and triceps.",
        "primary_muscle_group": "chest",
        "equipment": "barbell",
    },
    {
        "name": "Conventional Deadlift",
        "slug": "conventional-deadlift",
        "description": "Compound hip hinge for the posterior chain.",
        "primary_muscle_group": "back",
        "equipment": "barbell",
    },
    {
        "name": "Romanian Deadlift",
        "slug": "romanian-deadlift",
        "description": "Hip hinge focused on the hamstrings and glutes.",
        "primary_muscle_group": "hamstrings",
        "equipment": "barbell",
    },
    {
        "name": "Overhead Press",
        "slug": "overhead-press",
        "description": "Vertical press for the shoulders and triceps.",
        "primary_muscle_group": "shoulders",
        "equipment": "barbell",
    },
    {
        "name": "Barbell Row",
        "slug": "barbell-row",
        "description": "Horizontal pull for the upper back.",
        "primary_muscle_group": "back",
        "equipment": "barbell",
    },
    {
        "name": "Pull-Up",
        "slug": "pull-up",
        "description": "Bodyweight vertical pull for the back and biceps.",
        "primary_muscle_group": "back",
        "equipment": "bodyweight",
    },
    {
        "name": "Lat Pulldown",
        "slug": "lat-pulldown",
        "description": "Cable vertical pull focused on the latissimus dorsi.",
        "primary_muscle_group": "back",
        "equipment": "cable",
    },
    {
        "name": "Seated Cable Row",
        "slug": "seated-cable-row",
        "description": "Seated horizontal pull for the upper back.",
        "primary_muscle_group": "back",
        "equipment": "cable",
    },
    {
        "name": "Incline Dumbbell Bench Press",
        "slug": "incline-dumbbell-bench-press",
        "description": "Incline press focused on the upper chest.",
        "primary_muscle_group": "chest",
        "equipment": "dumbbell",
    },
    {
        "name": "Dumbbell Lateral Raise",
        "slug": "dumbbell-lateral-raise",
        "description": "Isolation exercise for the lateral deltoids.",
        "primary_muscle_group": "shoulders",
        "equipment": "dumbbell",
    },
    {
        "name": "Barbell Curl",
        "slug": "barbell-curl",
        "description": "Elbow flexion exercise for the biceps.",
        "primary_muscle_group": "biceps",
        "equipment": "barbell",
    },
    {
        "name": "Cable Triceps Pushdown",
        "slug": "cable-triceps-pushdown",
        "description": "Cable isolation exercise for the triceps.",
        "primary_muscle_group": "triceps",
        "equipment": "cable",
    },
    {
        "name": "Leg Press",
        "slug": "leg-press",
        "description": "Machine compound exercise for the lower body.",
        "primary_muscle_group": "quadriceps",
        "equipment": "machine",
    },
    {
        "name": "Leg Extension",
        "slug": "leg-extension",
        "description": "Machine isolation exercise for the quadriceps.",
        "primary_muscle_group": "quadriceps",
        "equipment": "machine",
    },
    {
        "name": "Seated Leg Curl",
        "slug": "seated-leg-curl",
        "description": "Machine isolation exercise for the hamstrings.",
        "primary_muscle_group": "hamstrings",
        "equipment": "machine",
    },
    {
        "name": "Hip Thrust",
        "slug": "hip-thrust",
        "description": "Hip extension exercise focused on the glutes.",
        "primary_muscle_group": "glutes",
        "equipment": "barbell",
    },
    {
        "name": "Standing Calf Raise",
        "slug": "standing-calf-raise",
        "description": "Standing plantar flexion exercise for the calves.",
        "primary_muscle_group": "calves",
        "equipment": "machine",
    },
    {
        "name": "Push-Up",
        "slug": "push-up",
        "description": "Bodyweight horizontal press for the chest.",
        "primary_muscle_group": "chest",
        "equipment": "bodyweight",
    },
    {
        "name": "Plank",
        "slug": "plank",
        "description": "Isometric trunk stability exercise.",
        "primary_muscle_group": "core",
        "equipment": "bodyweight",
    },
)


async def seed_exercise_catalogue(session: AsyncSession) -> int:
    statement = (
        insert(Exercise)
        .values(list(EXERCISE_SEEDS))
        .on_conflict_do_nothing(index_elements=[Exercise.slug])
        .returning(Exercise.id)
    )

    inserted_ids = await session.scalars(statement)
    inserted_count = len(inserted_ids.all())

    await session.commit()

    return inserted_count
