-- Falha se existir mais de um registro para o mesmo (codigo, data) em stg_series.
-- dbt trata "teste passou" como "a query nao retornou nenhuma linha".
select codigo, data, count(*) as ocorrencias
from {{ ref('stg_series') }}
group by codigo, data
having count(*) > 1
