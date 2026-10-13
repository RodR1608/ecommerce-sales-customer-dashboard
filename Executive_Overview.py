
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from pathlib import Path
from src.procesamiento import (
    cargar_ventas,
    calcular_kpis,
    calcular_periodo_anterior,
    calcular_variacion,
    filtrar_ventas,
)

# ==========================================
# CONFIGURACIÓN
# ==========================================

st.set_page_config(
    page_title="Executive overview | E-commerce",
    page_icon=":material/monitoring:",
    layout="wide"
)

MORADO = "#7654C8"
MORADO_CLARO = "#A68BDF"
GRIS_COMPARACION = "#98A2B3"

DATA_DIR = Path(__file__).resolve().parent / "data"


@st.cache_data(show_spinner="Preparando datos comerciales…")
def obtener_datos():
    ventas = cargar_ventas()

    detalle = pd.read_csv(DATA_DIR / "order_items.csv")
    productos = pd.read_csv(DATA_DIR / "product_catalog.csv")

    return ventas, detalle, productos


ventas, detalle, productos = obtener_datos()


def resolver_rango(valor, fecha_inicio, fecha_fin):
    """Normaliza el estado transitorio del selector de fechas."""
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


def formato_ventas(valor, moneda):
    if abs(valor) >= 1_000_000:
        return f"{moneda} {valor / 1_000_000:,.2f} M"
    if abs(valor) >= 1_000:
        return f"{moneda} {valor / 1_000:,.1f} K"
    return f"{moneda} {valor:,.0f}"


def delta_periodo(actual, anterior):
    variacion = calcular_variacion(actual, anterior)
    if variacion is None:
        return None
    if abs(variacion) < 0.05:
        return 0
    return f"{variacion:+.1f}%"


def preparar_serie_comparativa(df, inicio_real, inicio_eje, dias_bloque):
    if df.empty:
        return pd.DataFrame(columns=["fecha_eje", "fecha_real", "net_sales"])

    serie = df[["order_date", "net_sales"]].copy()
    serie["posicion"] = (
        serie["order_date"].dt.normalize() - pd.Timestamp(inicio_real)
    ).dt.days // dias_bloque
    serie = serie.groupby("posicion", as_index=False)["net_sales"].sum()
    serie["fecha_eje"] = (
        pd.Timestamp(inicio_eje)
        + pd.to_timedelta(serie["posicion"] * dias_bloque, unit="D")
    )
    serie["fecha_real"] = (
        pd.Timestamp(inicio_real)
        + pd.to_timedelta(serie["posicion"] * dias_bloque, unit="D")
    )
    return serie

# ==========================================
# FILTROS Y PERÍODOS COMPARABLES
# ==========================================

paises = sorted(ventas["customer_country"].dropna().unique())
segmentos = sorted(ventas["customer_segment"].dropna().unique())
canales = sorted(ventas["sales_channel"].dropna().unique())

min_fecha = ventas["order_date"].min().date()
max_fecha = ventas["order_date"].max().date()
inicio_default = max(
    min_fecha,
    (pd.Timestamp(max_fecha) - pd.DateOffset(months=12) + pd.Timedelta(days=1)).date(),
)

with st.sidebar:
    st.header("Filtros", icon=":material/filter_alt:")
    st.caption("Los filtros se aplican a toda la página.")
    pais = st.selectbox(
        "País",
        paises,
        index=paises.index("USA") if "USA" in paises else 0,
        key="pais",
    )
    periodo = st.date_input(
        "Período",
        value=(inicio_default, max_fecha),
        min_value=min_fecha,
        max_value=max_fecha,
        format="DD/MM/YYYY",
        key="periodo",
    )
    segmento = st.selectbox(
        "Segmento", ["Todos", *segmentos], key="segmento"
    )
    canal = st.selectbox("Canal", ["Todos", *canales], key="canal")
    st.caption("Estado fijo: Completed")

inicio, fin = resolver_rango(periodo, inicio_default, max_fecha)
inicio_anterior, fin_anterior = calcular_periodo_anterior(inicio, fin)

monedas_pais = ventas.loc[
    ventas["customer_country"] == pais, "currency"
].dropna().unique()
moneda = monedas_pais[0] if len(monedas_pais) == 1 else "Moneda local"

df = filtrar_ventas(
    ventas,
    pais=pais,
    fecha_inicio=inicio,
    fecha_fin=fin,
    segmento=segmento,
    canal=canal,
)

comparacion_disponible = inicio_anterior >= min_fecha
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

kpis = calcular_kpis(df)
kpis_anteriores = calcular_kpis(df_anterior)

# ==========================================
# ENCABEZADO
# ==========================================

st.title("Executive overview", icon=":material/monitoring:")
st.caption(
    f"Desempeño comercial de {pais} · {inicio:%d/%m/%Y}–{fin:%d/%m/%Y} · "
    f"{moneda} · órdenes completadas"
)

# ==========================================
# FILA 1: KPI
# ==========================================

st.subheader("Pulso del negocio")

with st.container(horizontal=True):
    st.metric(
        "Ventas netas",
        formato_ventas(kpis["ventas_netas"], moneda),
        delta_periodo(kpis["ventas_netas"], kpis_anteriores["ventas_netas"]),
        delta_description="vs. período anterior",
        border=True,
        help="Ventas netas de órdenes completadas.",
    )
    st.metric(
        "Ventas brutas",
        formato_ventas(kpis["ventas_brutas"], moneda),
        delta_periodo(kpis["ventas_brutas"], kpis_anteriores["ventas_brutas"]),
        delta_description="vs. período anterior",
        border=True,
        help="Ventas antes de descuentos, impuestos y envío.",
    )
    st.metric(
        "Órdenes",
        f"{kpis['ordenes']:,}",
        delta_periodo(kpis["ordenes"], kpis_anteriores["ordenes"]),
        delta_description="vs. período anterior",
        border=True,
        help="Cantidad de órdenes únicas completadas.",
    )
    st.metric(
        "Unidades",
        f"{kpis['unidades']:,.0f}",
        delta_periodo(kpis["unidades"], kpis_anteriores["unidades"]),
        delta_description="vs. período anterior",
        border=True,
        help="Suma de unidades en las órdenes completadas.",
    )
    st.metric(
        "Ticket promedio",
        formato_ventas(kpis["ticket_promedio"], moneda),
        delta_periodo(
            kpis["ticket_promedio"], kpis_anteriores["ticket_promedio"]
        ),
        delta_description="vs. período anterior",
        border=True,
        help="Ventas netas divididas entre órdenes completadas.",
    )

if comparacion_disponible:
    st.caption(
        f"Comparación homogénea: {inicio_anterior:%d/%m/%Y}–"
        f"{fin_anterior:%d/%m/%Y}, con los mismos filtros."
    )
else:
    st.caption(
        "Variación no disponible: la base no cubre un período anterior completo "
        "de igual duración."
    )

# ==========================================
# FILA 2: EVOLUCIÓN DE VENTAS
# ==========================================

with st.container(border=True):
    st.subheader("Evolución de ventas netas", icon=":material/show_chart:")
    st.caption(
        "¿El desempeño mejora frente al período comparable? El período anterior "
        "se alinea por posición temporal para una lectura equivalente."
    )

    if not df.empty:
        dias_periodo = (pd.Timestamp(fin) - pd.Timestamp(inicio)).days + 1
        if dias_periodo <= 62:
            dias_bloque, granularidad = 1, "día"
        elif dias_periodo <= 550:
            dias_bloque, granularidad = 7, "semana"
        else:
            dias_bloque, granularidad = 30, "bloque de 30 días"

        serie_actual = preparar_serie_comparativa(
            df, inicio, inicio, dias_bloque
        )
        serie_anterior = preparar_serie_comparativa(
            df_anterior, inicio_anterior, inicio, dias_bloque
        )

        fig_evolucion = go.Figure()
        for serie, nombre, color, guion in (
            (serie_actual, "Período actual", MORADO, "solid"),
            (serie_anterior, "Período anterior", GRIS_COMPARACION, "dash"),
        ):
            fig_evolucion.add_trace(
                go.Scatter(
                    x=serie["fecha_eje"],
                    y=serie["net_sales"],
                    customdata=serie[["fecha_real"]],
                    mode="lines",
                    name=nombre,
                    line=dict(color=color, width=3, dash=guion),
                    hovertemplate=(
                        f"{nombre}<br>"
                        "Fecha de origen: %{customdata[0]|%d %b %Y}<br>"
                        f"Ventas netas: {moneda} %{{y:,.0f}}<extra></extra>"
                    ),
                )
            )

        fig_evolucion.update_layout(
            height=390,
            margin=dict(l=8, r=8, t=16, b=8),
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0
            ),
            xaxis=dict(title=None, tickformat="%b %Y", showgrid=False),
            yaxis=dict(title=f"Ventas netas ({moneda})", rangemode="tozero"),
        )

        st.plotly_chart(
            fig_evolucion,
            width="stretch",
            config={"displayModeBar": False},
            alt="Comparación de ventas netas del período actual y el anterior.",
        )
        st.caption(f"Granularidad automática: {granularidad}.")
    else:
        st.warning("No existen ventas para los filtros seleccionados.")

# ==========================================
# FILA 3: CATEGORÍAS Y CANALES
# ==========================================

st.subheader("Principales impulsores")
st.caption(
    "Explore una dimensión a la vez para mantener el foco de la vista ejecutiva."
)
izquierda, derecha = st.tabs(
    [":material/category: Categorías", ":material/storefront: Canales"]
)

with izquierda:

    st.subheader("Categorías que impulsan ventas", icon=":material/category:")
    st.caption("¿Dónde se concentra el ingreso neto del período?")

    # Relacionar detalle con catálogo
    detalle_categoria = detalle.merge(
        productos[["product_id", "product_category"]],
        on="product_id",
        how="left",
        validate="many_to_one"
    )

    # Conservar órdenes filtradas
    detalle_categoria = detalle_categoria[
        detalle_categoria["order_id"].isin(df["order_id"])
    ].copy()

    # Distribuir ventas de cabecera proporcionalmente
    # al net_sales de cada línea del detalle.
    totales_detalle = (
        detalle_categoria.groupby("order_id")["net_sales"]
        .transform("sum")
    )

    cabeceras = df.set_index("order_id")["net_sales"]

    detalle_categoria["venta_cabecera"] = (
        detalle_categoria["order_id"].map(cabeceras)
    )

    detalle_categoria["ventas_asignadas"] = 0.0

    validos = totales_detalle > 0

    detalle_categoria.loc[validos, "ventas_asignadas"] = (
        detalle_categoria.loc[validos, "net_sales"]
        / totales_detalle.loc[validos]
        * detalle_categoria.loc[validos, "venta_cabecera"]
    )

    categorias = (
        detalle_categoria.groupby(
            "product_category", dropna=False
        )["ventas_asignadas"]
        .sum()
        .reset_index()
        .sort_values("ventas_asignadas", ascending=False)
    )

    categorias["product_category"] = (
        categorias["product_category"].fillna("Sin categoría")
    )

    categorias["ventas_k"] = (
        categorias["ventas_asignadas"] / 1000
    )

    fig_categoria = px.bar(
        categorias,
        x="ventas_k",
        y="product_category",
        orientation="h",
        labels={
            "ventas_k": f"Ventas (miles de {moneda})",
            "product_category": "Categoría"
        }
    )

    fig_categoria.update_traces(
        marker_color=MORADO,
        hovertemplate=(
            "%{y}<br>Ventas: %{x:,.0f} K<extra></extra>"
        )
    )

    fig_categoria.update_layout(
        height=360,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=10, t=10, b=10)
    )

    st.plotly_chart(
        fig_categoria,
        width="stretch",
        config={"displayModeBar": False},
        alt="Ranking de ventas netas asignadas por categoría."
    )

with derecha:

    st.subheader("Desempeño por canal", icon=":material/storefront:")
    st.caption("¿Qué canal genera mayor venta y participación?")

    canales = (
        df.groupby("sales_channel", as_index=False)["net_sales"]
        .sum()
        .sort_values("net_sales", ascending=False)
    )

    canales["ventas_k"] = canales["net_sales"] / 1000
    total_canales = canales["net_sales"].sum()
    canales["participacion"] = (
        canales["net_sales"] / total_canales if total_canales else 0
    )
    canales["etiqueta"] = canales["participacion"].map(
        lambda valor: f"{valor:.1%}"
    )

    fig_canales = px.bar(
        canales,
        x="ventas_k",
        y="sales_channel",
        orientation="h",
        text="etiqueta",
        labels={
            "ventas_k": f"Ventas (miles de {moneda})",
            "sales_channel": "Canal"
        }
    )

    fig_canales.update_traces(
        marker_color=MORADO_CLARO,
        textposition="outside",
        cliponaxis=False,
        hovertemplate=(
            "%{y}<br>Ventas: %{x:,.0f} K"
            "<br>Participación: %{text}<extra></extra>"
        )
    )

    fig_canales.update_layout(
        height=360,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=45, t=10, b=10)
    )

    st.plotly_chart(
        fig_canales,
        width="stretch",
        config={"displayModeBar": False},
        alt="Ventas netas y participación por canal."
    )

# ==========================================
# NOTAS METODOLÓGICAS
# ==========================================

with st.expander("Metodología y alcance", icon=":material/info:"):
    st.markdown(
        """
        - **Estado:** todos los indicadores y gráficos usan únicamente órdenes `Completed`.
        - **Ventas brutas:** valor registrado en `gross_sales`, antes de descuentos, impuestos y envío.
        - **Ventas netas:** `gross_sales - discount_amount + tax_amount + shipping_cost`, según la fórmula validada en la fuente.
        - **Ticket promedio:** ventas netas divididas entre órdenes únicas completadas.
        - **Moneda:** cada país se presenta en su moneda registrada; no se convierten ni se suman monedas distintas.
        - **Fechas:** la variación compara contra el intervalo inmediatamente anterior, con exactamente la misma duración y los mismos filtros.
        - **Categorías:** el valor de cabecera se asigna proporcionalmente según el `net_sales` de cada línea de `order_items`. Es una aproximación analítica necesaria por las diferencias detectadas entre cabecera y detalle.
        - **Margen:** se mantiene fuera de la vista hasta validar la comparabilidad de `product_cost` con ventas netas.
        - **Cero o sin base:** cuando no existe un período anterior completo o su base es cero, la variación se omite en lugar de inferir un porcentaje.
        """
    )
