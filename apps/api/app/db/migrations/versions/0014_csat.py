"""CSAT: satisfaction responses + conversation_threads.csat_requested_at

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-15T15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'satisfaction_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_number', sa.String(), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_satisfaction_responses_instance_sender', 'satisfaction_responses', ['instance_id', 'sender_number'])

    op.add_column('conversation_threads', sa.Column('csat_requested_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('conversation_threads', 'csat_requested_at')
    op.drop_index('ix_satisfaction_responses_instance_sender', table_name='satisfaction_responses')
    op.drop_table('satisfaction_responses')
