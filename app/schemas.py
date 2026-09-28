from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    rubrics: list[str]
    created_date: datetime


class SearchResponse(BaseModel):
    query: str
    total: int = Field(description="Сколько всего id нашёл ES")
    returned: int = Field(description="Сколько вернули после сортировки и лимита")
    items: list[DocumentOut]