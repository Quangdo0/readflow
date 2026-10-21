from datetime import datetime, timezone

from sqlalchemy import select
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

    async def soft_delete(
        self,
        document: Document,
    ) -> None:
        document.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()
