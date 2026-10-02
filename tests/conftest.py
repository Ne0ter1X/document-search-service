from collections.abc import AsyncIterator
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes import get_service
from app.main import app
from app.models import Document
from app.schemas import DocumentOut, SearchResponse
from app.services.documents import DocumentService


class FakeDocumentsRepo:
    def __init__(self, docs: list[Document] | None = None, delete_ok: bool = True):
        self.docs = docs or []
        self.delete_ok = delete_ok

    async def get_by_ids_ordered(self, ids: list[int], limit: int) -> list[Document]:
        return [d for d in self.docs if d.id in ids][:limit]

    async def delete_by_id(self, doc_id: int) -> bool:
        return self.delete_ok


class FakeSearchRepo:
    def __init__(self, ids: list[int] | None = None, es_ok: bool = True):
        self.ids = ids or []
        self.es_ok = es_ok

    async def find_ids(self, query: str) -> list[int]:
        return self.ids

    async def delete_by_id(self, doc_id: int) -> bool:
        return self.es_ok


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(
            id=1,
            text="Жигули в масштабе",
            rubrics=["VK-1", "VK-2"],
            created_date=datetime(2019, 7, 25, 12, 42, 13),
        ),
        Document(
            id=2,
            text="ВАЗ-2107 в бумаге",
            rubrics=["VK-1"],
            created_date=datetime(2019, 6, 10, 8, 0, 0),
        ),
    ]


@pytest.fixture
def service(sample_documents: list[Document]) -> DocumentService:
    return DocumentService(
        documents=FakeDocumentsRepo(docs=sample_documents),
        search=FakeSearchRepo(ids=[1, 2]),
    )


@pytest.fixture
async def api_client(service: DocumentService) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_service] = lambda: service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()