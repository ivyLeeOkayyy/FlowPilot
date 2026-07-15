from fastapi import APIRouter

from app.models import (
    AutomationFlow,
    FlowValidationResult,
    GenerationRequest,
    GenerationResponse,
    SimulationRequest,
    SimulationResult,
    FlowExplanation,
)
from app.services import (
    FlowExplanationService,
    FlowGenerationService,
    FlowSimulationService,
    FlowValidationService,
)

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.post(
    "/generate",
    response_model=GenerationResponse,
    summary="Generate a workflow from a natural-language prompt",
)
def generate_flow(request: GenerationRequest) -> GenerationResponse:
    return FlowGenerationService().generate(request)


@router.post("/validate", response_model=FlowValidationResult)
def validate_flow(flow: AutomationFlow) -> FlowValidationResult:
    return FlowValidationService().validate(flow)


@router.post("/simulate", response_model=SimulationResult)
def simulate_flow(request: SimulationRequest) -> SimulationResult:
    return FlowSimulationService().simulate(request)


@router.post("/explain", response_model=FlowExplanation)
def explain_flow(flow: AutomationFlow) -> FlowExplanation:
    return FlowExplanationService().explain(flow)
