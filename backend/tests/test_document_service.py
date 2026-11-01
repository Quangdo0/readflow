from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.document import (
    DocumentConflictError,
    DocumentForbiddenError,
    DocumentNotFoundError,
    DocumentService,
)


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


def make_document(
    owner_id: int = 1,
    deleted_at: datetime | None = None,
) -> Document:
    return Document(
        id=1,
        user_id=owner_id,
        title="Reading Notes",
        content="Private notes",
        status="uploaded",
        version=1,
        deleted_at=deleted_at,
    )


@pytest.mark.asyncio
async def test_create_document():
    repository = AsyncMock()
    actor = make_user(7)
    document = make_document(owner_id=actor.id)
    repository.create.return_value = document
    service = DocumentService(repository)
    data = DocumentCreate(
        title="Reading Notes",
        content="Private notes",
    )

    result = await service.create_document(data, actor)

    assert result is document
    repository.create.assert_awaited_once_with(
        title="Reading Notes",
        content="Private notes",
        user_id=actor.id,
    )


@pytest.mark.asyncio
async def test_owner_read_succeeds():
    repository = AsyncMock()
    actor = make_user(1)
    document = make_document(owner_id=actor.id)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    result = await service.get_document(document.id, actor)

    assert result is document
    repository.get_by_id.assert_awaited_once_with(document.id)


@pytest.mark.asyncio
async def test_admin_reading_another_users_document_succeeds():
    repository = AsyncMock()
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    result = await service.get_document(document.id, admin)

    assert result is document


@pytest.mark.asyncio
async def test_normal_non_owner_read_raises_not_found():
    repository = AsyncMock()
    user = make_user(2)
    document = make_document(owner_id=1)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    with pytest.raises(DocumentNotFoundError):
        await service.get_document(document.id, user)


@pytest.mark.asyncio
async def test_owner_update_succeeds():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(owner_id=owner.id)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)
    data = DocumentUpdate(
        version=1,
        title="Updated Notes",
    )

    updated_document = make_document(owner_id=owner.id)
    updated_document.title = "Updated Notes"
    updated_document.version = 2
    repository.update_if_version_matches.return_value = (
        updated_document
    )

    result = await service.update_document(
        document.id,
        data,
        owner,
    )

    assert result is updated_document
    assert result.version == 2
    repository.update_if_version_matches.assert_awaited_once_with(
        document_id=document.id,
        expected_version=1,
        title="Updated Notes",
        content=None,
    )


@pytest.mark.asyncio
async def test_repeated_updates_increment_versions_monotonically():
    repository = AsyncMock()
    owner = make_user(1)
    version_one = make_document(owner_id=owner.id)
    version_two = make_document(owner_id=owner.id)
    version_two.title = "Second Version"
    version_two.version = 2
    version_three = make_document(owner_id=owner.id)
    version_three.title = "Third Version"
    version_three.version = 3
    repository.get_by_id.side_effect = [
        version_one,
        version_two,
    ]
    repository.update_if_version_matches.side_effect = [
        version_two,
        version_three,
    ]
    service = DocumentService(repository)

    first = await service.update_document(
        version_one.id,
        DocumentUpdate(
            version=1,
            title="Second Version",
        ),
        owner,
    )
    second = await service.update_document(
        version_two.id,
        DocumentUpdate(
            version=2,
            title="Third Version",
        ),
        owner,
    )

    assert first.version == 2
    assert second.version == 3
    assert repository.update_if_version_matches.await_count == 2


@pytest.mark.asyncio
async def test_stale_version_raises_conflict_before_update():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(owner_id=owner.id)
    document.version = 2
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    with pytest.raises(DocumentConflictError):
        await service.update_document(
            document.id,
            DocumentUpdate(
                version=1,
                title="Stale Update",
            ),
            owner,
        )

    repository.update_if_version_matches.assert_not_awaited()


@pytest.mark.asyncio
async def test_atomic_update_miss_raises_conflict():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(owner_id=owner.id)
    repository.get_by_id.return_value = document
    repository.update_if_version_matches.return_value = None
    service = DocumentService(repository)

    with pytest.raises(DocumentConflictError):
        await service.update_document(
            document.id,
            DocumentUpdate(
                version=1,
                title="Racing Update",
            ),
            owner,
        )

    repository.update_if_version_matches.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_update_of_another_users_document_is_forbidden():
    repository = AsyncMock()
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    with pytest.raises(DocumentForbiddenError):
        await service.update_document(
            document.id,
            DocumentUpdate(
                version=99,
                title="Changed",
            ),
            admin,
        )

    repository.update_if_version_matches.assert_not_awaited()


@pytest.mark.asyncio
async def test_normal_non_owner_update_raises_not_found():
    repository = AsyncMock()
    user = make_user(2)
    document = make_document(owner_id=1)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    with pytest.raises(DocumentNotFoundError):
        await service.update_document(
            document.id,
            DocumentUpdate(
                version=99,
                title="Changed",
            ),
            user,
        )

    repository.update_if_version_matches.assert_not_awaited()


@pytest.mark.asyncio
async def test_owner_delete_soft_deletes_document():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(owner_id=owner.id)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    await service.delete_document(document.id, owner)

    repository.soft_delete.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_admin_delete_of_another_users_document_soft_deletes():
    repository = AsyncMock()
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    await service.delete_document(document.id, admin)

    repository.soft_delete.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_second_delete_raises_not_found():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(owner_id=owner.id)
    repository.get_by_id.side_effect = [document, None]
    service = DocumentService(repository)

    await service.delete_document(document.id, owner)

    with pytest.raises(DocumentNotFoundError):
        await service.delete_document(document.id, owner)

    repository.soft_delete.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_deleted_document_cannot_be_read():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(
        owner_id=owner.id,
        deleted_at=datetime.now(timezone.utc),
    )
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    with pytest.raises(DocumentNotFoundError):
        await service.get_document(document.id, owner)


@pytest.mark.asyncio
async def test_deleted_document_cannot_be_updated():
    repository = AsyncMock()
    owner = make_user(1)
    document = make_document(
        owner_id=owner.id,
        deleted_at=datetime.now(timezone.utc),
    )
    repository.get_by_id.return_value = document
    service = DocumentService(repository)

    with pytest.raises(DocumentNotFoundError):
        await service.update_document(
            document.id,
            DocumentUpdate(
                version=1,
                title="Changed",
            ),
            owner,
        )

    repository.update_if_version_matches.assert_not_awaited()


@pytest.mark.asyncio
async def test_deleted_document_is_absent_from_list():
    repository = AsyncMock()
    actor = make_user(1)
    repository.list_by_owner_id.return_value = []
    service = DocumentService(repository)

    result = await service.list_documents(
        actor=actor,
        limit=20,
        offset=0,
    )

    assert result == []
    repository.list_by_owner_id.assert_awaited_once_with(
        owner_id=actor.id,
        limit=20,
        offset=0,
    )
