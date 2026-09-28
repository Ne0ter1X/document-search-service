from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_ids_ordered(
        self, ids: list[int], limit: int
    ) -> list[Document]:
        if not ids:
            return []
        stmt = (
            select(Document)
            .where(Document.id.in_(ids))
            .order_by(Document.created_date.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_id(self, doc_id: int) -> bool:
        stmt = delete(Document).where(Document.id == doc_id).returning(Document.id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.scalar_one_or_none() is not None
