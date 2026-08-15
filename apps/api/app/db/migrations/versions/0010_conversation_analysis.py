"""conversation analysis

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-14T18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'extracted_data',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('occurrences', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'category', 'key', name='uq_extracted_data_instance_category_key'),
    )
    op.create_index('ix_extracted_data_instance_category', 'extracted_data', ['instance_id', 'category'])

    op.create_table(
        'faq_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_id', sa.UUID(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('asked_by', sa.String(), nullable=False),
        sa.Column('frequency', sa.Integer(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_faq_items_instance_category', 'faq_items', ['instance_id', 'category'])

    op.create_table(
        'attendant_patterns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_id', sa.UUID(), nullable=False),
        sa.Column('pattern_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('examples', sa.Text(), nullable=False),
        sa.Column('frequency', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_attendant_patterns_instance_type', 'attendant_patterns', ['instance_id', 'pattern_type'])

    op.create_table(
        'conversation_analyses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_id', sa.UUID(), nullable=False),
        sa.Column('sender_number', sa.String(), nullable=False),
        sa.Column('message_count', sa.Integer(), nullable=False),
        sa.Column('raw_result', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['instances.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_conversation_analyses_instance_sender', 'conversation_analyses', ['instance_id', 'sender_number']
    )

    op.add_column('instances', sa.Column('auto_generate_prompt', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column(
        'instances', sa.Column('auto_gen_conversation_threshold', sa.Integer(), nullable=False, server_default='5')
    )
    op.add_column(
        'instances', sa.Column('auto_gen_interval', sa.String(), nullable=False, server_default='off')
    )
    op.add_column('instances', sa.Column('last_auto_gen_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('instances', 'auto_generate_prompt', server_default=None)
    op.alter_column('instances', 'auto_gen_conversation_threshold', server_default=None)
    op.alter_column('instances', 'auto_gen_interval', server_default=None)

    op.add_column('prompt_versions', sa.Column('is_pending', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('prompt_versions', 'is_pending', server_default=None)

    # Requires Postgres 12+: adding an enum value inside a transaction is fine as long as the
    # new value is not referenced by another statement in this same transaction.
    # SQLAlchemy stores the Python Enum member NAME (not .value) for this column - matches the
    # existing MANUAL/AI_ASSIST/TEMPLATE values already in this type.
    op.execute("ALTER TYPE prompt_version_source ADD VALUE IF NOT EXISTS 'AUTO_GENERATED'")


def downgrade() -> None:
    op.drop_column('prompt_versions', 'is_pending')

    op.drop_column('instances', 'last_auto_gen_at')
    op.drop_column('instances', 'auto_gen_interval')
    op.drop_column('instances', 'auto_gen_conversation_threshold')
    op.drop_column('instances', 'auto_generate_prompt')

    op.drop_index('ix_conversation_analyses_instance_sender', table_name='conversation_analyses')
    op.drop_table('conversation_analyses')

    op.drop_index('ix_attendant_patterns_instance_type', table_name='attendant_patterns')
    op.drop_table('attendant_patterns')

    op.drop_index('ix_faq_items_instance_category', table_name='faq_items')
    op.drop_table('faq_items')

    op.drop_index('ix_extracted_data_instance_category', table_name='extracted_data')
    op.drop_table('extracted_data')

    # Postgres cannot drop a single enum value; 'AUTO_GENERATED' is left in prompt_version_source.
