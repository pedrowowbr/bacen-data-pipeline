from src.validate.schemas import SeriesRecord


class DuplicateDateError(Exception):
    pass


def validate_records(codigo: int, registros: list[dict]) -> list[SeriesRecord]:
    """Valida o schema de cada registro e a ausência de datas duplicadas.

    Fail-fast deliberado: um único registro malformado (SeriesRecord.
    model_validate levanta pydantic.ValidationError) ou uma data
    duplicada derruba a task inteira, sem descartar o registro ruim e
    seguir em frente. Isso bloqueia load_raw e transform_data pra
    aquela execução (via upstream_failed do Airflow) - decisão
    consciente: para uma fonte confiável como o BACEN, um schema
    inesperado é sinal de algo errado que merece parar e ser olhado,
    não ser mascarado.

    Lista vazia é um resultado válido (série sem dado no período).
    """
    validated = [SeriesRecord.model_validate(r) for r in registros]

    datas = [r.data for r in validated]
    if len(datas) != len(set(datas)):
        raise DuplicateDateError(f"serie {codigo}: datas duplicadas encontradas")

    return validated
