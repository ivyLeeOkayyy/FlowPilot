from fastapi import APIRouter

from app.models import (
    AutomationFlow,
    FlowValidationResult,
    SimulationRequest,
    SimulationResult,
)
from app.services import FlowSimulationService, FlowValidationService

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.post("/validate", response_model=FlowValidationResult)
def validate_flow(flow: AutomationFlow) -> FlowValidationResult:
    return FlowValidationService().validate(flow)


@router.post("/simulate", response_model=SimulationResult)
def simulate_flow(request: SimulationRequest) -> SimulationResult:
    return FlowSimulationService().simulate(request)
