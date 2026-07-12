from asyncio import to_thread

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models import User

DUMMY_PASSWORD_HASH = hash_password(
    "dummy-password-used-only-for-timing-protection",
)


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    normalized_email = email.strip().lower()

    user = await session.scalar(
        select(User).where(User.email == normalized_email),
    )

    stored_password_hash = (
        user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
    )

    password_is_valid = await to_thread(
        verify_password,
        password,
        stored_password_hash,
    )

    if user is None or not password_is_valid:
        return None

    return user
