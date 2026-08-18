"""instance knowledge files

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-18T01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'instance_knowledge_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('kind', sa.Enum('TEXT', 'IMAGE', 'AUDIO', 'VIDEO', name='knowledge_file_kind'), nullable=False),
        sa.Column(
            'usage_mode',
            sa.Enum('AUTO', 'MANUAL', 'DISABLED', name='knowledge_file_usage_mode'),
            nullable=False,
            server_default='AUTO',
        ),
        sa.Column('include_next', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            'status',
            sa.Enum('READY', 'PROCESSING_FAILED', name='knowledge_file_status'),
            nullable=False,
            server_default='READY',
        ),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.alter_column('instance_knowledge_files', 'usage_mode', server_default=None)
    op.alter_column('instance_knowledge_files', 'include_next', server_default=None)
    op.alter_column('instance_knowledge_files', 'status', server_default=None)
    op.create_index(
        'ix_instance_knowledge_files_instance_id', 'instance_knowledge_files', ['instance_id']
    )


def downgrade() -> None:
    op.drop_index('ix_instance_knowledge_files_instance_id', table_name='instance_knowledge_files')
    op.drop_table('instance_knowledge_files')
    sa.Enum(name='knowledge_file_status').drop(op.get_bind())
    sa.Enum(name='knowledge_file_usage_mode').drop(op.get_bind())
    sa.Enum(name='knowledge_file_kind').drop(op.get_bind())
