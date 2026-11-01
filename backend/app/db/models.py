"""SQLAlchemy models for ChatSession, ChatMessage, Customer, SalesLead, and SupportTicket persistence."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Customer(Base):
    """Database model for persistent customer profile and consented contact details."""
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    interests_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of product tags
    preferences_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON dict of preferences
    consented_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="customer",
    )
    leads: Mapped[List["SalesLead"]] = relationship(
        "SalesLead",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket",
        back_populates="customer",
        cascade="all, delete-orphan",
    )


class ChatSession(Base):
    """Database model for persistent visitor chat sessions."""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    human_active: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer",
        back_populates="sessions",
    )
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
    leads: Mapped[List["SalesLead"]] = relationship(
        "SalesLead",
        back_populates="session",
    )
    tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket",
        back_populates="session",
    )


class ChatMessage(Base):
    """Database model for recorded conversation turns."""
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20))  # "user", "assistant", "agent"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    citations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class SalesLead(Base):
    """Database model for high-intent B2B sales enquiries and RFQ requirements."""
    __tablename__ = "sales_leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_interest: Mapped[str] = mapped_column(String(255))
    requirement_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="NEW")  # NEW, QUALIFIED, CONTACTED, CLOSED
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="leads")
    session: Mapped[Optional["ChatSession"]] = relationship("ChatSession", back_populates="leads")


class SupportTicket(Base):
    """Database model for post-sales support and service requests with unique tracking codes."""
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g. "TK-2026-0001"
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_category: Mapped[str] = mapped_column(String(100))  # Motors, Pumps, Transformers, Switchgear Panels
    issue_description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status: Mapped[str] = mapped_column(String(50), default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="tickets")
    session: Mapped[Optional["ChatSession"]] = relationship("ChatSession", back_populates="tickets")
