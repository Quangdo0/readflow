from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        title: str,
        content: str,
        user_id: int,
    ) -> Document:
        document = Document(
            title=title,
            content=content,
            user_id=user_id,
        )

        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def get_by_id(
        self,
        document_id: int,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )

        result = await self.db.execute(statement)

        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self,
        document_id: int,
        user_id: int,
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
            Document.deleted_at.is_(None),
        )

        result = await self.db.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_owner_id(
        self,
        owner_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Document]:
        statement = (
            select(Document)
            .where(
                Document.user_id == owner_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.id.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(statement)

        return list(result.scalars().all())

    async def save(
        self,
        document: Document,
    ) -> Document:
        await self.db.commit()
        await self.db.refresh(document)

        return document

    async def update_if_version_matches(
        self,
        document_id: int,
        expected_version: int,
        title: str | None = None,
        content: str | None = None,
    ) -> Document | None:
        values = {
            "version": Document.version + 1,
        }

        if title is not None:
            values["title"] = title

        if content is not None:
            values["content"] = content

        statement = (
            update(Document)
            .where(
                Document.id == document_id,
                Document.version == expected_version,
                Document.deleted_at.is_(None),
            )
            .values(**values)
            .returning(Document)
        )

        result = await self.db.execute(
            statement,
            execution_options={
                "populate_existing": True
            },
        )
        document = result.scalar_one_or_none()

        if document is None:
            await self.db.rollback()
            return None

        await self.db.commit()

        return document

    async def soft_delete(
        self,
        document: Document,
    ) -> None:
        document.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
