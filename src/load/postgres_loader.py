import os
from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, Float, Integer, MetaData, Table, create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from src.validate.schemas import SeriesRecord

metadata = MetaData(schema="raw")

raw_series = Table(
    "raw_series",
    metadata,
    Column("codigo", Integer, primary_key=True),
    Column("data", Date, primary_key=True),
    Column("valor", Float, nullable=False),
    Column("extracted_at", DateTime(timezone=True), nullable=False),
)


def get_engine() -> Engine:
    return create_engine(os.environ["BACEN_DB_URI"])


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
    metadata.create_all(engine)


def load_records(codigo: int, registros: list[SeriesRecord], engine: Engine) -> int:
    """Upsert por (codigo, data): reprocessar o mesmo dia não duplica linha."""
    if not registros:
        return 0

    extracted_at = datetime.now(timezone.utc)
    rows = [
        {"codigo": codigo, "data": r.data, "valor": r.valor, "extracted_at": extracted_at}
        for r in registros
    ]

    stmt = pg_insert(raw_series).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["codigo", "data"],
        set_={"valor": stmt.excluded.valor, "extracted_at": stmt.excluded.extracted_at},
    )

    with engine.begin() as conn:
        conn.execute(stmt)

    return len(rows)
