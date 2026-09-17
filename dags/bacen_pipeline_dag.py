from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

from src.config import SERIES
from src.extract.bacen_extractor import extract_series, save_raw
from src.load.postgres_loader import ensure_schema, get_engine, load_records
from src.validate.schemas import SeriesRecord
from src.validate.validators import validate_records

# O SGS/BACEN rejeita (406) consultas com mais de ~10 anos de intervalo,
# por isso a janela é relativa a hoje, não uma data fixa.
JANELA_ANOS = 9
RAW_DATA_DIR = Path("/opt/airflow/data/raw")
DBT_PROJECT_DIR = "/opt/airflow/dbt/bacen_dw"
DBT_FLAGS = f"--project-dir {DBT_PROJECT_DIR} --profiles-dir {DBT_PROJECT_DIR}"


@dag(
    dag_id="bacen_pipeline",
    description="Extrai, valida e carrega series economicas do BACEN/SGS",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["bacen", "economia"],
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=1),
    },
)
def bacen_pipeline():
    @task
    def extract_data() -> dict[str, list[dict]]:
        hoje = date.today()
        data_inicial = (hoje - timedelta(days=365 * JANELA_ANOS)).strftime("%d/%m/%Y")
        data_final = hoje.strftime("%d/%m/%Y")
        raw_por_serie = {}
        for codigo in SERIES:
            registros = extract_series(codigo, data_inicial, data_final)
            save_raw(codigo, registros, RAW_DATA_DIR)
            raw_por_serie[str(codigo)] = registros
        return raw_por_serie

    @task
    def validate_schema(raw_por_serie: dict[str, list[dict]]) -> dict[str, list[dict]]:
        return {
            codigo: [r.model_dump(mode="json") for r in validate_records(int(codigo), registros)]
            for codigo, registros in raw_por_serie.items()
        }

    @task
    def load_raw(validado_por_serie: dict[str, list[dict]]) -> None:
        engine = get_engine()
        ensure_schema(engine)
        for codigo, registros in validado_por_serie.items():
            records = [SeriesRecord.model_validate(r) for r in registros]
            inseridos = load_records(int(codigo), records, engine)
            print(f"serie {codigo}: {inseridos} linhas carregadas")

    # dbt build = seed + run + test na ordem de dependencia do grafo (staging
    # antes de marts) - se um teste falhar num model, dbt pula quem depende
    # dele em vez de construir a camada seguinte em cima de dado ruim.
    transform_data = BashOperator(
        task_id="transform_data",
        bash_command=f"dbt build {DBT_FLAGS}",
    )

    load_raw(validate_schema(extract_data())) >> transform_data


bacen_pipeline()
