select
    data,
    max(case when codigo = 432 then valor end) as selic_meta,
    max(case when codigo = 433 then valor end) as ipca,
    max(case when codigo = 189 then valor end) as inpc,
    max(case when codigo = 1 then valor end) as dolar_comercial,
    max(case when codigo = 24369 then valor end) as taxa_desemprego
from {{ ref('stg_series') }}
group by data
order by data
