"""instance members (multi-seat)

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-15T16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'instance_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('OWNER', 'MEMBER', name='instance_member_role'), nullable=False, server_default='MEMBER'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'user_id', name='uq_instance_members_instance_user'),
    )
    op.alter_column('instance_members', 'role', server_default=None)
    op.create_index('ix_instance_members_instance', 'instance_members', ['instance_id'])
    op.create_index('ix_instance_members_user', 'instance_members', ['user_id'])

    # Backfill: every existing instance's current owner_user_id becomes its OWNER membership row,
    # so get_owned_instance's membership check (replacing the old owner_user_id equality check)
    # keeps working for every instance that already existed before this migration.
    op.execute(
        """
        INSERT INTO instance_members (id, instance_id, user_id, role, created_at)
        SELECT gen_random_uuid(), id, owner_user_id, 'OWNER', now()
        FROM instances
        """
    )


def downgrade() -> None:
    op.drop_index('ix_instance_members_user', table_name='instance_members')
    op.drop_index('ix_instance_members_instance', table_name='instance_members')
    op.drop_table('instance_members')
    sa.Enum(name='instance_member_role').drop(op.get_bind())
