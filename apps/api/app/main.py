from fastapi import FastAPI

from app.api.extractions import router as extraction_router
from app.api.trackers import router as tracker_router
from app.schemas.event import LifeEvent

app = FastAPI(
    title="Liflow API",
    version="0.1.0",
    description="API para convertir registros personales en eventos estructurados.",
)

app.include_router(extraction_router)
app.include_router(tracker_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/entries/validate", response_model=LifeEvent)
def validate_entry(entry: LifeEvent) -> LifeEvent:
    """Validate a generic personal event before it is persisted."""
    return entry
