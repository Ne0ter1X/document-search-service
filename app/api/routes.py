from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.es import get_es
from app.repositories.documents import DocumentRepository
from app.repositories.search import SearchRepository
from app.schemas import SearchResponse
from app.services.documents import DocumentService

router = APIRouter()


async def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    es: Annotated[AsyncElasticsearch, Depends(get_es)],
) -> DocumentService:
    return DocumentService(
        documents=DocumentRepository(session),
        search=SearchRepository(es),
    )


ServiceDep = Annotated[DocumentService, Depends(get_service)]


@router.get("/search", response_model=SearchResponse)
async def search(
    service: ServiceDep,
    q: Annotated[str, Query(min_length=1, max_length=500, description="Поисковый запрос")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SearchResponse:
    return await service.search(q, limit=limit)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(doc_id: int, service: ServiceDep) -> None:
    deleted = await service.delete(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")