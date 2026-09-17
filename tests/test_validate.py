import pytest
from pydantic import ValidationError

from src.validate.validators import DuplicateDateError, validate_records


def test_validate_records_happy_path():
    registros = [
        {"data": "01/01/2024", "valor": "11.75"},
        {"data": "02/01/2024", "valor": "11.75"},
    ]

    validated = validate_records(432, registros)

    assert len(validated) == 2
    assert validated[0].valor == 11.75


def test_validate_records_rejects_non_numeric_valor():
    registros = [{"data": "01/01/2024", "valor": "N/D"}]

    with pytest.raises(ValidationError):
        validate_records(432, registros)


def test_validate_records_rejects_missing_field():
    registros = [{"data": "01/01/2024"}]

    with pytest.raises(ValidationError):
        validate_records(432, registros)


def test_validate_records_rejects_duplicate_dates():
    registros = [
        {"data": "01/01/2024", "valor": "11.75"},
        {"data": "01/01/2024", "valor": "11.75"},
    ]

    with pytest.raises(DuplicateDateError):
        validate_records(432, registros)


def test_validate_records_empty_list_is_valid():
    assert validate_records(432, []) == []
