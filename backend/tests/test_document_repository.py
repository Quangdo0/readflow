from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.document import Document
from app.repositories.document import DocumentRepository


def compile_query(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={
                "literal_binds": True
            },
        )
    )


def database_result():
    result = Mock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    return result


@pytest.mark.asyncio
async def test_get_by_id_excludes_deleted_rows():
    db = AsyncMock()
    db.execute.return_value = database_result()
    repository = DocumentRepository(db)

    await repository.get_by_id(document_id=1)

    statement = db.execute.await_args.args[0]
    query = compile_query(statement)

    assert "documents.id = 1" in query
    assert "documents.deleted_at IS NULL" in query


@pytest.mark.asyncio
async def test_get_by_id_for_user_filters_owner_and_active_rows():
    db = AsyncMock()
    db.execute.return_value = database_result()
    repository = DocumentRepository(db)

    await repository.get_by_id_for_user(
        document_id=1,
        user_id=2,
    )

    statement = db.execute.await_args.args[0]
    query = compile_query(statement)

    assert "documents.id = 1" in query
    assert "documents.user_id = 2" in query
    assert "documents.deleted_at IS NULL" in query


@pytest.mark.asyncio
async def test_list_by_owner_id_excludes_deleted_rows():
    db = AsyncMock()
    db.execute.return_value = database_result()
    repository = DocumentRepository(db)

    documents = await repository.list_by_owner_id(
        owner_id=2,
        limit=20,
        offset=0,
    )

    statement = db.execute.await_args.args[0]
    query = compile_query(statement)

    assert documents == []
    assert "documents.user_id = 2" in query
    assert "documents.deleted_at IS NULL" in query


@pytest.mark.asyncio
async def test_soft_delete_sets_aware_utc_timestamp_and_persists():
    db = AsyncMock()
    repository = DocumentRepository(db)
    document = Document(
        id=1,
        user_id=1,
        title="Reading Notes",
        content="Private notes",
        status="uploaded",
        deleted_at=None,
    )
    before = datetime.now(timezone.utc)

    await repository.soft_delete(document)

    after = datetime.now(timezone.utc)
    assert document.deleted_at is not None
    assert document.deleted_at.utcoffset() == timedelta(0)
    assert before <= document.deleted_at <= after
    db.commit.assert_awaited_once_with()
    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_if_version_matches_is_atomic():
    db = AsyncMock()
    updated_document = Document(
        id=1,
        user_id=1,
        title="Updated Notes",
        content="Private notes",
        status="uploaded",
        version=2,
        deleted_at=None,
    )
    result = Mock()
    result.scalar_one_or_none.return_value = updated_document
    db.execute.return_value = result
    repository = DocumentRepository(db)

    document = await repository.update_if_version_matches(
        document_id=1,
        expected_version=1,
        title="Updated Notes",
        content=None,
    )

    statement = db.execute.await_args.args[0]
    query = compile_query(statement)
    assert document is updated_document
    assert document.version == 2
    assert "UPDATE documents" in query
    assert "documents.id = 1" in query
    assert "documents.version = 1" in query
    assert "documents.deleted_at IS NULL" in query
    assert "version=(documents.version + 1)" in query
    assert "RETURNING" in query
    db.commit.assert_awaited_once_with()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_if_version_matches_returns_none_on_conflict():
    db = AsyncMock()
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    repository = DocumentRepository(db)

    document = await repository.update_if_version_matches(
        document_id=1,
        expected_version=1,
        title="Stale Notes",
    )

    assert document is None
    db.rollback.assert_awaited_once_with()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_two_updates_with_same_version_do_not_overwrite():
    db = AsyncMock()
    first_document = Document(
        id=1,
        user_id=1,
        title="First Update",
        content="Private notes",
        status="uploaded",
        version=2,
        deleted_at=None,
    )
    first_result = Mock()
    first_result.scalar_one_or_none.return_value = first_document
    second_result = Mock()
    second_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [first_result, second_result]
    repository = DocumentRepository(db)

    first = await repository.update_if_version_matches(
        document_id=1,
        expected_version=1,
        title="First Update",
    )
    second = await repository.update_if_version_matches(
        document_id=1,
        expected_version=1,
        title="Second Update",
    )

    assert first is first_document
    assert first.title == "First Update"
    assert first.version == 2
    assert second is None
    assert db.commit.await_count == 1
    assert db.rollback.await_count == 1
