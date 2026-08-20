"""conversation queue (filas de atendimento)

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-20T15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0025'
down_revision: Union[str, None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    queue_status_enum = postgresql.ENUM(
        'NONE', 'QUEUED', 'IN_PROGRESS', 'ON_HOLD', 'RESOLVED', name='queue_status'
    )
    escalation_reason_enum = postgresql.ENUM('CUSTOMER_REQUEST', 'AI_UNCERTAIN', name='escalation_reason')
    # `op.add_column` on an existing table, unlike `op.create_table`, does not auto-issue
    # CREATE TYPE for a new enum - has to be created explicitly first, then referenced with
    # create_type=False so add_column doesn't try (and fail) to create it again.
    queue_status_enum.create(bind, checkfirst=True)
    escalation_reason_enum.create(bind, checkfirst=True)

    op.add_column(
        'conversation_threads',
        sa.Column(
            'queue_status',
            postgresql.ENUM(
                'NONE', 'QUEUED', 'IN_PROGRESS', 'ON_HOLD', 'RESOLVED', name='queue_status', create_type=False
            ),
            nullable=False,
            server_default='NONE',
        ),
    )
    op.add_column(
        'conversation_threads',
        sa.Column(
            'escalation_reason',
            postgresql.ENUM('CUSTOMER_REQUEST', 'AI_UNCERTAIN', name='escalation_reason', create_type=False),
            nullable=True,
        ),
    )
    op.add_column('conversation_threads', sa.Column('ai_confidence', sa.Integer(), nullable=True))
    op.add_column(
        'conversation_threads', sa.Column('assigned_agent_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column('conversation_threads', sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversation_threads', sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversation_threads', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_conversation_threads_assigned_agent_id',
        'conversation_threads',
        'users',
        ['assigned_agent_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.alter_column('conversation_threads', 'queue_status', server_default=None)
    op.create_index(
        'ix_conversation_threads_instance_queue_status', 'conversation_threads', ['instance_id', 'queue_status']
    )

    op.create_table(
        'agent_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status',
            sa.Enum('ONLINE', 'BUSY', 'AWAY', 'OFFLINE', name='agent_availability'),
            nullable=False,
            server_default='OFFLINE',
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'user_id', name='uq_agent_profiles_instance_user'),
    )
    op.alter_column('agent_profiles', 'status', server_default=None)

    op.create_table(
        'queue_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'event_type', sa.Enum('QUEUED', 'CLAIMED', 'RESOLVED', name='queue_event_type'), nullable=False
        ),
        sa.Column('agent_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['conversation_threads.id']),
        sa.ForeignKeyConstraint(['agent_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_queue_events_thread_id', 'queue_events', ['thread_id'])


def downgrade() -> None:
    op.drop_index('ix_queue_events_thread_id', table_name='queue_events')
    op.drop_table('queue_events')
    sa.Enum(name='queue_event_type').drop(op.get_bind())

    op.drop_table('agent_profiles')
    sa.Enum(name='agent_availability').drop(op.get_bind())

    op.drop_index('ix_conversation_threads_instance_queue_status', table_name='conversation_threads')
    op.drop_constraint('fk_conversation_threads_assigned_agent_id', 'conversation_threads', type_='foreignkey')
    op.drop_column('conversation_threads', 'resolved_at')
    op.drop_column('conversation_threads', 'assigned_at')
    op.drop_column('conversation_threads', 'queued_at')
    op.drop_column('conversation_threads', 'assigned_agent_id')
    op.drop_column('conversation_threads', 'ai_confidence')
    op.drop_column('conversation_threads', 'escalation_reason')
    op.drop_column('conversation_threads', 'queue_status')
    sa.Enum(name='escalation_reason').drop(op.get_bind())
    sa.Enum(name='queue_status').drop(op.get_bind())
