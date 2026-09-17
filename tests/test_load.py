from datetime import date

import pytest
from sqlalchemy import text

from src.load.postgres_loader import ensure_schema, get_engine, load_records, raw_series
from src.validate.schemas import SeriesRecord

TEST_CODIGO = 999999


@pytest.fixture
def engine():
    engine = get_engine()
    ensure_schema(engine)
    yield engine
    with engine.begin() as conn:
        conn.execute(raw_series.delete().where(raw_series.c.codigo == TEST_CODIGO))


def test_load_records_inserts_rows(engine):
    registros = [
        SeriesRecord(data=date(2024, 1, 1), valor=11.75),
        SeriesRecord(data=date(2024, 1, 2), valor=11.75),
    ]

    inserted = load_records(TEST_CODIGO, registros, engine)

    assert inserted == 2
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM raw.raw_series WHERE codigo = :codigo"),
            {"codigo": TEST_CODIGO},
        ).scalar_one()
    assert count == 2


def test_load_records_upserts_on_conflict(engine):
    load_records(TEST_CODIGO, [SeriesRecord(data=date(2024, 1, 1), valor=11.75)], engine)
    load_records(TEST_CODIGO, [SeriesRecord(data=date(2024, 1, 1), valor=12.00)], engine)

    with engine.connect() as conn:
        valor = conn.execute(
            text("SELECT valor FROM raw.raw_series WHERE codigo = :codigo AND data = :data"),
            {"codigo": TEST_CODIGO, "data": date(2024, 1, 1)},
        ).scalar_one()

    assert valor == 12.00


def test_load_records_empty_list_is_noop(engine):
    assert load_records(TEST_CODIGO, [], engine) == 0
