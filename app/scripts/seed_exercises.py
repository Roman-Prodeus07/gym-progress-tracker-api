import asyncio

from app.db.session import async_session_factory, engine
from app.services.exercise_seed import (
    EXERCISE_SEEDS,
    seed_exercise_catalogue,
)


async def main() -> None:
    try:
        async with async_session_factory() as session:
            inserted_count = await seed_exercise_catalogue(session)
    finally:
        await engine.dispose()

    existing_count = len(EXERCISE_SEEDS) - inserted_count

    print(
        "Exercise catalogue seed complete: "
        f"{inserted_count} inserted, "
        f"{existing_count} already present."
    )


if __name__ == "__main__":
    asyncio.run(main())
