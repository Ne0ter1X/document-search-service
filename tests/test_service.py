from datetime import datetime

import pytest

from app.services.documents import DocumentService
from tests.conftest import FakeDocumentsRepo, FakeSearchRepo


@pytest.mark.asyncio
async def test_search_returns_documents_sorted(service: DocumentService) -> None:
    response = await service.search("жигули")
    assert response.total == 2
    assert response.returned == 2
    # сортировка — репозиторий обязан её соблюсти, проверяем что получили как есть
    assert response.items[0].id == 1


@pytest.mark.asyncio
async def test_search_empty_query_returns_nothing() -> None:
    service = DocumentService(
        documents=FakeDocumentsRepo(docs=[]),
        search=FakeSearchRepo(ids=[]),
    )
    response = await service.search("ничего")
    assert response.total == 0
    assert response.returned == 0
    assert response.items == []


@pytest.mark.asyncio
async def test_search_no_ids_in_es_short_circuits(sample_documents) -> None:
    """Если ES ничего не нашёл, PG не должна даже дёргаться."""
    service = DocumentService(
        documents=FakeDocumentsRepo(docs=sample_documents),
        search=FakeSearchRepo(ids=[]),
    )
    response = await service.search("xxx")
    assert response.returned == 0


@pytest.mark.asyncio
async def test_delete_missing_document_returns_false(sample_documents) -> None:
    service = DocumentService(
        documents=FakeDocumentsRepo(delete_ok=False),
        search=FakeSearchRepo(),
    )
    assert await service.delete(999) is False


@pytest.mark.asyncio
async def test_delete_existing_document_returns_true(sample_documents) -> None:
    service = DocumentService(
        documents=FakeDocumentsRepo(delete_ok=True),
        search=FakeSearchRepo(es_ok=True),
    )
    assert await service.delete(1) is True


@pytest.mark.asyncio
async def test_delete_succeeds_even_if_es_fails(sample_documents) -> None:
    """Главный архитектурный кейс: PG — источник истины, ES — второстепенный."""
    service = DocumentService(
        documents=FakeDocumentsRepo(delete_ok=True),
        search=FakeSearchRepo(es_ok=False),
    )
    assert await service.delete(1) is True