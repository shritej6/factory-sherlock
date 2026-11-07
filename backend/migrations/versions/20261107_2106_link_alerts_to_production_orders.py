"""link alerts to production orders

Adds a nullable ``production_order_id`` to ``alerts`` so the ORDER_OVERDUE
check can record which order an alert is about and can find the open alert
for an order without parsing the message text. The reference is SET NULL on
delete because alerts are audit rows that should outlive the order they name.

The foreign key is named explicitly (``fk_alerts_production_order``) so the
downgrade can drop it by name; the original migration left foreign key names
to MySQL.

Revision ID: 383273c26ef7
Revises: 3a5e982c3679
Create Date: 2026-11-07 21:06:34.710177+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '383273c26ef7'
down_revision: str | None = '3a5e982c3679'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('alerts', sa.Column('production_order_id', sa.Integer(), nullable=True))
    op.create_index('ix_alerts_production_order', 'alerts', ['production_order_id'], unique=False)
    op.create_foreign_key(
        'fk_alerts_production_order',
        'alerts',
        'production_orders',
        ['production_order_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    # MySQL refuses to drop an index that backs a foreign key while the
    # constraint exists, so the constraint goes first.
    op.drop_constraint('fk_alerts_production_order', 'alerts', type_='foreignkey')
    op.drop_index('ix_alerts_production_order', table_name='alerts')
    op.drop_column('alerts', 'production_order_id')
