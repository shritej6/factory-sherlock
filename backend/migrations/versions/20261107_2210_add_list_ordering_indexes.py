"""add list ordering indexes

The paginated list endpoints order by a time column and then by ``id`` as
the tiebreak (``inspected_at DESC, id DESC`` for inspections, ``started_at``
for batches, ``created_at`` for orders and investigations). Before this
revision only ``alerts`` had a matching ``(time, id)`` index; the other four
lists sorted with a filesort over the whole table, and the control chart
(query 10) had to choose between the ``specification_id`` foreign-key index
and ``ix_inspections_time_result`` because no index covered both predicates.

Every operation is an ``ADD INDEX`` or ``DROP INDEX``, which InnoDB performs
INPLACE and online (reads and writes continue while the index is built). No
column or constraint changes.

``ix_inspections_spec_time`` leads with ``specification_id``, so it takes over
as the index behind the ``inspections.specification_id`` foreign key. MySQL
drops the implicit single-column index it created for that key as soon as
the composite index exists, but only when the index was auto-generated; an
explicitly created one of the same name is kept. The upgrade therefore drops
the single-column index if it is still there, so the schema after this
revision is the same either way, and the downgrade recreates it under its
original name before dropping the composite index (MySQL refuses to drop the
only index backing a foreign key with error 1553).

Revision ID: 6c1f0d2a9b47
Revises: 383273c26ef7
Create Date: 2026-11-07 22:10:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '6c1f0d2a9b47'
down_revision: str | None = '383273c26ef7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_INDEX = 'specification_id'
INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    ('ix_inspections_time_id', 'inspections', ['inspected_at', 'id']),
    ('ix_inspections_spec_time', 'inspections', ['specification_id', 'inspected_at']),
    ('ix_production_batches_started_id', 'production_batches', ['started_at', 'id']),
    ('ix_production_orders_created_id', 'production_orders', ['created_at', 'id']),
    ('ix_investigations_created_id', 'investigations', ['created_at', 'id']),
)


def _inspections_index_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {str(index['name']) for index in inspector.get_indexes('inspections')}


def upgrade() -> None:
    for name, table, columns in INDEXES:
        op.create_index(name, table, columns, unique=False)
    if FK_INDEX in _inspections_index_names():
        op.drop_index(FK_INDEX, table_name='inspections')


def downgrade() -> None:
    op.create_index(FK_INDEX, 'inspections', ['specification_id'], unique=False)
    for name, table, _columns in reversed(INDEXES):
        op.drop_index(name, table_name=table)
