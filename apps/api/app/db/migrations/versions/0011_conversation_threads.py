"""conversation threads

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-15T12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversation_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_number', sa.String(), nullable=False),
        sa.Column('last_whatsbotmais_token', sa.String(), nullable=True),
        sa.Column('ai_paused', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'sender_number', name='uq_conversation_threads_instance_sender'),
    )
    op.alter_column('conversation_threads', 'ai_paused', server_default=None)


def downgrade() -> None:
    op.drop_table('conversation_threads')
