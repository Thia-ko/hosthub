"""whatsapp provider

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-18T00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0017'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE whatsapp_provider AS ENUM ('whatsbotmais', 'evolution', 'meta_cloud')")
    op.add_column(
        'instances',
        sa.Column(
            'whatsapp_provider',
            postgresql.ENUM('whatsbotmais', 'evolution', 'meta_cloud', name='whatsapp_provider', create_type=False),
            nullable=True,
        ),
    )
    op.add_column('instances', sa.Column('meta_phone_number_id', sa.String(), nullable=True))
    op.add_column('instances', sa.Column('meta_access_token', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('instances', 'meta_access_token')
    op.drop_column('instances', 'meta_phone_number_id')
    op.drop_column('instances', 'whatsapp_provider')
    op.execute("DROP TYPE whatsapp_provider")
