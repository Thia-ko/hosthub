"""conversation message origin

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-18T02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE message_origin AS ENUM ('AI', 'HUMAN', 'SYSTEM')")
    op.add_column(
        'conversation_messages',
        sa.Column(
            'origin',
            postgresql.ENUM('AI', 'HUMAN', 'SYSTEM', name='message_origin', create_type=False),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('conversation_messages', 'origin')
    op.execute("DROP TYPE message_origin")
