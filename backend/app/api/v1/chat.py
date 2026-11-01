"""RAG Chat endpoint for NIEL Industrial Intelligence Assistant."""

from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.config import Settings, get_settings
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.rag_service import get_rag_service
from backend.app.security.rate_limiter import rate_limit_guard

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit_guard)])
def ask_question(
    request: ChatRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Submit a technical question to the NIEL Industrial Intelligence Assistant.
    Answers are strictly grounded in indexed product documents with verifiable citations.
    """
    clean_question = request.question.strip()
    if len(clean_question) > settings.MAX_QUESTION_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Question exceeds maximum allowed length of {settings.MAX_QUESTION_LENGTH} characters.",
        )

    rag_service = get_rag_service()
    response = rag_service.answer_question(
        question=clean_question,
        top_k=request.top_k or settings.MAX_RETRIEVAL_CHUNKS,
        conversation_history=request.conversation_history,
        session_id=request.session_id,
    )
    return response

