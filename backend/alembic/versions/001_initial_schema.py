"""Initial schema for NIEL PostgreSQL and SQLite database.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-03 14:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("interests_json", sa.Text(), nullable=True),
        sa.Column("preferences_json", sa.Text(), nullable=True),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_customers_id", "customers", ["id"])
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_created_at", "customers", ["created_at"])

    # 2. chat_sessions table
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("customer_id", sa.String(length=64), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("human_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_chat_sessions_id", "chat_sessions", ["id"])
    op.create_index("ix_chat_sessions_customer_id", "chat_sessions", ["customer_id"])
    op.create_index("ix_chat_sessions_created_at", "chat_sessions", ["created_at"])

    # 3. chat_messages table
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("citations_json", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    # 4. sales_leads table
    op.create_table(
        "sales_leads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.String(length=64), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_interest", sa.String(length=255), nullable=False),
        sa.Column("requirement_details", sa.Text(), nullable=True),
        sa.Column("required_quantity", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="NEW"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sales_leads_customer_id", "sales_leads", ["customer_id"])
    op.create_index("ix_sales_leads_session_id", "sales_leads", ["session_id"])
    op.create_index("ix_sales_leads_status", "sales_leads", ["status"])
    op.create_index("ix_sales_leads_priority", "sales_leads", ["priority"])
    op.create_index("ix_sales_leads_created_at", "sales_leads", ["created_at"])

    # 5. support_tickets table
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("customer_id", sa.String(length=64), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.String(length=64), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("product_category", sa.String(length=100), nullable=False),
        sa.Column("issue_description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_support_tickets_customer_id", "support_tickets", ["customer_id"])
    op.create_index("ix_support_tickets_session_id", "support_tickets", ["session_id"])
    op.create_index("ix_support_tickets_severity", "support_tickets", ["severity"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])
    op.create_index("ix_support_tickets_created_at", "support_tickets", ["created_at"])

    # 6. flagged_queries table
    op.create_table(
        "flagged_queries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_question", sa.Text(), nullable=False),
        sa.Column("product_category", sa.String(length=100), nullable=False),
        sa.Column("unverified_field", sa.String(length=255), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_flagged_queries_session_id", "flagged_queries", ["session_id"])


def downgrade() -> None:
    op.drop_table("flagged_queries")
    op.drop_table("support_tickets")
    op.drop_table("sales_leads")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("customers")

