import os
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Indicadores BACEN", layout="wide")

# codigo SGS de cada serie - permite auditar/conferir direto na API do BACEN
SERIES_INFO = {
    "selic_meta": {"titulo": "Selic Meta (% a.a.)", "codigo": 432, "sufixo": "% a.a.", "casas": 2},
    "dolar_comercial": {"titulo": "Dólar Comercial (venda, BRL/USD)", "codigo": 1, "sufixo": "R$", "casas": 4},
    "ipca": {"titulo": "IPCA (variação mensal, %)", "codigo": 433, "sufixo": "%", "casas": 2},
    "taxa_desemprego": {"titulo": "Taxa de Desemprego (%)", "codigo": 24369, "sufixo": "%", "casas": 1},
}


@st.cache_resource
def get_engine():
    return create_engine(os.environ["BACEN_DB_URI"])


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    return pd.read_sql(
        "select * from marts.mart_series_wide order by data",
        get_engine(),
        parse_dates=["data"],
    )


df = load_data()

st.title("Indicadores Econômicos - BACEN")

data_min, data_max = df["data"].min().date(), df["data"].max().date()
inicio_padrao = max(data_min, date(2020, 1, 1))

col_inicio, col_fim = st.columns(2)
with col_inicio:
    data_inicial = st.date_input(
        "Data inicial", value=inicio_padrao, min_value=data_min, max_value=data_max
    )
with col_fim:
    data_final = st.date_input(
        "Data final", value=data_max, min_value=data_min, max_value=data_max
    )

df_filtrado = df[
    (df["data"].dt.date >= data_inicial) & (df["data"].dt.date <= data_final)
].set_index("data")


def grafico(serie: pd.Series, chave: str) -> None:
    """Cada série tem sua própria frequência de publicação (diária vs.
    mensal, com atraso do próprio BACEN) - por isso a data de referência
    é por gráfico, não uma data única no rodapé, que induziria a achar
    que todas as séries estão igualmente em dia."""
    info = SERIES_INFO[chave]
    dados = serie.dropna()
    st.subheader(info["titulo"])
    if dados.empty:
        st.line_chart(dados)
        return

    st.metric(
        info["titulo"].split(" (")[0],
        f"{dados.iloc[-1]:.{info['casas']}f} {info['sufixo']}",
    )

    # Domínio manual quebrou a renderização (linha vira um traço vertical
    # colapsado) mesmo com spec JSON correto - bug real do Altair/Vega
    # nesse stack, não consegui depurar sem acesso a navegador. Domínio
    # automático (nice=False, sem forçar range) é o que funciona de fato.
    pontos = dados.reset_index()
    pontos.columns = ["data", "valor"]
    chart = (
        alt.Chart(pontos)
        .mark_line()
        .encode(
            x=alt.X("data:T", title=None, scale=alt.Scale(nice=False)),
            y=alt.Y("valor:Q", title=None),
        )
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption(f"Última atualização: {dados.index.max().date()} · série SGS {info['codigo']}")


col1, col2 = st.columns(2)
with col1:
    grafico(df_filtrado["selic_meta"], "selic_meta")
with col2:
    grafico(df_filtrado["dolar_comercial"], "dolar_comercial")

col3, col4 = st.columns(2)
with col3:
    grafico(df_filtrado["ipca"], "ipca")
with col4:
    grafico(df_filtrado["taxa_desemprego"], "taxa_desemprego")

st.caption(
    "Fonte: SGS/BACEN. Selic e dólar são diários; IPCA e desemprego têm "
    "publicação mensal com atraso natural do próprio BACEN de ~1-2 meses "
    "- por isso cada gráfico mostra sua própria última data, não uma data "
    "única."
)
