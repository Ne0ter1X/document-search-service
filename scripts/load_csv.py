import asyncio
import ast
import csv
from datetime import datetime
from pathlib import Path

from elasticsearch.helpers import async_bulk
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal, engine
from app.es import close_es, get_es
from app.models import Base, Document


def parse_rubrics(raw: str | None) -> list[str]:
    """rubrics в CSV — Python-список в виде строки: "['a','b']"."""
    if not raw:
        return []
    try:
        parsed = ast.literal_eval(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except (ValueError, SyntaxError):
        pass
    return [raw.strip()]


def parse_date(raw: str) -> datetime:
    return datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S")


async def create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def recreate_index(es) -> None:
    index = settings.es_index
    if await es.indices.exists(index=index):
        await es.indices.delete(index=index)
    await es.indices.create(
        index=index,
        mappings={
            "properties": {
                "id": {"type": "long"},
                "text": {"type": "text", "analyzer": "russian"},
            }
        },
    )
    print(f"ES: index '{index}' recreated")


async def load_to_postgres() -> list[tuple[int, str]]:
    csv_path = Path(settings.csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path.resolve()}")

    skipped = 0
    async with SessionLocal() as session:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = (row.get("text") or "").strip()
                date_raw = (row.get("created_date") or "").strip()
                if not text or not date_raw:
                    skipped += 1
                    continue
                session.add(
                    Document(
                        text=text,
                        created_date=parse_date(date_raw),
                        rubrics=parse_rubrics(row.get("rubrics")),
                    )
                )
        await session.commit()

        result = await session.execute(select(Document.id, Document.text))
        rows = list(result.all())

    print(f"Postgres: inserted {len(rows)} docs, skipped {skipped}")
    return rows


async def index_to_es(es, rows: list[tuple[int, str]]) -> None:
    async def actions():
        for doc_id, text in rows:
            yield {
                "_op_type": "index",
                "_index": settings.es_index,
                "_id": doc_id,
                "_source": {"id": doc_id, "text": text},
            }

    success, errors = await async_bulk(
        es, actions(), refresh=True, raise_on_error=False
    )
    if errors:
        errors_list = list(errors) if isinstance(errors, list) else []
        if errors_list:
            print(f"ES: {success} ok, {len(errors_list)} errors. First: {errors_list[0]}")
    else:
        print(f"ES: indexed {success} docs")


async def main() -> None:
    await create_schema()

    es = get_es()
    try:
        await recreate_index(es)
        rows = await load_to_postgres()
        await index_to_es(es, rows)
    finally:
        await close_es()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

