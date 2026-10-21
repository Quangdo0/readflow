import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password():
    plain_password = "correct-horse-battery-staple"

    hashed_password = hash_password(plain_password)

    assert hashed_password != plain_password
    assert plain_password not in hashed_password


def test_verify_password():
    plain_password = "correct-horse-battery-staple"
    hashed_password = hash_password(plain_password)

    assert verify_password(
        plain_password,
        hashed_password,
    ) is True
    assert verify_password(
        "incorrect-password",
        hashed_password,
    ) is False


def test_create_and_decode_access_token():
    token = create_access_token(user_id=42)

    assert isinstance(token, str)
    assert decode_access_token(token) == 42


def test_decode_invalid_access_token():
    with pytest.raises(
        InvalidTokenError,
        match="Invalid Token",
    ):
        decode_access_token("not-a-valid-jwt")
