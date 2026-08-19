"""chatbot nodes (deterministic non-AI reply tree)

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-19T23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0024'
down_revision: Union[str, None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE message_origin ADD VALUE IF NOT EXISTS 'CHATBOT'")

    op.add_column('instances', sa.Column('chatbot_enabled_override', sa.Boolean(), nullable=True))

    op.create_table(
        'chatbot_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('keywords', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False
        ),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id']),
        sa.ForeignKeyConstraint(['parent_id'], ['chatbot_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.alter_column('chatbot_nodes', 'order_index', server_default=None)
    op.create_index('ix_chatbot_nodes_instance_id', 'chatbot_nodes', ['instance_id'])
    op.create_index('ix_chatbot_nodes_parent_id', 'chatbot_nodes', ['parent_id'])
    # Enforces a single root (parent_id IS NULL) per instance - a partial unique index, not a
    # plain UniqueConstraint, since Postgres treats every NULL as distinct otherwise.
    op.execute(
        "CREATE UNIQUE INDEX uq_chatbot_nodes_one_root ON chatbot_nodes (instance_id) WHERE parent_id IS NULL"
    )

    op.add_column(
        'conversation_threads', sa.Column('chatbot_node_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_conversation_threads_chatbot_node_id',
        'conversation_threads',
        'chatbot_nodes',
        ['chatbot_node_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_conversation_threads_chatbot_node_id', 'conversation_threads', type_='foreignkey'
    )
    op.drop_column('conversation_threads', 'chatbot_node_id')
    op.execute("DROP INDEX uq_chatbot_nodes_one_root")
    op.drop_index('ix_chatbot_nodes_parent_id', table_name='chatbot_nodes')
    op.drop_index('ix_chatbot_nodes_instance_id', table_name='chatbot_nodes')
    op.drop_table('chatbot_nodes')
    op.drop_column('instances', 'chatbot_enabled_override')
    # Postgres cannot remove a value from an enum type; downgrade intentionally leaves 'CHATBOT'.
