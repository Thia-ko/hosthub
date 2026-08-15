"""outbound webhook subscriptions

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-15T14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'outbound_webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('events', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.alter_column('outbound_webhook_subscriptions', 'events', server_default=None)
    op.alter_column('outbound_webhook_subscriptions', 'active', server_default=None)
    op.create_index(
        'ix_outbound_webhook_subscriptions_instance', 'outbound_webhook_subscriptions', ['instance_id']
    )


def downgrade() -> None:
    op.drop_index('ix_outbound_webhook_subscriptions_instance', table_name='outbound_webhook_subscriptions')
    op.drop_table('outbound_webhook_subscriptions')
