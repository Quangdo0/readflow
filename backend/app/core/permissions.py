from app.models.document import Document
from app.models.user import User, UserRole


def can_read_document(
    user: User,
    document: Document,
) -> bool:
    if document.deleted_at is not None:
        return False

    if user.role == UserRole.ADMIN:
        return True

    return document.user_id == user.id


def can_update_document(
    user: User,
    document: Document,
) -> bool:
    if document.deleted_at is not None:
        return False

    return document.user_id == user.id


def can_delete_document(
    user: User,
    document: Document,
) -> bool:
    if document.deleted_at is not None:
        return False

    if user.role == UserRole.ADMIN:
        return True

    return document.user_id == user.id