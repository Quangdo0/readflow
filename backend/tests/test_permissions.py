from app.core.permissions import (
    can_delete_document,
    can_read_document,
    can_update_document,
)
from app.models.document import Document
from app.models.user import User, UserRole


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
    return Document(
        id=1,
        user_id=owner_id,
        title="Reading Notes",
        content="Private notes",
        status="uploaded",
        deleted_at=None,
    )


def test_owner_can_read_update_and_delete_document():
    owner = make_user(1)
    document = make_document(owner_id=owner.id)

    assert can_read_document(owner, document) is True
    assert can_update_document(owner, document) is True
    assert can_delete_document(owner, document) is True


def test_admin_can_read_and_delete_another_users_document():
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)

    assert can_read_document(admin, document) is True
    assert can_delete_document(admin, document) is True


def test_admin_cannot_update_another_users_document():
    admin = make_user(2, UserRole.ADMIN)
    document = make_document(owner_id=1)

    assert can_update_document(admin, document) is False


def test_normal_non_owner_cannot_read_update_or_delete_document():
    user = make_user(2)
    document = make_document(owner_id=1)

    assert can_read_document(user, document) is False
    assert can_update_document(user, document) is False
    assert can_delete_document(user, document) is False
