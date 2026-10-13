import pandas as pd
import plotly.express as px
import streamlit as st

from src.procesamiento import (
    calcular_periodo_anterior,
    calcular_variacion,
    cargar_ventas,
    filtrar_ventas,
)


st.set_page_config(
    page_title="Customer analytics | E-commerce",
    page_icon=":material/groups:",
    layout="wide",
)

MORADO = "#7654C8"
MORADO_CLARO = "#A68BDF"


@st.cache_data(show_spinner="Preparando datos de clientes…")
def obtener_ventas():
    return cargar_ventas()


def resolver_rango(valor, fecha_inicio, fecha_fin):
    if isinstance(valor, (tuple, list)):
        if len(valor) == 2:
            inicio, fin = valor
        elif len(valor) == 1:
            inicio = fin = valor[0]
        else:
            inicio, fin = fecha_inicio, fecha_fin
    else:
        inicio = fin = valor
    return (inicio, fin) if inicio <= fin else (fin, inicio)


def variacion_periodo(actual, anterior):
    variacion = calcular_variacion(actual, anterior)
    if variacion is None:
        return None
    if abs(variacion) < 0.05:
        return 0
    return f"{variacion:+.1f}%"


def resumen_clientes(df):
    clientes = df["customer_id"].nunique()
    ordenes = df["order_id"].nunique()
    ventas = df["net_sales"].sum()
    return {
        "clientes": clientes,
        "ordenes": ordenes,
        "ventas": ventas,
        "frecuencia": ordenes / clientes if clientes else 0,
        "ticket": ventas / ordenes if ordenes else 0,
        "ventas_cliente": ventas / clientes if clientes else 0,
    }


def formato_moneda(valor, moneda):
    if abs(valor) >= 1_000_000:
        return f"{moneda} {valor / 1_000_000:,.2f} M"
    if abs(valor) >= 1_000:
        return f"{moneda} {valor / 1_000:,.1f} K"
    return f"{moneda} {valor:,.0f}"


ventas = obtener_ventas()
fecha_minima = ventas["order_date"].min().date()
fecha_maxima = ventas["order_date"].max().date()
inicio_default = max(
    fecha_minima,
    (pd.Timestamp(fecha_maxima) - pd.DateOffset(months=12) + pd.Timedelta(days=1)).date(),
)

paises = sorted(ventas["customer_country"].dropna().unique())
segmentos = sorted(ventas["customer_segment"].dropna().unique())
canales = sorted(ventas["sales_channel"].dropna().unique())

with st.sidebar:
    st.header("Filtros", icon=":material/filter_alt:")
    st.caption("Los filtros se aplican a toda la página.")
    pais = st.selectbox(
        "País",
        paises,
        index=paises.index("USA") if "USA" in paises else 0,
        key="ca_pais",
    )
    periodo = st.date_input(
        "Período",
        value=(inicio_default, fecha_maxima),
        min_value=fecha_minima,
        max_value=fecha_maxima,
        format="DD/MM/YYYY",
        key="ca_periodo",
    )
    segmento = st.selectbox(
        "Segmento", ["Todos", *segmentos], key="ca_segmento"
    )
    canal = st.selectbox("Canal", ["Todos", *canales], key="ca_canal")
    st.caption("Estado fijo: Completed")

inicio, fin = resolver_rango(periodo, inicio_default, fecha_maxima)
inicio_anterior, fin_anterior = calcular_periodo_anterior(inicio, fin)
comparacion_disponible = inicio_anterior >= fecha_minima

monedas = ventas.loc[
    ventas["customer_country"] == pais, "currency"
].dropna().unique()
moneda = monedas[0] if len(monedas) == 1 else "Moneda local"

df = filtrar_ventas(
    ventas,
    pais=pais,
    fecha_inicio=inicio,
    fecha_fin=fin,
    segmento=segmento,
    canal=canal,
)
df_anterior = (
    filtrar_ventas(
        ventas,
        pais=pais,
        fecha_inicio=inicio_anterior,
        fecha_fin=fin_anterior,
        segmento=segmento,
        canal=canal,
    )
    if comparacion_disponible
    else ventas.iloc[0:0].copy()
)

actual = resumen_clientes(df)
anterior = resumen_clientes(df_anterior)

st.title("Customer analytics", icon=":material/groups:")
st.caption(
    f"Valor y comportamiento de clientes de {pais} · "
    f"{inicio:%d/%m/%Y}–{fin:%d/%m/%Y} · {moneda} · órdenes completadas"
)

st.subheader("Indicadores de clientes")
with st.container(horizontal=True):
    st.metric(
        "Clientes únicos",
        f"{actual['clientes']:,}",
        variacion_periodo(actual["clientes"], anterior["clientes"]),
        delta_description="vs. período anterior",
        border=True,
    )
    st.metric(
        "Órdenes por cliente",
        f"{actual['frecuencia']:.2f}",
        variacion_periodo(actual["frecuencia"], anterior["frecuencia"]),
        delta_description="vs. período anterior",
        border=True,
    )
    st.metric(
        "Ticket promedio",
        formato_moneda(actual["ticket"], moneda),
        variacion_periodo(actual["ticket"], anterior["ticket"]),
        delta_description="vs. período anterior",
        border=True,
    )
    st.metric(
        "Ventas por cliente",
        formato_moneda(actual["ventas_cliente"], moneda),
        variacion_periodo(
            actual["ventas_cliente"], anterior["ventas_cliente"]
        ),
        delta_description="vs. período anterior",
        border=True,
    )

if not comparacion_disponible:
    st.caption(
        "Variación no disponible: no existe un período anterior completo "
        "de igual duración."
    )

with st.container(border=True):
    st.subheader("Desempeño por segmento", icon=":material/leaderboard:")
    st.caption("Compare tamaño, actividad y valor comercial entre segmentos.")
    metrica = st.segmented_control(
        "Métrica",
        ["Ventas netas", "Clientes", "Órdenes", "Ticket promedio", "Frecuencia"],
        default="Ventas netas",
        key="ca_metrica_segmento",
    )

    segmentos_df = (
        df.groupby("customer_segment", as_index=False)
        .agg(
            ventas_netas=("net_sales", "sum"),
            clientes=("customer_id", "nunique"),
            ordenes=("order_id", "nunique"),
        )
    )
    segmentos_df["ticket_promedio"] = (
        segmentos_df["ventas_netas"] / segmentos_df["ordenes"].replace(0, pd.NA)
    ).fillna(0)
    segmentos_df["frecuencia"] = (
        segmentos_df["ordenes"] / segmentos_df["clientes"].replace(0, pd.NA)
    ).fillna(0)

    columnas_metricas = {
        "Ventas netas": "ventas_netas",
        "Clientes": "clientes",
        "Órdenes": "ordenes",
        "Ticket promedio": "ticket_promedio",
        "Frecuencia": "frecuencia",
    }
    columna = columnas_metricas[metrica]
    segmentos_ordenados = segmentos_df.sort_values(columna)

    fig_segmentos = px.bar(
        segmentos_ordenados,
        x=columna,
        y="customer_segment",
        orientation="h",
        labels={columna: metrica, "customer_segment": "Segmento"},
    )
    fig_segmentos.update_traces(
        marker_color=MORADO,
        hovertemplate=f"%{{y}}<br>{metrica}: %{{x:,.2f}}<extra></extra>",
    )
    fig_segmentos.update_layout(
        height=340,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        yaxis=dict(title=None),
    )
    st.plotly_chart(
        fig_segmentos,
        width="stretch",
        config={"displayModeBar": False},
        alt=f"Comparación de {metrica.lower()} por segmento de clientes.",
    )

tipo_col, perfil_col = st.columns(2, gap="large", border=True)

with tipo_col:
    st.subheader("Tipo de cliente", icon=":material/person_check:")
    st.caption("Participación de ventas entre clientes nuevos y recurrentes.")
    tipos = (
        df.groupby("customer_type", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales")
    )
    total_tipos = tipos["net_sales"].sum()
    tipos["participacion"] = tipos["net_sales"] / total_tipos if total_tipos else 0
    tipos["etiqueta"] = tipos["participacion"].map(lambda valor: f"{valor:.1%}")
    fig_tipos = px.bar(
        tipos,
        x="net_sales",
        y="customer_type",
        orientation="h",
        text="etiqueta",
        labels={"net_sales": f"Ventas netas ({moneda})", "customer_type": "Tipo"},
    )
    fig_tipos.update_traces(
        marker_color=MORADO_CLARO,
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            f"%{{y}}<br>{moneda} %{{x:,.0f}}"
            "<br>Participación: %{text}<extra></extra>"
        ),
    )
    fig_tipos.update_layout(
        height=330,
        margin=dict(l=8, r=45, t=8, b=8),
        showlegend=False,
        yaxis=dict(title=None),
    )
    st.plotly_chart(
        fig_tipos,
        width="stretch",
        config={"displayModeBar": False},
        alt="Participación de ventas netas por tipo de cliente.",
    )

with perfil_col:
    st.subheader("Perfil demográfico", icon=":material/demography:")
    st.caption("Lectura secundaria de la base de clientes activos.")
    perfil = st.segmented_control(
        "Desglose",
        ["Rango de edad", "Género"],
        default="Rango de edad",
        key="ca_perfil",
    )

    if perfil == "Rango de edad":
        perfil_df = df.copy()
        perfil_df["grupo"] = pd.cut(
            perfil_df["customer_age"],
            bins=[0, 24, 34, 44, 54, 64, float("inf")],
            labels=["18–24", "25–34", "35–44", "45–54", "55–64", "65+"],
        )
        perfil_df = (
            perfil_df.groupby("grupo", observed=True, as_index=False)["customer_id"]
            .nunique()
            .rename(columns={"customer_id": "clientes"})
        )
        titulo_eje = "Rango de edad"
    else:
        perfil_df = (
            df.groupby("gender", as_index=False)["customer_id"]
            .nunique()
            .rename(columns={"gender": "grupo", "customer_id": "clientes"})
        )
        titulo_eje = "Género"

    fig_perfil = px.bar(
        perfil_df,
        x="grupo",
        y="clientes",
        labels={"grupo": titulo_eje, "clientes": "Clientes únicos"},
    )
    fig_perfil.update_traces(
        marker_color=MORADO,
        hovertemplate="%{x}<br>Clientes: %{y:,.0f}<extra></extra>",
    )
    fig_perfil.update_layout(
        height=330,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
    )
    st.plotly_chart(
        fig_perfil,
        width="stretch",
        config={"displayModeBar": False},
        alt=f"Clientes únicos por {titulo_eje.lower()}.",
    )

with st.expander("Definiciones y alcance", icon=":material/info:"):
    st.markdown(
        """
        - **Clientes únicos:** conteo distinto de `customer_id` con al menos una orden completada en el período.
        - **Órdenes por cliente:** órdenes únicas completadas divididas entre clientes únicos del período. Es frecuencia observada en el rango seleccionado, no frecuencia histórica total.
        - **Ticket promedio:** ventas netas divididas entre órdenes únicas completadas.
        - **Ventas por cliente:** ventas netas divididas entre clientes únicos activos.
        - **Relación de fuentes:** todos los `customer_id` presentes en ventas fueron encontrados en `customer_master`; no se muestran nombres de clientes.
        - **Moneda:** cada país se analiza en su moneda registrada, sin conversiones entre monedas.
        """
    )
