"""Add read-only Confluence document identity.

Revision ID: 0013_confluence_document_sources
Revises: 0012_jira_execution
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_confluence_document_sources"
down_revision: str | None = "0012_jira_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confluence_document_sources",
        sa.Column("document_id", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("external_page_id", sa.String(length=100), nullable=False),
        sa.Column("external_title", sa.String(length=300), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("space_id", sa.String(length=100), nullable=False),
        sa.Column("space_key", sa.String(length=100), nullable=False),
        sa.Column("external_version", sa.Integer(), nullable=False),
        sa.Column("external_status", sa.String(length=30), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("last_refresh_result", sa.String(length=40), nullable=False),
        sa.Column("last_refresh_message", sa.Text(), nullable=False),
        sa.Column("last_refresh_attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "provider = 'confluence_cloud'",
            name="ck_confluence_document_sources_provider",
        ),
        sa.CheckConstraint(
            "external_version > 0",
            name="ck_confluence_document_sources_external_version",
        ),
        sa.CheckConstraint(
            "external_status IN ('current', 'draft', 'archived')",
            name="ck_confluence_document_sources_external_status",
        ),
        sa.CheckConstraint(
            "last_refresh_result IN "
            "('success', 'already_current', 'authentication_failure', "
            "'permission_denied', 'page_not_found', 'provider_unavailable', "
            "'validation_failure', 'ambiguous_response')",
            name="ck_confluence_document_sources_last_refresh_result",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["enterprise_documents.id"]),
        sa.PrimaryKeyConstraint("document_id"),
        sa.UniqueConstraint(
            "external_page_id",
            name="uq_confluence_document_sources_external_page",
        ),
    )


def downgrade() -> None:
    op.drop_table("confluence_document_sources")
