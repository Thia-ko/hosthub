"""attendance queues (named/configurable filas + routing)

Revision ID: 0026
Revises: 0025
Create Date: 2026-08-20T16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0026'
down_revision: Union[str, None] = '0025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    queue_id_enum = postgresql.ENUM('NORMAL', 'HIGH', 'URGENT', name='queue_base_priority')
    queue_id_enum.create(bind, checkfirst=True)

    op.create_table(
        'attendance_queues',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('routing_hint', sa.Text(), nullable=True),
        sa.Column('keywords', sa.Text(), nullable=True),
        sa.Column(
            'base_priority',
            postgresql.ENUM('NORMAL', 'HIGH', 'URGENT', name='queue_base_priority', create_type=False),
            nullable=False,
            server_default='NORMAL',
        ),
        sa.Column('color', sa.String(), nullable=False, server_default='#64748b'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'slug', name='uq_attendance_queues_instance_slug'),
    )
    op.alter_column('attendance_queues', 'base_priority', server_default=None)
    op.alter_column('attendance_queues', 'color', server_default=None)
    op.alter_column('attendance_queues', 'position', server_default=None)
    op.alter_column('attendance_queues', 'is_default', server_default=None)
    op.alter_column('attendance_queues', 'active', server_default=None)
    op.create_index('ix_attendance_queues_instance_id', 'attendance_queues', ['instance_id'])

    # Every instance needs exactly one default queue to route into - backfill "Geral" for every
    # pre-existing instance (new instances get one created inline by
    # app.api.v1.routers.instances.create_instance from here on).
    op.execute(
        """
        INSERT INTO attendance_queues (id, instance_id, name, slug, base_priority, color, position, is_default, active, created_at, updated_at)
        SELECT gen_random_uuid(), id, 'Geral', 'geral', 'NORMAL', '#64748b', 0, true, true, now(), now()
        FROM instances
        """
    )

    op.add_column('conversation_threads', sa.Column('queue_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_conversation_threads_queue_id',
        'conversation_threads',
        'attendance_queues',
        ['queue_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_conversation_threads_queue_id', 'conversation_threads', ['queue_id'])

    # Backfill any thread currently sitting in an active queue lane to its instance's new
    # default queue - none expected in practice (queues didn't exist before this migration) but
    # correct in case data was seeded another way.
    op.execute(
        """
        UPDATE conversation_threads
        SET queue_id = (
            SELECT aq.id FROM attendance_queues aq
            WHERE aq.instance_id = conversation_threads.instance_id AND aq.is_default
        )
        WHERE queue_status IN ('QUEUED', 'IN_PROGRESS', 'ON_HOLD')
        """
    )


def downgrade() -> None:
    op.drop_index('ix_conversation_threads_queue_id', table_name='conversation_threads')
    op.drop_constraint('fk_conversation_threads_queue_id', 'conversation_threads', type_='foreignkey')
    op.drop_column('conversation_threads', 'queue_id')

    op.drop_index('ix_attendance_queues_instance_id', table_name='attendance_queues')
    op.drop_table('attendance_queues')
    sa.Enum(name='queue_base_priority').drop(op.get_bind())
