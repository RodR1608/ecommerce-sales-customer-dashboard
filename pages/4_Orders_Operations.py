import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.procesamiento import cargar_ventas


st.set_page_config(
    page_title="Orders & operations | E-commerce",
    page_icon=":material/local_shipping:",
    layout="wide",
)

MORADO = "#7654C8"
ROJO = "#D6455D"
GRIS = "#98A2B3"


@st.cache_data(show_spinner="Preparando datos operativos…")
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


def porcentaje(cantidad, total):
    return cantidad / total if total else 0


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
    pais = st.selectbox(
        "País",
        paises,
        index=paises.index("USA") if "USA" in paises else 0,
        key="op_pais",
    )
    periodo = st.date_input(
        "Período",
        value=(inicio_default, fecha_maxima),
        min_value=fecha_minima,
        max_value=fecha_maxima,
        format="DD/MM/YYYY",
        key="op_periodo",
    )
    segmento = st.selectbox(
        "Segmento", ["Todos", *segmentos], key="op_segmento"
    )
    canal = st.selectbox("Canal", ["Todos", *canales], key="op_canal")
    st.caption("Esta página considera todos los estados de orden.")

inicio, fin = resolver_rango(periodo, inicio_default, fecha_maxima)
mascara = (
    (ventas["customer_country"] == pais)
    & (ventas["order_date"].dt.date >= inicio)
    & (ventas["order_date"].dt.date <= fin)
)
if segmento != "Todos":
    mascara &= ventas["customer_segment"] == segmento
if canal != "Todos":
    mascara &= ventas["sales_channel"] == canal
df = ventas.loc[mascara].copy()

total_ordenes = df["order_id"].nunique()
ordenes_estado = df.groupby("order_status")["order_id"].nunique()
completadas = ordenes_estado.get("Completed", 0)
canceladas = ordenes_estado.get("Cancelled", 0)
devueltas = ordenes_estado.get("Returned", 0)
pendientes = ordenes_estado.get("Pending", 0)

st.title("Orders & operations", icon=":material/local_shipping:")
st.caption(
    f"Estados y excepciones operativas de {pais} · "
    f"{inicio:%d/%m/%Y}–{fin:%d/%m/%Y}"
)

with st.container(horizontal=True):
    st.metric("Órdenes totales", f"{total_ordenes:,}", border=True)
    st.metric(
        "Tasa completada",
        f"{porcentaje(completadas, total_ordenes):.1%}",
        border=True,
    )
    st.metric(
        "Tasa de cancelación",
        f"{porcentaje(canceladas, total_ordenes):.1%}",
        delta_color="inverse",
        border=True,
        help="Órdenes canceladas divididas entre todas las órdenes registradas.",
    )
    st.metric(
        "Tasa de devolución",
        f"{porcentaje(devueltas, total_ordenes):.1%}",
        delta_color="inverse",
        border=True,
    )
    st.metric("Órdenes pendientes", f"{pendientes:,}", border=True)

estado_col, tendencia_col = st.columns([1, 2], gap="large", border=True)

with estado_col:
    st.subheader("Distribución por estado", icon=":material/checklist:")
    estados = ordenes_estado.rename("ordenes").reset_index()
    estados["participacion"] = estados["ordenes"] / total_ordenes if total_ordenes else 0
    estados = estados.sort_values("ordenes")
    colores = {
        "Completed": MORADO,
        "Cancelled": ROJO,
        "Returned": "#E19A3B",
        "Pending": GRIS,
    }
    fig_estados = px.bar(
        estados,
        x="ordenes",
        y="order_status",
        orientation="h",
        text=estados["participacion"].map(lambda valor: f"{valor:.1%}"),
        labels={"ordenes": "Órdenes", "order_status": "Estado"},
    )
    fig_estados.update_traces(
        marker_color=[colores.get(valor, GRIS) for valor in estados["order_status"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}<br>Órdenes: %{x:,.0f}<br>Participación: %{text}<extra></extra>",
    )
    fig_estados.update_layout(
        height=350,
        margin=dict(l=8, r=45, t=8, b=8),
        showlegend=False,
        yaxis=dict(title=None),
    )
    st.plotly_chart(
        fig_estados,
        width="stretch",
        config={"displayModeBar": False},
        alt="Distribución de órdenes por estado.",
    )

with tendencia_col:
    st.subheader("Evolución de cancelaciones", icon=":material/trending_down:")
    st.caption("Tasa mensual: órdenes canceladas sobre órdenes registradas.")
    mensual = df.assign(mes=df["order_date"].dt.to_period("M").dt.to_timestamp())
    mensual = (
        mensual.groupby("mes", as_index=False)
        .agg(
            ordenes=("order_id", "nunique"),
            canceladas=("order_status", lambda serie: (serie == "Cancelled").sum()),
        )
    )
    mensual["tasa_cancelacion"] = (
        mensual["canceladas"] / mensual["ordenes"].replace(0, pd.NA)
    ).fillna(0)

    fig_tendencia = go.Figure(
        go.Scatter(
            x=mensual["mes"],
            y=mensual["tasa_cancelacion"],
            mode="lines+markers",
            line=dict(color=ROJO, width=3),
            marker=dict(size=6),
            hovertemplate="%{x|%b %Y}<br>Cancelación: %{y:.1%}<extra></extra>",
        )
    )
    fig_tendencia.update_layout(
        height=350,
        margin=dict(l=8, r=8, t=8, b=8),
        xaxis=dict(title=None, tickformat="%b %Y", showgrid=False),
        yaxis=dict(title="Tasa de cancelación", tickformat=".1%", rangemode="tozero"),
    )
    st.plotly_chart(
        fig_tendencia,
        width="stretch",
        config={"displayModeBar": False},
        alt="Evolución mensual de la tasa de cancelación.",
    )

with st.container(border=True):
    st.subheader("Dónde se concentra la cancelación", icon=":material/search_insights:")
    dimension = st.segmented_control(
        "Desglose",
        ["Canal", "Segmento"],
        default="Canal",
        key="op_dimension",
    )
    campo = "sales_channel" if dimension == "Canal" else "customer_segment"
    desglose = (
        df.groupby(campo, as_index=False)
        .agg(
            ordenes=("order_id", "nunique"),
            canceladas=("order_status", lambda serie: (serie == "Cancelled").sum()),
        )
    )
    desglose["tasa_cancelacion"] = (
        desglose["canceladas"] / desglose["ordenes"].replace(0, pd.NA)
    ).fillna(0)
    desglose = desglose.sort_values("tasa_cancelacion")
    fig_desglose = px.bar(
        desglose,
        x="tasa_cancelacion",
        y=campo,
        orientation="h",
        labels={"tasa_cancelacion": "Tasa de cancelación", campo: dimension},
    )
    fig_desglose.update_traces(
        marker_color=ROJO,
        hovertemplate="%{y}<br>Cancelación: %{x:.1%}<extra></extra>",
    )
    fig_desglose.update_layout(
        height=330,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        xaxis=dict(tickformat=".1%"),
        yaxis=dict(title=None),
    )
    st.plotly_chart(
        fig_desglose,
        width="stretch",
        config={"displayModeBar": False},
        alt=f"Tasa de cancelación por {dimension.lower()}.",
    )

with st.expander("Definiciones y límites", icon=":material/info:"):
    st.markdown(
        """
        - **Tasa de cancelación:** órdenes `Cancelled` divididas entre todas las órdenes registradas en el período y filtros seleccionados.
        - **Tasa de devolución:** órdenes `Returned` divididas entre todas las órdenes registradas.
        - **Tasa completada:** órdenes `Completed` divididas entre todas las órdenes registradas.
        - Las tasas describen asociaciones y concentración; no demuestran las causas de una cancelación o devolución.
        - Los motivos de devolución pueden analizarse por separado porque representan un fenómeno posterior a la venta.
        """
    )
