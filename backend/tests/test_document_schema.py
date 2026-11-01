from datetime import datetime, timezone

from app.models.document import Document
from app.schemas.document import DocumentRead, DocumentUpdate


def test_document_model_defaults_version_to_one():
    version_column = Document.__table__.c.version

    assert version_column.nullable is False
    assert version_column.default.arg == 1
    assert str(version_column.server_default.arg) == "1"


def test_document_update_uses_version_as_expected_version():
    data = DocumentUpdate(
        version=4,
        title="Updated Notes",
    )

    assert data.version == 4


def test_document_response_includes_version():
    now = datetime.now(timezone.utc)
    document = Document(
        id=1,
        user_id=1,
        title="Reading Notes",
        content="Private notes",
        status="uploaded",
        version=3,
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )

    response = DocumentRead.model_validate(document)

    assert response.version == 3
