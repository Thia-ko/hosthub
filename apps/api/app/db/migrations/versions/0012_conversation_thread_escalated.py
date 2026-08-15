"""conversation thread escalated flag

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-15T13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversation_threads', sa.Column('escalated', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.alter_column('conversation_threads', 'escalated', server_default=None)


def downgrade() -> None:
    op.drop_column('conversation_threads', 'escalated')
