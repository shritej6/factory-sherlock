"""Revision 6c1f0d2a9b47: the list orderings and the control chart have matching indexes.

The checks read the migrated schema through the SQLAlchemy inspector, so they
observe what Alembic created, not what the models declare.
"""

from sqlalchemy import inspect
from sqlalchemy.orm import Session

EXPECTED = {
    ("inspections", "ix_inspections_time_id"): ["inspected_at", "id"],
    ("inspections", "ix_inspections_spec_time"): ["specification_id", "inspected_at"],
    ("production_batches", "ix_production_batches_started_id"): ["started_at", "id"],
    ("production_orders", "ix_production_orders_created_id"): ["created_at", "id"],
    ("investigations", "ix_investigations_created_id"): ["created_at", "id"],
}


def _indexes(session: Session, table: str) -> dict[str, list[str]]:
    inspector = inspect(session.get_bind())
    return {
        str(index["name"]): [str(c) for c in index["column_names"]]
        for index in inspector.get_indexes(table)
    }


def test_list_ordering_indexes_exist_with_time_then_id(db_session: Session) -> None:
    by_table = {table: _indexes(db_session, table) for table, _ in EXPECTED}
    for (table, name), columns in EXPECTED.items():
        assert by_table[table].get(name) == columns, (table, name)


def test_composite_index_replaces_the_implicit_specification_fk_index(db_session: Session) -> None:
    indexes = _indexes(db_session, "inspections")
    assert "specification_id" not in indexes
    assert indexes["ix_inspections_spec_time"][0] == "specification_id"
