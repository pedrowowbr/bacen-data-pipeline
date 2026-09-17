import os
from datetime import date

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

col1, col2 = st.columns(2)
with col1:
    st.subheader("Selic Meta (% a.a.)")
    st.line_chart(df_filtrado["selic_meta"].dropna())
with col2:
    st.subheader("Dólar Comercial (venda)")
    st.line_chart(df_filtrado["dolar_comercial"].dropna())

col3, col4 = st.columns(2)
with col3:
    st.subheader("IPCA (variação mensal, %)")
    st.line_chart(df_filtrado["ipca"].dropna())
with col4:
    st.subheader("Taxa de Desemprego (%)")
    st.line_chart(df_filtrado["taxa_desemprego"].dropna())

st.caption(f"Fonte: SGS/BACEN. Última data disponível: {data_max}")
