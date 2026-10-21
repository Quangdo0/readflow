from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_user_service
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.schemas.user import UserCreate


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_register_user():
    service = AsyncMock()
    created_at = datetime.now(timezone.utc)
    service.register.return_value = User(
        id=1,
        email="reader@example.com",
        hashed_password="stored-hash",
        created_at=created_at,
    )
    app.dependency_overrides[
        get_user_service
    ] = lambda: service

    response = client.post(
        "/auth/register",
        json={
            "email": "reader@example.com",
            "password": "secret-password",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "email": "reader@example.com",
        "created_at": created_at.isoformat().replace(
            "+00:00",
            "Z",
        ),
    }
    service.register.assert_awaited_once_with(
        UserCreate(
            email="reader@example.com",
            password="secret-password",
        )
    )


def test_login_user():
    service = AsyncMock()
    service.login.return_value = "encoded-access-token"
    app.dependency_overrides[
        get_user_service
    ] = lambda: service

    response = client.post(
        "/auth/login",
        data={
            "username": "reader@example.com",
            "password": "secret-password",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "encoded-access-token",
        "token_type": "bearer",
    }
    service.login.assert_awaited_once_with(
        UserCreate(
            email="reader@example.com",
            password="secret-password",
        )
    )


def test_get_current_user_with_valid_token():
    created_at = datetime.now(timezone.utc)
    user = User(
        id=9,
        email="reader@example.com",
        hashed_password="stored-hash",
        created_at=created_at,
    )
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = user
    db.execute.return_value = result

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(user_id=user.id)

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 9,
        "email": "reader@example.com",
        "created_at": created_at.isoformat().replace(
            "+00:00",
            "Z",
        ),
    }
    db.execute.assert_awaited_once()


def test_get_current_user_without_token():
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Not authenticated"
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_get_current_user_with_invalid_token():
    db = AsyncMock()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer not-a-valid-jwt"
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Could not validate credentials"
    }
    assert response.headers["www-authenticate"] == "Bearer"
    db.execute.assert_not_awaited()
