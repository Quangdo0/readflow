from unittest.mock import AsyncMock

import pytest

from app.core.security import (
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user import (
    EmailAlreadyExistsError,
    InvalidCredentialError,
    UserService,
)


@pytest.mark.asyncio
async def test_register_user():
    repository = AsyncMock()
    repository.get_by_email.return_value = None

    created_user = User(
        id=1,
        email="reader@example.com",
        hashed_password="stored-hash",
    )
    repository.create.return_value = created_user

    service = UserService(repository)
    data = UserCreate(
        email="reader@example.com",
        password="secret-password",
    )

    result = await service.register(data)

    assert result is created_user
    repository.get_by_email.assert_awaited_once_with(
        email="reader@example.com"
    )
    repository.create.assert_awaited_once()

    create_kwargs = repository.create.await_args.kwargs
    assert create_kwargs["email"] == "reader@example.com"
    assert create_kwargs["hashed_password"] != data.password
    assert verify_password(
        data.password,
        create_kwargs["hashed_password"],
    ) is True


@pytest.mark.asyncio
async def test_register_duplicate_email():
    repository = AsyncMock()
    repository.get_by_email.return_value = User(
        id=1,
        email="reader@example.com",
        hashed_password="stored-hash",
    )

    service = UserService(repository)
    data = UserCreate(
        email="reader@example.com",
        password="secret-password",
    )

    with pytest.raises(
        EmailAlreadyExistsError,
        match="Email already exist",
    ):
        await service.register(data)

    repository.get_by_email.assert_awaited_once_with(
        email="reader@example.com"
    )
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_user():
    repository = AsyncMock()
    user = User(
        id=7,
        email="reader@example.com",
        hashed_password=hash_password(
            "secret-password"
        ),
    )
    repository.get_by_email.return_value = user

    service = UserService(repository)
    data = UserCreate(
        email="reader@example.com",
        password="secret-password",
    )

    token = await service.login(data)

    assert decode_access_token(token) == user.id
    repository.get_by_email.assert_awaited_once_with(
        email="reader@example.com"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("stored_user", "password"),
    [
        (None, "secret-password"),
        (
            User(
                id=7,
                email="reader@example.com",
                hashed_password=hash_password(
                    "secret-password"
                ),
            ),
            "incorrect-password",
        ),
    ],
)
async def test_login_with_invalid_credentials(
    stored_user,
    password,
):
    repository = AsyncMock()
    repository.get_by_email.return_value = stored_user

    service = UserService(repository)
    data = UserCreate(
        email="reader@example.com",
        password=password,
    )

    with pytest.raises(
        InvalidCredentialError,
        match="Invalid email or password",
    ):
        await service.login(data)

    repository.get_by_email.assert_awaited_once_with(
        email="reader@example.com"
    )
