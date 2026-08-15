"""campaigns (broadcast)

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-15T17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0016'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column(
            'status', sa.Enum('SENDING', 'COMPLETED', 'FAILED', name='campaign_status'),
            nullable=False, server_default='SENDING',
        ),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('total_recipients', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.alter_column('campaigns', 'status', server_default=None)
    op.alter_column('campaigns', 'total_recipients', server_default=None)
    op.alter_column('campaigns', 'sent_count', server_default=None)
    op.alter_column('campaigns', 'skipped_count', server_default=None)
    op.alter_column('campaigns', 'failed_count', server_default=None)
    op.create_index('ix_campaigns_instance', 'campaigns', ['instance_id'])

    op.create_table(
        'campaign_recipients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_number', sa.String(), nullable=False),
        sa.Column(
            'status', sa.Enum('SENT', 'SKIPPED_WINDOW', 'FAILED', name='campaign_recipient_status'),
            nullable=False,
        ),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaign_recipients_campaign', 'campaign_recipients', ['campaign_id'])


def downgrade() -> None:
    op.drop_index('ix_campaign_recipients_campaign', table_name='campaign_recipients')
    op.drop_table('campaign_recipients')
    op.drop_index('ix_campaigns_instance', table_name='campaigns')
    op.drop_table('campaigns')
