from src.validate.schemas import SeriesRecord


class DuplicateDateError(Exception):
    pass


def validate_records(codigo: int, registros: list[dict]) -> list[SeriesRecord]:
    """Valida o schema de cada registro e a ausência de datas duplicadas.

    Lista vazia é um resultado válido (série sem dado no período).
    """
    validated = [SeriesRecord.model_validate(r) for r in registros]

    datas = [r.data for r in validated]
    if len(datas) != len(set(datas)):
        raise DuplicateDateError(f"serie {codigo}: datas duplicadas encontradas")

    return validated
