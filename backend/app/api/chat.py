from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm import llm_service

router = APIRouter(prefix="/chat", tags=["Text Chat"])

@router.post("", response_model=ChatResponse)
async def chat_message(req: ChatRequest):
    """
    Direct Bangla text chat with Shoi.
    Runs crisis detection, retrieves WHO/DGHS facts, and generates grounded warm response.
    Never persists full chat history to disk.
    """
    response = await llm_service.generate_response(
        message=req.message,
        history=req.history
    )
    return response
