from fastapi import APIRouter

from app.models import AutomationFlow, FlowValidationResult
from app.services import FlowValidationService

router = APIRouter(prefix="/api/flows", tags=["flows"])


@router.post("/validate", response_model=FlowValidationResult)
def validate_flow(flow: AutomationFlow) -> FlowValidationResult:
    return FlowValidationService().validate(flow)
