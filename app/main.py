"""Ponto de entrada da aplicação FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers.financeiro import router as financeiro_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="FinanScope API",
    description=(
        "Importe lançamentos financeiros fictícios por CSV, consulte-os e gere "
        "relatórios mensais e por categoria."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(financeiro_router)


@app.get("/health", tags=["Saúde"])
def health() -> dict[str, str]:
    return {"status": "ok"}
