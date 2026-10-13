from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.procesamiento import cargar_ventas, filtrar_ventas


st.set_page_config(
    page_title="Product & sales | E-commerce",
    page_icon=":material/inventory_2:",
    layout="wide",
)

MORADO = "#7654C8"
MORADO_CLARO = "#A68BDF"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data(show_spinner="Preparando datos de productos…")
def obtener_datos():
    ventas = cargar_ventas()
    detalle = pd.read_csv(DATA_DIR / "order_items.csv", low_memory=False)
    productos = pd.read_csv(DATA_DIR / "product_catalog.csv", low_memory=False)
    detalle = detalle.merge(
        productos[
            [
                "product_id",
                "product_name",
                "product_category",
                "product_subcategory",
                "brand",
            ]
        ],
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    return ventas, detalle


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


def asignar_ventas_cabecera(cabeceras, detalle):
    resultado = detalle[detalle["order_id"].isin(cabeceras["order_id"])].copy()
    if resultado.empty:
        resultado["ventas_asignadas"] = pd.Series(dtype="float64")
        return resultado

    total_lineas = resultado.groupby("order_id")["net_sales"].transform("sum")
    neto_cabecera = cabeceras.set_index("order_id")["net_sales"]
    resultado["neto_cabecera"] = resultado["order_id"].map(neto_cabecera)
    resultado["ventas_asignadas"] = 0.0
    validos = total_lineas > 0
    resultado.loc[validos, "ventas_asignadas"] = (
        resultado.loc[validos, "net_sales"]
        / total_lineas.loc[validos]
        * resultado.loc[validos, "neto_cabecera"]
    )
    return resultado


def formato_moneda(valor, moneda):
    if abs(valor) >= 1_000_000:
        return f"{moneda} {valor / 1_000_000:,.2f} M"
    if abs(valor) >= 1_000:
        return f"{moneda} {valor / 1_000:,.1f} K"
    return f"{moneda} {valor:,.0f}"


ventas, detalle_productos = obtener_datos()
fecha_minima = ventas["order_date"].min().date()
fecha_maxima = ventas["order_date"].max().date()
inicio_default = max(
    fecha_minima,
    (pd.Timestamp(fecha_maxima) - pd.DateOffset(months=12) + pd.Timedelta(days=1)).date(),
)

paises = sorted(ventas["customer_country"].dropna().unique())
segmentos = sorted(ventas["customer_segment"].dropna().unique())
canales = sorted(ventas["sales_channel"].dropna().unique())
categorias = sorted(detalle_productos["product_category"].dropna().unique())

with st.sidebar:
    st.header("Filtros", icon=":material/filter_alt:")
    pais = st.selectbox(
        "País",
        paises,
        index=paises.index("USA") if "USA" in paises else 0,
        key="ps_pais",
    )
    periodo = st.date_input(
        "Período",
        value=(inicio_default, fecha_maxima),
        min_value=fecha_minima,
        max_value=fecha_maxima,
        format="DD/MM/YYYY",
        key="ps_periodo",
    )
    segmento = st.selectbox(
        "Segmento", ["Todos", *segmentos], key="ps_segmento"
    )
    canal = st.selectbox("Canal", ["Todos", *canales], key="ps_canal")
    categoria = st.selectbox(
        "Categoría", ["Todas", *categorias], key="ps_categoria"
    )
    st.caption("Estado fijo: Completed")

inicio, fin = resolver_rango(periodo, inicio_default, fecha_maxima)
monedas = ventas.loc[
    ventas["customer_country"] == pais, "currency"
].dropna().unique()
moneda = monedas[0] if len(monedas) == 1 else "Moneda local"

cabeceras = filtrar_ventas(
    ventas,
    pais=pais,
    fecha_inicio=inicio,
    fecha_fin=fin,
    segmento=segmento,
    canal=canal,
)
detalle = asignar_ventas_cabecera(cabeceras, detalle_productos)
if categoria != "Todas":
    detalle = detalle[detalle["product_category"] == categoria].copy()

st.title("Product & sales analytics", icon=":material/inventory_2:")
st.caption(
    f"Contribución comercial de productos de {pais} · "
    f"{inicio:%d/%m/%Y}–{fin:%d/%m/%Y} · {moneda}"
)

with st.container(horizontal=True):
    st.metric(
        "Ventas asignadas",
        formato_moneda(detalle["ventas_asignadas"].sum(), moneda),
        border=True,
        help="Ventas de cabecera distribuidas proporcionalmente entre líneas válidas.",
    )
    st.metric("Unidades de detalle", f"{detalle['quantity'].sum():,.0f}", border=True)
    st.metric("Productos vendidos", f"{detalle['product_id'].nunique():,}", border=True)
    st.metric(
        "Categorías activas",
        f"{detalle['product_category'].nunique():,}",
        border=True,
    )

with st.container(border=True):
    st.subheader("Concentración comercial", icon=":material/leaderboard:")
    nivel = st.segmented_control(
        "Nivel de análisis",
        ["Categoría", "Subcategoría", "Marca"],
        default="Categoría",
        key="ps_nivel",
    )
    campo = {
        "Categoría": "product_category",
        "Subcategoría": "product_subcategory",
        "Marca": "brand",
    }[nivel]
    ranking = (
        detalle.groupby(campo, dropna=False, as_index=False)["ventas_asignadas"]
        .sum()
        .nlargest(12, "ventas_asignadas")
        .sort_values("ventas_asignadas")
    )
    ranking[campo] = ranking[campo].fillna("Sin clasificación")
    fig_ranking = px.bar(
        ranking,
        x="ventas_asignadas",
        y=campo,
        orientation="h",
        labels={"ventas_asignadas": f"Ventas asignadas ({moneda})", campo: nivel},
    )
    fig_ranking.update_traces(
        marker_color=MORADO,
        hovertemplate=f"%{{y}}<br>{moneda} %{{x:,.0f}}<extra></extra>",
    )
    fig_ranking.update_layout(
        height=390,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        yaxis=dict(title=None),
    )
    st.plotly_chart(
        fig_ranking,
        width="stretch",
        config={"displayModeBar": False},
        alt=f"Ranking de ventas asignadas por {nivel.lower()}.",
    )

ventas_col, unidades_col = st.columns(2, gap="large", border=True)

with ventas_col:
    st.subheader("Productos líderes", icon=":material/star:")
    top_productos = (
        detalle.groupby(["product_id", "product_name"], as_index=False)
        .agg(
            ventas_asignadas=("ventas_asignadas", "sum"),
            unidades=("quantity", "sum"),
        )
        .nlargest(10, "ventas_asignadas")
    )
    st.dataframe(
        top_productos[["product_name", "ventas_asignadas", "unidades"]],
        hide_index=True,
        width="stretch",
        column_config={
            "product_name": st.column_config.TextColumn("Producto"),
            "ventas_asignadas": st.column_config.NumberColumn(
                f"Ventas ({moneda})", format="%.0f"
            ),
            "unidades": st.column_config.NumberColumn("Unidades", format="%.0f"),
        },
        alt="Los diez productos con mayores ventas asignadas.",
    )

with unidades_col:
    st.subheader("Unidades por categoría", icon=":material/shopping_cart:")
    unidades = (
        detalle.groupby("product_category", as_index=False)["quantity"]
        .sum()
        .sort_values("quantity")
    )
    fig_unidades = px.bar(
        unidades,
        x="quantity",
        y="product_category",
        orientation="h",
        labels={"quantity": "Unidades", "product_category": "Categoría"},
    )
    fig_unidades.update_traces(marker_color=MORADO_CLARO)
    fig_unidades.update_layout(
        height=330,
        margin=dict(l=8, r=8, t=8, b=8),
        showlegend=False,
        yaxis=dict(title=None),
    )
    st.plotly_chart(
        fig_unidades,
        width="stretch",
        config={"displayModeBar": False},
        alt="Unidades vendidas por categoría según el detalle de órdenes.",
    )

with st.expander("Metodología y limitaciones", icon=":material/info:"):
    st.markdown(
        """
        - Las ventas por producto se asignan proporcionalmente desde el `net_sales` de cabecera usando el peso de cada línea de `order_items`.
        - Las unidades provienen directamente de `order_items`; por ello se identifican explícitamente como unidades de detalle.
        - La asignación es provisional por las diferencias detectadas entre cabecera y detalle.
        - El margen queda fuera hasta validar que `product_cost` sea comparable con la definición de ventas netas.
        """
    )
