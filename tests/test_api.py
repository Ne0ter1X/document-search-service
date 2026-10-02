import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_endpoint_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/search", params={"q": "жигули"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "жигули"
    assert body["returned"] == 2


@pytest.mark.asyncio
async def test_search_endpoint_rejects_empty_query(api_client: AsyncClient) -> None:
    response = await api_client.get("/search", params={"q": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_rejects_huge_limit(api_client: AsyncClient) -> None:
    response = await api_client.get("/search", params={"q": "test", "limit": 500})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_endpoint_default_limit_is_20(api_client: AsyncClient) -> None:
    response = await api_client.get("/search", params={"q": "жигули"})
    body = response.json()
    assert body["returned"] <= 20


@pytest.mark.asyncio
async def test_delete_existing_returns_204(api_client: AsyncClient) -> None:
    response = await api_client.delete("/documents/1")
    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_missing_returns_404(
    service, api_client: AsyncClient
) -> None:
    service._documents.delete_ok = False  # type: ignore[attr-defined]
    response = await api_client.delete("/documents/999")
    assert response.status_code == 404