"""Administrative endpoints for Human Agent Escalation dashboard."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.api.v1.ws_chat import get_connection_manager
from backend.app.security.auth import verify_admin_key
from backend.app.services.escalation_service import get_escalation_service
from backend.app.services.session_service import get_session_service

router = APIRouter(prefix="/escalations", tags=["Escalations"])


class HumanReplyRequest(BaseModel):
    """Payload for human agent reply."""
    content: str = Field(..., min_length=1, max_length=2000, description="Message from human support engineer.")


@router.get("", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_admin_key)])
def list_escalations():
    """List all sessions currently flagged as human_active for agent attention."""
    session_service = get_session_service()
    return session_service.list_escalated_sessions()


@router.get("/{session_id}/messages", response_model=List[Dict[str, Any]], dependencies=[Depends(verify_admin_key)])
def get_session_messages(session_id: str):
    """Get complete chronological message history for a given session."""
    session_service = get_session_service()
    return session_service.get_full_history(session_id)


@router.post("/{session_id}/reply", dependencies=[Depends(verify_admin_key)])
async def reply_to_session(session_id: str, payload: HumanReplyRequest):
    """
    Human support agent sends a response to the visitor.
    Persists turn as 'agent' and pushes to the visitor over their open WebSocket.
    """
    session_service = get_session_service()
    manager = get_connection_manager()

    # Ensure session is active
    if not session_service.is_human_active(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not currently in an escalated human_active state.",
        )

    # Persist agent message
    msg = session_service.add_message(
        session_id=session_id,
        role="agent",
        content=payload.content,
    )

    # Push to visitor's open WebSocket connection
    await manager.broadcast_to_session(session_id, {
        "type": "agent_message",
        "role": "agent",
        "content": payload.content,
        "human_active": True,
    })

    return {
        "status": "delivered",
        "session_id": session_id,
        "message_id": msg.id,
        "content": payload.content,
    }


@router.post("/{session_id}/resolve", dependencies=[Depends(verify_admin_key)])
async def resolve_session(session_id: str):
    """
    Mark an escalated session as resolved and return conversational control to AI.
    """
    escalation_service = get_escalation_service()
    manager = get_connection_manager()

    escalation_service.resolve_session(session_id)

    # Notify visitor over WebSocket that AI has resumed
    await manager.broadcast_to_session(session_id, {
        "type": "session_resolved",
        "human_active": False,
        "answer": "Your human support session has concluded. I am here to continue helping you with technical product questions!",
    })

    return {
        "status": "resolved",
        "session_id": session_id,
        "human_active": False,
    }
