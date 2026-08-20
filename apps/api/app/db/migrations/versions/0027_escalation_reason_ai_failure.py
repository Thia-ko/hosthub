"""escalation_reason: add AI_FAILURE value

Revision ID: 0027
Revises: 0026
Create Date: 2026-08-20T18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0027'
down_revision: Union[str, None] = '0026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New value only, not referenced by another statement in this same transaction - safe on
    # PG12+ (same pattern as 0010/0021/0024). SQLAlchemy stores the Python Enum member NAME
    # (not .value) for this column - matches the existing CUSTOMER_REQUEST/AI_UNCERTAIN values
    # already in this type.
    op.execute("ALTER TYPE escalation_reason ADD VALUE IF NOT EXISTS 'AI_FAILURE'")


def downgrade() -> None:
    # Postgres cannot drop a single enum value; 'AI_FAILURE' is left in escalation_reason.
    pass
