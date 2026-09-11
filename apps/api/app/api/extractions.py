from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_extractor
from app.core.config import ConfigurationError
from app.extraction.base import Extractor
from app.extraction.errors import (
    ExtractionProviderError,
    ExtractionResponseError,
    ExtractionTimeoutError,
)
from app.schemas.extraction import ExtractionRequest, ExtractionResult


router = APIRouter(prefix="/v1", tags=["extractions"])


@router.post("/extractions", response_model=ExtractionResult)
def extract_text(
    request: ExtractionRequest,
    extractor: Annotated[Extractor, Depends(get_extractor)],
) -> ExtractionResult:
    try:
        return extractor.extract(request)
    except ConfigurationError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The extraction provider is not configured.",
        ) from error
    except ExtractionTimeoutError as error:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The extraction provider timed out.",
        ) from error
    except ExtractionResponseError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The extraction provider returned an invalid result.",
        ) from error
    except ExtractionProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The extraction provider is unavailable.",
        ) from error
