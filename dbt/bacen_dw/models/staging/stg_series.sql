select
    raw_series.codigo,
    raw_series.data,
    raw_series.valor,
    series.nome_serie
from {{ source('raw', 'raw_series') }} as raw_series
left join {{ ref('series') }} as series
    on raw_series.codigo = series.codigo
