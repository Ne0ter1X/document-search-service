from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db import engine
from app.es import close_es, get_es


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_es()
    yield

    await close_es()
    await engine.dispose()


app = FastAPI(
    title="Search Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)