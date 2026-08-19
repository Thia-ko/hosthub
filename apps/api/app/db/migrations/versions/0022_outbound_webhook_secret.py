"""outbound webhook signing secret

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-19T22:00:00.000000

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0022'
down_revision: Union[str, None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('outbound_webhook_subscriptions', sa.Column('secret', sa.String(), nullable=True))

    # Backfill: existing rows predate the column and need a real per-row secret, not a shared
    # placeholder - generated in Python since Postgres has no built-in secure-random-string SQL.
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id FROM outbound_webhook_subscriptions")).fetchall()
    for row in rows:
        connection.execute(
            sa.text("UPDATE outbound_webhook_subscriptions SET secret = :secret WHERE id = :id"),
            {"secret": secrets.token_urlsafe(32), "id": row.id},
        )

    op.alter_column('outbound_webhook_subscriptions', 'secret', nullable=False)


def downgrade() -> None:
    op.drop_column('outbound_webhook_subscriptions', 'secret')
