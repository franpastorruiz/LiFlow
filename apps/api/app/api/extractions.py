from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_extractor
from app.db.session import get_session
from app.extraction.base import Extractor
from app.extraction.errors import (
    ExtractionProviderError,
    ExtractionResponseError,
    ExtractionTimeoutError,
)
from app.schemas.extraction import ExtractionRequest, ExtractionResult, StoredExtractionRequest
from app.services.persistence import (
    PersistenceError,
    TrackerNotFoundError,
    get_tracker_for_development_user,
    persist_extraction,
    tracker_to_context,
)


router = APIRouter(prefix="/v1", tags=["extractions"])


@router.post("/extractions", response_model=ExtractionResult)
def extract_text(
    request: StoredExtractionRequest,
    extractor: Annotated[Extractor, Depends(get_extractor)],
    session: Annotated[Session, Depends(get_session)],
) -> ExtractionResult:
    try:
        tracker = get_tracker_for_development_user(session, request.tracker_key)
        result = extractor.extract(
            ExtractionRequest(
                text=request.text,
                reference_date=request.reference_date,
                timezone=request.timezone,
                tracker=tracker_to_context(tracker),
            )
        )
        persist_extraction(session, tracker, result, request.text)
        return result
    except TrackerNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested tracker does not exist.",
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
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The extracted data could not be stored safely.",
        ) from error
