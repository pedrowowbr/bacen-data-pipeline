#!/bin/bash
# Cria os bancos AIRFLOW_DB e BACEN_DB no mesmo container Postgres.
# O Postgres so aceita um POSTGRES_DB via env; este script roda no primeiro
# start (docker-entrypoint-initdb.d) e cria os demais.
set -e

for db in "$AIRFLOW_DB" "$BACEN_DB"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE "$db"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
done
