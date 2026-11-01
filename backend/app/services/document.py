from app.core.permissions import (
    can_delete_document,
    can_read_document,
    can_update_document,
)
from app.models.document import Document
from app.models.user import User, UserRole
from app.repositories.document import DocumentRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
)


class DocumentNotFoundError(Exception):
    pass


class DocumentForbiddenError(Exception):
    pass


class DocumentConflictError(Exception):
    pass


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
    ):
        self.repository = repository

    async def create_document(
        self,
        data: DocumentCreate,
        actor: User,
    ) -> Document:
        return await self.repository.create(
            title=data.title,
            content=data.content,
            user_id=actor.id,
        )

    async def get_document(
        self,
        document_id: int,
        actor: User,
    ) -> Document:
        document = await self.repository.get_by_id(
            document_id
        )

        if (
            document is None
            or not can_read_document(actor, document)
        ):
            raise DocumentNotFoundError(
                f"Document {document_id} not found"
            )

        return document

    async def list_documents(
        self,
        actor: User,
        limit: int,
        offset: int,
    ) -> list[Document]:
        return await self.repository.list_by_owner_id(
            owner_id=actor.id,
            limit=limit,
            offset=offset,
        )

    async def update_document(
        self,
        document_id: int,
        data: DocumentUpdate,
        actor: User,
    ) -> Document:
        document = await self.repository.get_by_id(
            document_id
        )

        if document is None:
            raise DocumentNotFoundError(
                f"Document {document_id} not found"
            )

        if not can_update_document(actor, document):
            if document.deleted_at is not None:
                raise DocumentNotFoundError(
                    f"Document {document_id} not found"
                )

            if (
                actor.role == UserRole.ADMIN
                and document.user_id != actor.id
            ):
                raise DocumentForbiddenError(
                    f"Document {document_id} cannot be updated"
                )

            raise DocumentNotFoundError(
                f"Document {document_id} not found"
            )

        if data.version != document.version:
            raise DocumentConflictError(
                f"Document {document_id} version conflict"
            )

        updated_document = (
            await self.repository.update_if_version_matches(
                document_id=document_id,
                expected_version=data.version,
                title=data.title,
                content=data.content,
            )
        )

        if updated_document is None:
            raise DocumentConflictError(
                f"Document {document_id} version conflict"
            )

        return updated_document

    async def delete_document(
        self,
        document_id: int,
        actor: User,
    ) -> None:
        document = await self.repository.get_by_id(
            document_id
        )

        if (
            document is None
            or not can_delete_document(actor, document)
        ):
            raise DocumentNotFoundError(
                f"Document {document_id} not found"
            )

        await self.repository.soft_delete(document)
