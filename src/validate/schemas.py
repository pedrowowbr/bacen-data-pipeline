from datetime import date, datetime

from pydantic import BaseModel, field_validator


class SeriesRecord(BaseModel):
    data: date
    valor: float

    @field_validator("data", mode="before")
    @classmethod
    def parse_data_br(cls, v: str | date) -> str | date:
        if isinstance(v, str):
            try:
                return datetime.strptime(v, "%d/%m/%Y").date()
            except ValueError:
                return v
        return v
