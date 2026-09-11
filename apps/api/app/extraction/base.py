from typing import Protocol

from app.schemas.extraction import ExtractionRequest, ExtractionResult


class Extractor(Protocol):
    """Common contract implemented by every Liflow extraction provider."""

    def extract(self, request: ExtractionRequest) -> ExtractionResult: ...
