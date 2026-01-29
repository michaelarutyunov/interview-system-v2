"""
Simulation API routes.

Endpoints for AI-to-AI interview simulation.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite
import structlog

from src.api.schemas import (
    SimulationRequest,
    SimulationResponse,
    SimulationTurnSchema,
)
from src.core.config import settings
from src.persistence.database import get_db
from src.persistence.repositories.session_repo import SessionRepository
from src.persistence.repositories.graph_repo import GraphRepository
from src.services.session_service import SessionService
from src.services.simulation_service import SimulationService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/simulation", tags=["simulation"])


# ============ DEPENDENCY INJECTION ============


async def get_simulation_service(
    db: aiosqlite.Connection = Depends(get_db),
) -> SimulationService:
    """
    Create SimulationService with dependencies.

    Args:
        db: Database connection

    Returns:
        SimulationService instance
    """
    session_repo = SessionRepository(str(settings.database_path))
    graph_repo = GraphRepository(db)

    # Create session service
    session_service = SessionService(
        session_repo=session_repo,
        graph_repo=graph_repo,
    )

    # Create simulation service (synthetic service will be created internally)
    return SimulationService(session_service=session_service)


SimulationServiceDep = Annotated[SimulationService, Depends(get_simulation_service)]


# ============ SIMULATION ENDPOINTS ============


@router.post(
    "/interview",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
)
async def simulate_interview(
    request: SimulationRequest,
    simulation_service: SimulationServiceDep = Depends(),
):
    """
    Simulate a complete AI-to-AI interview.

    Orchestrates an AI interviewer with an AI synthetic respondent
    to generate a complete interview transcript for testing.

    The simulation:
    1. Loads the concept to extract product_name and objective
    2. Creates a session with the specified max_turns
    3. Generates an opening question
    4. Loops: generates synthetic response → processes turn → generates next question
    5. Continues until max_turns or close strategy

    **Response includes:**
    - Complete transcript with all questions and responses
    - Turn-by-turn analysis (strategy selected, latency)
    - Coverage achieved
    - Status (completed, max_turns_reached, error)

    **Example request:**
    ```json
    {
        "concept_id": "oat_milk_v2",
        "persona_id": "health_conscious",
        "max_turns": 10
    }
    ```
    """
    try:
        result = await simulation_service.simulate_interview(
            concept_id=request.concept_id,
            persona_id=request.persona_id,
            max_turns=request.max_turns,
            session_id=request.session_id,
        )

        log.info(
            "simulation_completed",
            session_id=result.session_id,
            concept_id=result.concept_id,
            total_turns=result.total_turns,
        )

        return SimulationResponse(
            concept_id=result.concept_id,
            concept_name=result.concept_name,
            product_name=result.product_name,
            objective=result.objective,
            methodology=result.methodology,
            persona_id=result.persona_id,
            persona_name=result.persona_name,
            session_id=result.session_id,
            total_turns=result.total_turns,
            turns=[
                SimulationTurnSchema(
                    turn_number=t.turn_number,
                    question=t.question,
                    response=t.response,
                    persona=t.persona,
                    persona_name=t.persona_name,
                    strategy_selected=t.strategy_selected,
                    should_continue=t.should_continue,
                    latency_ms=t.latency_ms,
                )
                for t in result.turns
            ],
            status=result.status,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept not found: {request.concept_id}",
        )
    except Exception as e:
        log.error("simulation_failed", error=str(e), concept_id=request.concept_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}",
        )
