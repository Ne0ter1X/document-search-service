from elasticsearch import AsyncElasticsearch

from app.config import settings


class SearchRepository:
    MAX_IDS = 10000

    def __init__(self, es: AsyncElasticsearch) -> None:
        self._es = es

    async def find_ids(self, query: str) -> list[int]:
        resp = await self._es.search(
            index=settings.es_index,
            query={"match": {"text": query}},
            size=self.MAX_IDS,
            source=False,
        )
        return [int(hit["_id"]) for hit in resp["hits"]["hits"]]

    async def delete_by_id(self, doc_id: int) -> bool:
        try:
            await self._es.delete(
                index=settings.es_index,
                id=str(doc_id),
                refresh=True,
            )
            return True
        except Exception:
            return False