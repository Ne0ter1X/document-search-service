# Document Search Service

REST-сервис полнотекстового поиска по документам с фильтрацией по дате создания.  
FastAPI + PostgreSQL + Elasticsearch.

## Что делает

- **`GET /search?q=<query>&limit=20`** — поиск по тексту документа, возвращает топ-N, отсортированных по дате создания (DESC)
- **`DELETE /documents/{id}`** — удаление документа из БД и поискового индекса

## Стек

| Компонент | Технология | Зачем |
|---|---|---|
| HTTP-фреймворк | FastAPI | Async из коробки, авто-OpenAPI |
| БД | PostgreSQL 18 | Источник истины, `ARRAY` под `rubrics`, GIN-индекс |
| Поиск | Elasticsearch 8.19 | Инвертированный индекс, `russian`-analyzer |
| ORM | SQLAlchemy 2.0 (async) + asyncpg | Async-сессии, 2.0-style declarative |
| ES-клиент | elasticsearch-py (async) | Официальный async-клиент |
| Пакетный менеджер | uv | Быстрее pip, lock-файл |
| Контейнеризация | Docker + Compose | Воспроизводимость |

## Архитектура

```
       Клиент
         │
         ▼
    FastAPI (routes)
         │
         ▼
   DocumentService         ← бизнес-логика
         │
    ┌────┴────┐
    ▼         ▼
PostgreSQL  Elasticsearch
(истина)    (индекс)
```

### Как работает поиск

1. ES ищет все `id` документов, чей `text` соответствует запросу (`match` по `russian`-analyzer)
2. PG достаёт полные документы по этим `id`, сортирует по `created_date DESC`, отдаёт топ-N
3. Сортировка — **на стороне PG**, потому что в ES-индексе нет `created_date` (по ТЗ: только `id` и `text`)

### Как работает удаление

1. Сначала удаление из PG (`DELETE ... RETURNING id`)
2. Затем удаление из ES
3. Если ES упал — логируем warning, но возвращаем `204` клиенту

**Почему PG первым:** источник истины — БД. Если ES рассинхронизирован, «фантомный» id отфильтруется при следующем поиске через `WHERE id IN (...)` — пользователь его не увидит. Обратный порядок хуже: при падении PG после ES-удаления документ останется в БД, но пропадёт из поиска.

## Быстрый старт

### Требования

- Docker + Docker Compose
- Свободные порты: `5432` (PG), `9200` (ES), `8000` (API)

### Поднять одной командой

```bash
docker compose up -d
docker compose exec app python -m scripts.load_csv
```

После этого:

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- OpenAPI-спека: [docs.json](./docs.json)

### Проверка

```bash
# Поиск
curl -G "http://localhost:8000/search" \
  --data-urlencode "q=жигули" \
  --data "limit=3"

# Удаление
curl -X DELETE "http://localhost:8000/documents/1"
```

## Локальная разработка

Без Docker для приложения (инфра — в контейнерах):

```bash
# 1. Инфраструктура
docker compose up -d postgres elasticsearch

# 2. Зависимости
uv sync

# 3. Конфиг
cp .env.example .env

# 4. Загрузка данных
uv run python -m scripts.load_csv

# 5. Приложение
uv run uvicorn app.main:app --reload
```

## API

### `GET /search`

| Параметр | Тип | По умолчанию | Ограничения |
|---|---|---|---|
| `q` | string | обязательный | 1–500 символов |
| `limit` | int | 20 | 1–100 |

**Ответ:**

```json
{
  "query": "жигули",
  "total": 47,
  "returned": 3,
  "items": [
    {
      "id": 1487,
      "text": "...",
      "rubrics": ["VK-1603736028819866", "..."],
      "created_date": "2019-12-26T09:27:00"
    }
  ]
}
```

`total` — сколько документов нашёл ES, `returned` — сколько вернули после сортировки и лимита. Полезно для отладки: `total=500, returned=20` — норма, а `total=500, returned=0` — сигнал о рассинхроне индексов.

### `DELETE /documents/{id}`

- `204` — удалено
- `404` — документа с таким `id` нет

## Тесты

```bash
uv run pytest -v
```

12 тестов:
- **Unit** (6) — `DocumentService` с фейковыми репозиториями, без живых PG/ES
- **API** (6) — HTTP через `httpx.ASGITransport`, dependency overrides на фейки

Все тесты выполняются за < 1 секунды, не требуют Docker.

## Документация

- [docs.json](./docs.json) — OpenAPI-спека (генерируется из FastAPI)
- `/docs` (Swagger UI) — интерактивная документация при запущенном сервисе
- `/openapi.json` — сырая спека в рантайме

## Известные ограничения

- **`MAX_IDS=10_000`** в `SearchRepository.find_ids` — ES по умолчанию не отдаёт больше за один `search`. При росте датасета нужен **scroll API** или **PIT (point-in-time)**. Для 1500 документов не проблема.
- **Отсутствие транзакции между PG и ES.** При падении ES между коммитами возможно расхождение индексов. Митигация: периодический reindex (`scripts/load_csv.py` пересоздаёт индекс с нуля — идемпотентен).
- **Падение ES или PG** возвращает `500` — это честно: поиск невозможен без ES, удаление невозможно без PG.

## Структура проекта

```
.
├── app/
│   ├── main.py              # FastAPI-приложение, lifespan
│   ├── config.py            # Pydantic Settings
│   ├── db.py                # async engine + session factory
│   ├── es.py                # async ES-клиент (singleton)
│   ├── models.py            # SQLAlchemy: Document
│   ├── schemas.py           # Pydantic: DocumentOut, SearchResponse
│   ├── repositories/        # доступ к данным (PG, ES)
│   ├── services/            # бизнес-логика
│   └── api/routes.py        # HTTP-эндпоинты
├── scripts/
│   └── load_csv.py          # ETL: CSV -> PG + ES
├── tests/
│   ├── conftest.py          # фикстуры, фейки репозиториев
│   ├── test_service.py      # unit
│   └── test_api.py          # HTTP
├── data/
│   └── posts.csv
├── docs.json                # OpenAPI
├── Dockerfile
├── docker-compose.yaml
├── pyproject.toml
├── uv.lock
└── .env.example
```

CSV-массив из ТЗ находится в `data/posts.csv` и уже закоммичен в репозиторий.

Загрузка выполняется идемпотентно: `scripts/load_csv.py` пересоздаёт ES-индекс 
с нуля и загружает данные в PG. Повторный запуск не дублирует записи.