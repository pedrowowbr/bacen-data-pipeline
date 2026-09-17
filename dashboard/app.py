import os
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Indicadores BACEN", layout="wide")


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


def grafico(serie: pd.Series, titulo: str) -> None:
    """Cada série tem sua própria frequência de publicação (diária vs.
    mensal, com atraso do próprio BACEN) - por isso a data de referência
    é por gráfico, não uma data única no rodapé, que induziria a achar
    que todas as séries estão igualmente em dia."""
    dados = serie.dropna()
    st.subheader(titulo)
    if dados.empty:
        st.line_chart(dados)
        return

    # st.line_chart arredonda o eixo de tempo pra um limite "bonito"
    # (ex.: estende até o ano seguinte) - nice=False usa a extensão real
    # dos dados como domínio, sem precisar informar datas manualmente
    # (informar domain à mão quebrou o eixo - ver commit anterior).
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
    st.caption(f"Última atualização: {dados.index.max().date()}")


col1, col2 = st.columns(2)
with col1:
    grafico(df_filtrado["selic_meta"], "Selic Meta (% a.a.)")
with col2:
    grafico(df_filtrado["dolar_comercial"], "Dólar Comercial (venda)")

col3, col4 = st.columns(2)
with col3:
    grafico(df_filtrado["ipca"], "IPCA (variação mensal, %)")
with col4:
    grafico(df_filtrado["taxa_desemprego"], "Taxa de Desemprego (%)")

st.caption(
    "Fonte: SGS/BACEN. Selic e dólar são diários; IPCA e desemprego têm "
    "publicação mensal com atraso natural do próprio BACEN - por isso "
    "cada gráfico mostra sua própria última data, não uma data única."
)
