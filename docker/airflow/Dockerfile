FROM apache/airflow:2.9.3-python3.11

COPY requirements.txt /requirements.txt

# Usa o constraints file oficial do Airflow para essa versão/Python, para que
# nossas libs extras (requests, pandas, dbt...) não sobrescrevam versões de
# dependências compartilhadas (ex.: SQLAlchemy) das quais o próprio Airflow
# depende internamente.
RUN pip install --no-cache-dir -r /requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.3/constraints-3.11.txt"
