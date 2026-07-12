from app.core.security import hash_password, verify_password

TEST_PASSWORD = "correct-horse-battery-staple"


def test_hash_password_uses_argon2id() -> None:
    hashed_password = hash_password(TEST_PASSWORD)

    assert hashed_password != TEST_PASSWORD
    assert hashed_password.startswith("$argon2id$")
    assert verify_password(TEST_PASSWORD, hashed_password)


def test_hash_password_uses_random_salt() -> None:
    first_hash = hash_password(TEST_PASSWORD)
    second_hash = hash_password(TEST_PASSWORD)

    assert first_hash != second_hash
    assert verify_password(TEST_PASSWORD, first_hash)
    assert verify_password(TEST_PASSWORD, second_hash)


def test_verify_password_rejects_incorrect_password() -> None:
    hashed_password = hash_password(TEST_PASSWORD)

    assert not verify_password("incorrect-password", hashed_password)
