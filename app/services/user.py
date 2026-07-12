from asyncio import to_thread

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User
from app.schemas import UserCreate


class EmailAlreadyRegisteredError(Exception):
    """Raised when an account with the email already exists."""


def _is_email_unique_violation(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)

    return constraint_name == "uq_users_email"


async def register_user(
    session: AsyncSession,
    user_data: UserCreate,
) -> User:
    email = str(user_data.email)

    existing_user = await session.scalar(select(User).where(User.email == email))

    if existing_user is not None:
        raise EmailAlreadyRegisteredError

    plain_password = user_data.password.get_secret_value()
    hashed_password = await to_thread(hash_password, plain_password)

    user = User(
        email=email,
        hashed_password=hashed_password,
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()

        if _is_email_unique_violation(error):
            raise EmailAlreadyRegisteredError from error

        raise
    except SQLAlchemyError:
        await session.rollback()
        raise

    await session.refresh(user)
    return user
