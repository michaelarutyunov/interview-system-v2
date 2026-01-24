"""
Synthetic API routes.

Endpoints for generating synthetic respondent responses for testing.
"""

from typing import Annotated, Dict

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from src.api.schemas import (
    SyntheticRespondRequest,
    SyntheticRespondResponse,
    SyntheticMultiRequest,
    SyntheticSequenceRequest,
)
from src.llm.prompts.synthetic import get_available_personas
from src.services.synthetic_service import SyntheticService, get_synthetic_service

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/synthetic", tags=["synthetic"])


# ============ DEPENDENCY INJECTION ============


async def get_synthetic_service_dep() -> SyntheticService:
    """
    Dependency that provides a SyntheticService instance.

    Injected into route handlers.
    """
    return get_synthetic_service()


SyntheticServiceDep = Annotated[SyntheticService, Depends(get_synthetic_service_dep)]


# ============ ENDPOINTS ============


@router.post(
    "/respond",
    response_model=SyntheticRespondResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_synthetic_response(
    request: SyntheticRespondRequest,
    service: SyntheticServiceDep,
):
    """
    Generate a single synthetic response.

    Args:
        request: Request with question, session_id, persona, and optional context
        service: Synthetic service instance

    Returns:
        SyntheticRespondResponse with generated response and metadata

    Raises:
        HTTPException 400: If persona is invalid
        HTTPException 500: If generation fails
    """
    log.info(
        "generating_synthetic_response",
        session_id=request.session_id,
        persona=request.persona,
        question_length=len(request.question),
    )

    try:
        result = await service.generate_response(
            question=request.question,
            session_id=request.session_id,
            persona=request.persona,
            interview_context=request.interview_context,
            use_deflection=request.use_deflection,
        )

        return SyntheticRespondResponse(**result)

    except ValueError as e:
        log.warning(
            "invalid_persona",
            persona=request.persona,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        log.error(
            "synthetic_generation_failed",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate synthetic response: {e}",
        )


@router.post(
    "/respond/multi",
    response_model=list[SyntheticRespondResponse],
    status_code=status.HTTP_200_OK,
)
async def generate_multi_response(
    request: SyntheticMultiRequest,
    service: SyntheticServiceDep,
):
    """
    Generate multiple responses (one per persona).

    Args:
        request: Request with question, session_id, and optional personas list
        service: Synthetic service instance

    Returns:
        List of SyntheticRespondResponse, one per persona
    """
    log.info(
        "generating_multi_synthetic_response",
        session_id=request.session_id,
        personas=request.personas,
        question_length=len(request.question),
    )

    try:
        results = await service.generate_multi_response(
            question=request.question,
            session_id=request.session_id,
            personas=request.personas,
            interview_context=request.interview_context,
        )

        return [SyntheticRespondResponse(**result) for result in results]

    except Exception as e:
        log.error(
            "multi_synthetic_generation_failed",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate multi response: {e}",
        )


@router.post(
    "/respond/sequence",
    response_model=list[SyntheticRespondResponse],
    status_code=status.HTTP_200_OK,
)
async def generate_interview_sequence(
    request: SyntheticSequenceRequest,
    service: SyntheticServiceDep,
):
    """
    Generate responses for an interview sequence.

    Args:
        request: Request with questions list, session_id, persona, and product_name
        service: Synthetic service instance

    Returns:
        List of SyntheticRespondResponse, one per question
    """
    log.info(
        "generating_interview_sequence",
        session_id=request.session_id,
        persona=request.persona,
        question_count=len(request.questions),
    )

    try:
        results = await service.generate_interview_sequence(
            session_id=request.session_id,
            questions=request.questions,
            persona=request.persona,
            product_name=request.product_name,
        )

        return [SyntheticRespondResponse(**result) for result in results]

    except Exception as e:
        log.error(
            "sequence_generation_failed",
            session_id=request.session_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sequence: {e}",
        )


@router.get(
    "/personas",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
)
async def list_personas():
    """
    List available personas.

    Returns:
        Dict mapping persona_id to persona_name
    """
    log.info("listing_personas")

    personas = get_available_personas()
    return personas
