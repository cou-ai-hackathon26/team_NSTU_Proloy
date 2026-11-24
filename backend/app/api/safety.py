from fastapi import APIRouter
from app.schemas.safety import SafetyCheckRequest, SafetyCheckResponse
from app.services.crisis_detector import detect_crisis

router = APIRouter(prefix="/safety", tags=["Crisis Safety Guardrails"])

@router.post("/check", response_model=SafetyCheckResponse)
def check_safety(req: SafetyCheckRequest):
    """
    Direct endpoint for crisis & emotional distress screening.
    Never stores or logs the triggering input text.
    """
    return detect_crisis(req.text)
