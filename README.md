# Brazilian Economic Data Pipeline

Pipeline de dados que extrai séries econômicas públicas do Banco Central do
Brasil (SGS/BACEN), valida e carrega em um data warehouse Postgres,
transforma com dbt em camadas analíticas e entrega tabelas prontas para
consumo em dashboard.

Séries acompanhadas: Meta Selic, IPCA, INPC, dólar comercial e taxa de
desemprego (PNAD contínua).

## Architecture

```
Dados públicos (API BACEN)
        |
      Python (extract + validate)
        |
      Airflow (orquestração, @daily)
        |
   PostgreSQL (raw)
        |
       dbt build (staging -> marts, com testes de qualidade)
        |
  Analytics tables
        |
     Streamlit (dashboard)
```

DAG:

```
extract_data -> validate_schema -> load_raw -> transform_data (dbt build)
```

## Technologies

- Python + Pydantic (extração e validação de schema)
- SQLAlchemy Core (carga idempotente no Postgres, upsert)
- Apache Airflow (orquestração, `LocalExecutor`)
- PostgreSQL (armazenamento raw / staging / marts)
- dbt (transformação em camadas e testes de qualidade)
- Streamlit (dashboard)
- Docker Compose (ambiente local reprodutível)

## Data Source

API SGS do Banco Central do Brasil — sem autenticação, sem rate limit
agressivo. A API rejeita (`406`) consultas com mais de ~10 anos de
intervalo entre `dataInicial` e `dataFinal`, por isso a extração usa uma
janela relativa a "hoje" (9 anos), não datas fixas.

```
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={data}&dataFinal={data}
```

| Código | Série |
|---|---|
| 432 | Meta Selic |
| 433 | IPCA (variação mensal) |
| 189 | INPC |
| 1 | Dólar comercial (venda, diária) |
| 24369 | Taxa de desemprego (PNAD contínua) |

## Pipeline

| Task | O que faz |
|---|---|
| `extract_data` | Chama a API do SGS para cada série, salva o JSON cru em `data/raw/` e retorna os registros para a próxima task |
| `validate_schema` | Valida o formato de cada registro com Pydantic (`data`, `valor`) e rejeita datas duplicadas dentro do mesmo lote |
| `load_raw` | Upsert (`INSERT ... ON CONFLICT DO UPDATE`) na tabela `raw.raw_series`, por `(codigo, data)` — reprocessar o mesmo dia não duplica nada |
| `transform_data` | `dbt build`: carrega o seed de séries, constrói `staging` e `marts`, e roda os 10 testes de qualidade na ordem de dependência do grafo |

Full refresh a cada execução (não incremental): o volume das séries é
pequeno (poucos milhares de linhas), e a carga é idempotente via upsert —
rodar de novo no mesmo dia é seguro e não compensa a complexidade extra
de rastrear o que já foi extraído.

## Data Model

Três schemas no Postgres, cada um com uma responsabilidade:

- **`raw`** — dado como veio da API, só tipado (`raw.raw_series`:
  `codigo`, `data`, `valor`, `extracted_at`). Chave primária composta
  `(codigo, data)`.
- **`staging`** (dbt, **view**) — `stg_series`: junta `raw.raw_series` com
  o seed `series.csv` para resolver `codigo -> nome_serie`.
- **`marts`** (dbt, **table**) — `mart_series_wide`: uma linha por data,
  as 5 séries lado a lado (pivô via `CASE WHEN` + `MAX` + `GROUP BY`).
  É a tabela que o dashboard consulta.

```
raw.raw_series          staging.stg_series         marts.mart_series_wide
codigo | data | valor   codigo | data | valor |    data | selic_meta | ipca | ...
                         nome_serie
```

## Data Quality

Duas camadas de validação, com propósitos diferentes:

1. **Schema (Pydantic, `validate_schema`)** — o registro individual tem o
   formato certo? Tipo, campo obrigatório, data parseável. Roda antes de
   qualquer escrita no banco. **Fail-fast deliberado**: um registro
   malformado derruba a task inteira (sem log-and-continue), bloqueando
   `load_raw` e `transform_data` para aquela execução — fonte confiável
   como o BACEN, schema inesperado é sinal de algo errado que merece
   parar, não ser mascarado.
2. **Data quality (dbt test, dentro do `dbt build`)** — o conjunto de
   dados faz sentido? 10 testes: `not_null` nas colunas de `raw`,
   `staging` e `marts`, `unique` na chave da mart, e um teste customizado
   de unicidade composta `(codigo, data)` em `staging`.

`dbt build` intercala model e teste por nó do grafo — se um teste de
`staging` falhar, a `marts` não chega a ser construída em cima do dado
ruim.

Resiliência a falha externa: `retries=2` com `retry_delay=1min` na DAG
(a API do BACEN já apresentou timeout de rede durante o desenvolvimento).

## How to Run

```bash
cp .env.example .env
docker compose up -d
```

- Airflow: `http://localhost:8080` (usuário/senha em `.env`)
- Dashboard: `http://localhost:8501`

Rodar os testes automatizados (dentro do container do Airflow, que já tem
as dependências):

```bash
docker compose exec -w /opt/airflow airflow-scheduler python -m pytest tests/ -v
```

## Airflow DAG

```
extract_data --> validate_schema --> load_raw --> transform_data
```

- Schedule: `@daily`, `catchup=False`
- `transform_data` roda `dbt build --project-dir ... --profiles-dir ...`
- TaskFlow API (`@dag`/`@task`) para as 3 primeiras tasks, `BashOperator`
  para a chamada ao dbt — os dois estilos convivem na mesma DAG

## Example Queries

IPCA acumulado nos últimos 12 meses:

```sql
select
    data,
    sum(ipca) over (order by data rows between 11 preceding and current row) as ipca_acum_12m
from marts.mart_series_wide
where ipca is not null
order by data;
```

Selic vs. dólar no último ano:

```sql
select data, selic_meta, dolar_comercial
from marts.mart_series_wide
where data >= current_date - interval '1 year'
order by data;
```

Última leitura de cada série:

```sql
select
    max(data) filter (where selic_meta is not null) as ultima_selic,
    max(data) filter (where ipca is not null) as ultimo_ipca,
    max(data) filter (where dolar_comercial is not null) as ultimo_dolar
from marts.mart_series_wide;
```

## Future Improvements

- **astronomer-cosmos**: trocar o `BashOperator` do `transform_data` por
  um `DbtTaskGroup` do Cosmos — ele lê o manifest do dbt e gera uma task
  do Airflow por model/teste automaticamente, dando visibilidade por nó
  no grafo sem abrir mão do fail-fast do `dbt build`
- `models/intermediate/`: IPCA acumulado 12 meses como model dbt (hoje é
  só a query acima, não uma tabela) e forward-fill das séries mensais
  para a mart não ficar esparsa em granularidade diária
- CI (GitHub Actions) rodando `pytest` e `dbt build` a cada push
- Dynamic task mapping no Airflow (uma task por série, em vez de um loop
  dentro de `extract_data`) para isolar falha de uma série sem derrubar
  as outras
