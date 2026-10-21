from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_user,
    get_document_service,
)
from app.main import app
from app.models.document import Document
from app.models.user import User, UserRole
from app.services.document import DocumentService


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def make_user(
    user_id: int,
    role: UserRole = UserRole.USER,
) -> User:
    return User(
        id=user_id,
        email=f"user-{user_id}@example.com",
        hashed_password="stored-hash",
        role=role,
    )


def make_document(owner_id: int = 1) -> Document:
    now = datetime.now(timezone.utc)
    return Document(
        id=1,
        user_id=owner_id,
        title="User A Notes",
        content="Private reading notes",
        status="uploaded",
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )


def override_document_dependencies(
    current_user: User,
    repository: AsyncMock,
):
    service = DocumentService(repository)
    app.dependency_overrides[
        get_current_user
    ] = lambda: current_user
    app.dependency_overrides[
        get_document_service
    ] = lambda: service


@pytest.mark.parametrize(
    ("method", "path", "request_kwargs"),
    [
        ("GET", "/documents/1", {}),
        ("GET", "/documents", {}),
        (
            "POST",
            "/documents",
            {
                "json": {
                    "title": "Notes",
                    "content": "Private notes",
                }
            },
        ),
        (
            "PATCH",
            "/documents/1",
            {"json": {"title": "Changed"}},
        ),
        ("DELETE", "/documents/1", {}),
    ],
)
def test_unauthenticated_document_routes_return_401(
    method,
    path,
    request_kwargs,
):
    service = AsyncMock()
    app.dependency_overrides[
        get_document_service
    ] = lambda: service

    response = client.request(
        method,
        path,
        **request_kwargs,
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Not authenticated"
    }
    assert response.headers["www-authenticate"] == "Bearer"


def test_owner_can_read_own_document():
    owner = make_user(1)
    document = make_document(owner_id=owner.id)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(owner, repository)

    response = client.get("/documents/1")

    assert response.status_code == 200
    assert response.json()["id"] == document.id
    assert response.json()["title"] == document.title


def test_normal_non_owner_read_returns_404():
    user = make_user(2)
    document = make_document(owner_id=1)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(user, repository)

    response = client.get("/documents/1")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document 1 not found"
    }


def test_normal_non_owner_update_returns_404():
    user = make_user(2)
    document = make_document(owner_id=1)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(user, repository)

    response = client.patch(
        "/documents/1",
        json={"title": "Changed"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document 1 not found"
    }
    repository.save.assert_not_awaited()


def test_normal_non_owner_delete_returns_404():
    user = make_user(2)
    document = make_document(owner_id=1)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(user, repository)

    response = client.delete("/documents/1")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document 1 not found"
    }
    repository.soft_delete.assert_not_awaited()


def test_admin_can_read_another_users_document():
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(admin, repository)

    response = client.get("/documents/1")

    assert response.status_code == 200
    assert response.json()["id"] == document.id


def test_admin_update_of_another_users_document_returns_403():
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(admin, repository)

    response = client.patch(
        "/documents/1",
        json={"title": "Changed"},
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Document 1 cannot be updated"
    }
    repository.save.assert_not_awaited()


def test_admin_can_delete_another_users_document():
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)
    repository = AsyncMock()
    repository.get_by_id.return_value = document
    override_document_dependencies(admin, repository)

    response = client.delete("/documents/1")

    assert response.status_code == 204
    assert response.content == b""
    repository.soft_delete.assert_awaited_once_with(document)


def test_deleted_document_get_returns_404():
    owner = make_user(1)
    repository = AsyncMock()
    repository.get_by_id.return_value = None
    override_document_dependencies(owner, repository)

    response = client.get("/documents/1")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Document 1 not found"
    }


def test_document_list_is_scoped_to_actor_and_active_rows():
    admin = make_user(2, UserRole.ADMIN)
    repository = AsyncMock()
    repository.list_by_owner_id.return_value = []
    override_document_dependencies(admin, repository)

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []
    repository.list_by_owner_id.assert_awaited_once_with(
        owner_id=admin.id,
        limit=20,
        offset=0,
    )
