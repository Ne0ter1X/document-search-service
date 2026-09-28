import logging

from app.repositories.documents import DocumentRepository
from app.repositories.search import SearchRepository
from app.schemas import DocumentOut, SearchResponse

logger = logging.getLogger(__name__)

MAX_RESULTS = 20


class DocumentService:
    def __init__(
        self,
        documents: DocumentRepository,
        search: SearchRepository,
    ) -> None:
        self._documents = documents
        self._search = search

    async def search(self, query: str, limit: int = MAX_RESULTS) -> SearchResponse:
        ids = await self._search.find_ids(query)
        docs = await self._documents.get_by_ids_ordered(ids, limit=limit)

        return SearchResponse(
            query=query,
            total=len(ids),
            returned=len(docs),
            items=[DocumentOut.model_validate(d) for d in docs],
        )

    async def delete(self, doc_id: int) -> bool:
        deleted_in_pg = await self._documents.delete_by_id(doc_id)
        if not deleted_in_pg:
            return False

        deleted_in_es = await self._search.delete_by_id(doc_id)
        if not deleted_in_es:
            logger.warning(
                "Document %s deleted from PG but ES delete failed "
                "(likely already absent from index)",
                doc_id,
            )
        return True