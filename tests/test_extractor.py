import json
from unittest.mock import Mock, patch

from src.extract.bacen_extractor import extract_series, save_raw


@patch("src.extract.bacen_extractor.requests.get")
def test_extract_series_returns_api_payload(mock_get):
    mock_get.return_value = Mock(
        status_code=200,
        json=lambda: [{"data": "01/01/2024", "valor": "11.75"}],
    )

    registros = extract_series(432, "01/01/2024", "31/01/2024")

    assert registros == [{"data": "01/01/2024", "valor": "11.75"}]


@patch("src.extract.bacen_extractor.requests.get")
def test_extract_series_empty_period_returns_empty_list(mock_get):
    mock_get.return_value = Mock(status_code=200, json=lambda: [])

    assert extract_series(432, "01/01/1900", "02/01/1900") == []


def test_save_raw_writes_json_file(tmp_path):
    registros = [{"data": "01/01/2024", "valor": "11.75"}]

    path = save_raw(432, registros, tmp_path)

    assert path.exists()
    assert json.loads(path.read_text(encoding="utf-8")) == registros
