"""Human escalation service with pluggable notifications (Discord webhook) and state control."""

from abc import ABC, abstractmethod
import logging
import re
from typing import Optional
import httpx

from backend.app.config import get_settings
from backend.app.services.session_service import get_session_service

logger = logging.getLogger(__name__)

ESCALATION_PHRASES = [
    "talk to a human",
    "talk to an agent",
    "talk to someone",
    "speak to someone",
    "speak with someone",
    "speak to a human",
    "speak to an agent",
    "real person",
    "human agent",
    "human support",
    "agent please",
    "human please",
    "connect me to a representative",
    "customer care executive",
    "operator please",
]


class NotificationBackend(ABC):
    """Abstract interface for human agent notifications."""

    @abstractmethod
    async def notify(self, session_id: str, triggering_message: str, summary: str) -> bool:
        """Send notification to human support channel."""
        pass


class DiscordNotificationBackend(NotificationBackend):
    """Sends escalation alerts to a Discord channel via incoming webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.settings = get_settings()
        self.webhook_url = webhook_url or self.settings.DISCORD_WEBHOOK_URL.strip()

    async def notify(self, session_id: str, triggering_message: str, summary: str) -> bool:
        if not self.webhook_url:
            logger.info("No DISCORD_WEBHOOK_URL configured. Escalation notification skipped for session %s.", session_id)
            return False

        payload = {
            "content": f"🚨 **NIEL AI Escalation Alert** | Session `{session_id}`",
            "embeds": [
                {
                    "title": "Human Support Requested",
                    "color": 0xD97706,  # NIEL Industrial Amber
                    "fields": [
                        {"name": "Session ID", "value": f"`{session_id}`", "inline": True},
                        {"name": "Trigger Message", "value": triggering_message or "Manual Escalation", "inline": False},
                        {"name": "Conversation Summary", "value": summary or "No previous history.", "inline": False},
                    ],
                    "footer": {"text": "NIEL Industrial Intelligence Assistant"},
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.webhook_url, json=payload)
                res.raise_for_status()
                logger.info("Discord escalation notification sent successfully for session %s", session_id)
                return True
        except Exception as exc:
            logger.error("Failed to post Discord escalation webhook for session %s: %s", session_id, exc)
            return False


class EscalationService:
    """Orchestrates keyword escalation detection, session locking, and agent notifications."""

    def __init__(self, notification_backend: Optional[NotificationBackend] = None):
        self.notification_backend = notification_backend or DiscordNotificationBackend()
        self.session_service = get_session_service()

    def check_escalation_trigger(self, text: str) -> bool:
        """Check if message explicitly asks for a human agent."""
        clean = text.lower().strip()
        if any(phrase in clean for phrase in ESCALATION_PHRASES):
            return True
        return bool(re.search(r"\b(talk|speak|connect|transfer|chat with)\b.*?\b(human|person|people|representative|agent|engineer|operator|sales|salesperson|sales\s*person|someone|executive)\b", clean))

    async def escalate_session(self, session_id: str, triggering_message: str = "") -> bool:
        """Lock session for human handoff and dispatch agent notification."""
        self.session_service.set_human_active(session_id, True)

        # Build short context summary
        history = self.session_service.get_recent_history(session_id, max_turns=4)
        summary_lines = [f"• {turn['role'].capitalize()}: {turn['content'][:100]}" for turn in history]
        summary = "\n".join(summary_lines) if summary_lines else "New session."

        logger.info("Session %s escalated to human active state. Trigger: %s", session_id, triggering_message)
        return await self.notification_backend.notify(
            session_id=session_id,
            triggering_message=triggering_message,
            summary=summary,
        )

    def resolve_session(self, session_id: str):
        """Release session back to autonomous AI assistance."""
        self.session_service.set_human_active(session_id, False)
        logger.info("Session %s resolved and returned to AI control.", session_id)


_escalation_service_instance: Optional[EscalationService] = None


def get_escalation_service() -> EscalationService:
    """Singleton accessor for EscalationService."""
    global _escalation_service_instance
    if _escalation_service_instance is None:
        _escalation_service_instance = EscalationService()
    return _escalation_service_instance
