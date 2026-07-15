from fastapi import APIRouter

from app.models import (
    AutomationFlow,
    FlowValidationResult,
    SimulationRequest,
    SimulationResult,
    FlowExplanation,
)
from app.services import (
    FlowExplanationService,
    FlowSimulationService,
    FlowValidationService,
)

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.post("/validate", response_model=FlowValidationResult)
def validate_flow(flow: AutomationFlow) -> FlowValidationResult:
    return FlowValidationService().validate(flow)


@router.post("/simulate", response_model=SimulationResult)
def simulate_flow(request: SimulationRequest) -> SimulationResult:
    return FlowSimulationService().simulate(request)


@router.post("/explain", response_model=FlowExplanation)
def explain_flow(flow: AutomationFlow) -> FlowExplanation:
    return FlowExplanationService().explain(flow)
