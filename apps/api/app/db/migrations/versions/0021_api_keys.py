"""api keys + API message origin

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-19T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0021'
down_revision: Union[str, None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New value only, not used anywhere in this same transaction - safe on PG12+.
    op.execute("ALTER TYPE message_origin ADD VALUE IF NOT EXISTS 'API'")

    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('instance_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_prefix', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash'),
    )
    op.alter_column('api_keys', 'active', server_default=None)
    op.create_index('ix_api_keys_instance_id', 'api_keys', ['instance_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])


def downgrade() -> None:
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_instance_id', table_name='api_keys')
    op.drop_table('api_keys')
    # Postgres cannot drop a single enum value; downgrade intentionally leaves 'API' in place.
