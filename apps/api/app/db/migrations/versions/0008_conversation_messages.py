"""conversation messages

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-14 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('conversation_messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('instance_id', sa.UUID(), nullable=False),
    sa.Column('sender_number', sa.String(), nullable=False),
    sa.Column('direction', sa.Enum('INBOUND', 'OUTBOUND', name='message_direction'), nullable=False),
    sa.Column('kind', sa.Enum('TEXT', 'AUDIO', 'IMAGE', name='message_kind'), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('media_url', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'ix_conversation_messages_instance_sender_created',
        'conversation_messages',
        ['instance_id', 'sender_number', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_conversation_messages_instance_sender_created', table_name='conversation_messages')
    op.drop_table('conversation_messages')
