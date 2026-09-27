from elasticsearch import AsyncElasticsearch

from app.config import settings

_es: AsyncElasticsearch | None = None


def get_es() -> AsyncElasticsearch | None:
    global _es
    if _es is None:
        _es = AsyncElasticsearch(settings.es_url)
    assert _es is not None
    return _es


async def close_es() -> None:
    global _es
    if _es is not None:
        await _es.close()
        _es = None
