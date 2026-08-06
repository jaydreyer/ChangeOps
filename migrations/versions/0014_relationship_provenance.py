"""Add trusted relationship provenance.

Revision ID: 0014_relationship_provenance
Revises: 0013_confluence_document_sources
Create Date: 2026-08-06
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0014_relationship_provenance"
down_revision: str | None = "0013_confluence_document_sources"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROVENANCE_RECORDED_AT = datetime(2026, 8, 6, tzinfo=UTC)
PROVENANCE_AUTHORITY = "ChangeOps demonstration seed"
PROVENANCE_REFERENCE = "changeops.seed.relationships.v1"

CANONICAL_IDS = {
    "policy_system_dependencies": (
        "dependency-policy-travel-request",
        "dependency-policy-travel-request-proposed",
        "dependency-policy-learning-management",
        "dependency-policy-learning-management-proposed",
    ),
    "policy_document_dependencies": (
        "dependency-policy-primary-document",
        "dependency-policy-primary-document-proposed",
        "dependency-policy-booking-article",
        "dependency-policy-booking-article-proposed",
        "dependency-policy-manager-guide",
        "dependency-policy-manager-guide-proposed",
    ),
    "policy_training_dependencies": (
        "dependency-policy-security-course",
        "dependency-policy-security-course-proposed",
    ),
}


def upgrade() -> None:
    for table_name in CANONICAL_IDS:
        op.add_column(
            table_name,
            sa.Column("provenance_category", sa.String(length=40), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("provenance_authority", sa.String(length=200), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("provenance_reference", sa.String(length=100), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("provenance_recorded_at", sa.DateTime(timezone=True), nullable=True),
        )

    for table_name, canonical_ids in CANONICAL_IDS.items():
        quoted_ids = ", ".join(f"'{item}'" for item in canonical_ids)
        op.execute(
            sa.text(
                f"""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM {table_name}
                        WHERE id NOT IN ({quoted_ids})
                    ) THEN
                        RAISE EXCEPTION
                            'Cannot assign seeded provenance to noncanonical rows in {table_name}';
                    END IF;
                END
                $$;
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                SET provenance_category = 'seeded_demonstration',
                    provenance_authority = :authority,
                    provenance_reference = :reference,
                    provenance_recorded_at = :recorded_at
                WHERE id IN ({quoted_ids})
                """
            ).bindparams(
                authority=PROVENANCE_AUTHORITY,
                reference=PROVENANCE_REFERENCE,
                recorded_at=PROVENANCE_RECORDED_AT,
            )
        )

        for column_name in (
            "provenance_category",
            "provenance_authority",
            "provenance_reference",
            "provenance_recorded_at",
        ):
            op.alter_column(table_name, column_name, nullable=False)

        op.create_check_constraint(
            f"ck_{table_name}_provenance_category",
            table_name,
            "provenance_category = 'seeded_demonstration'",
        )
        op.create_check_constraint(
            f"ck_{table_name}_provenance_authority",
            table_name,
            "length(btrim(provenance_authority)) > 0",
        )
        op.create_check_constraint(
            f"ck_{table_name}_provenance_reference",
            table_name,
            "length(btrim(provenance_reference)) > 0",
        )


def downgrade() -> None:
    for table_name in reversed(tuple(CANONICAL_IDS)):
        op.drop_constraint(
            f"ck_{table_name}_provenance_reference",
            table_name,
            type_="check",
        )
        op.drop_constraint(
            f"ck_{table_name}_provenance_authority",
            table_name,
            type_="check",
        )
        op.drop_constraint(
            f"ck_{table_name}_provenance_category",
            table_name,
            type_="check",
        )
        op.drop_column(table_name, "provenance_recorded_at")
        op.drop_column(table_name, "provenance_reference")
        op.drop_column(table_name, "provenance_authority")
        op.drop_column(table_name, "provenance_category")
