"""instance plans and feature overrides

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-19T23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0023'
down_revision: Union[str, None] = '0022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE instance_plan AS ENUM ('STARTER', 'PRO', 'ENTERPRISE')")
    op.add_column(
        'instances',
        sa.Column(
            'plan',
            sa.Enum('STARTER', 'PRO', 'ENTERPRISE', name='instance_plan', create_type=False),
            nullable=False,
            server_default='STARTER',
        ),
    )
    op.alter_column('instances', 'plan', server_default=None)

    op.add_column('instances', sa.Column('ai_enabled_override', sa.Boolean(), nullable=True))
    op.add_column('instances', sa.Column('campaigns_enabled_override', sa.Boolean(), nullable=True))
    op.add_column('instances', sa.Column('api_access_enabled_override', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('instances', 'api_access_enabled_override')
    op.drop_column('instances', 'campaigns_enabled_override')
    op.drop_column('instances', 'ai_enabled_override')
    op.drop_column('instances', 'plan')
    op.execute("DROP TYPE instance_plan")
