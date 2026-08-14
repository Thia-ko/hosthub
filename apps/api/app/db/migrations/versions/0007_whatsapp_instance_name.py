"""whatsapp instance name

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-13 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('instances', sa.Column('whatsapp_instance_name', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('instances', 'whatsapp_instance_name')
