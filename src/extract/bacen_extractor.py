import json
from datetime import date
from pathlib import Path

import requests

from src.config import SERIES

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"


def extract_series(codigo: int, data_inicial: str, data_final: str) -> list[dict]:
    """Busca uma série do SGS/BACEN. Datas no formato dd/mm/yyyy.

    A API retorna lista vazia (nao erro) quando nao ha dado no periodo -
    isso e um resultado valido, nao uma falha.
    """
    response = requests.get(
        BASE_URL.format(codigo=codigo),
        params={"formato": "json", "dataInicial": data_inicial, "dataFinal": data_final},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def save_raw(codigo: int, registros: list[dict], output_dir: Path) -> Path:
    """Grava os registros crus como vieram da API, sem transformação."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"serie_{codigo}_{date.today().isoformat()}.json"
    path.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def extract_all(data_inicial: str, data_final: str, output_dir: Path) -> list[Path]:
    """Extrai todas as séries de SERIES e salva cada uma como um JSON cru."""
    return [
        save_raw(codigo, extract_series(codigo, data_inicial, data_final), output_dir)
        for codigo in SERIES
    ]


if __name__ == "__main__":
    paths = extract_all("01/01/2020", date.today().strftime("%d/%m/%Y"), Path("data/raw"))
    for path in paths:
        print(f"salvo: {path}")
