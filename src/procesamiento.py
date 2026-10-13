
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def cargar_ventas():
    ruta = DATA_DIR / "ecommerce_sales_customer_analytics_150k.csv"

    df = pd.read_csv(ruta, low_memory=False)
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    return df


def filtrar_ventas(
    df,
    pais="USA",
    fecha_inicio=None,
    fecha_fin=None,
    segmento="Todos",
    canal="Todos",
    estado="Completed",
):
    """Aplica filtros comerciales sin mezclar países ni monedas."""
    mascara = (
        (df["order_status"] == estado)
        & (df["customer_country"] == pais)
    )

    if fecha_inicio is not None:
        mascara &= df["order_date"].dt.date >= fecha_inicio
    if fecha_fin is not None:
        mascara &= df["order_date"].dt.date <= fecha_fin
    if segmento != "Todos":
        mascara &= df["customer_segment"] == segmento
    if canal != "Todos":
        mascara &= df["sales_channel"] == canal

    resultado = df.loc[mascara].copy()

    return resultado


def calcular_periodo_anterior(fecha_inicio, fecha_fin):
    """Devuelve el intervalo inmediatamente anterior con igual duración."""
    inicio = pd.Timestamp(fecha_inicio)
    fin = pd.Timestamp(fecha_fin)

    if inicio > fin:
        inicio, fin = fin, inicio

    duracion = fin - inicio
    fin_anterior = inicio - pd.Timedelta(days=1)
    inicio_anterior = fin_anterior - duracion

    return inicio_anterior.date(), fin_anterior.date()


def calcular_variacion(valor_actual, valor_anterior):
    """Calcula variación porcentual; sin base válida devuelve None."""
    if pd.isna(valor_anterior) or valor_anterior == 0:
        return None

    return (valor_actual / valor_anterior - 1) * 100


def calcular_kpis(df):
    ventas_netas = df["net_sales"].sum()
    ventas_brutas = df["gross_sales"].sum()
    ordenes = df["order_id"].nunique()
    unidades = df["quantity"].sum()

    ticket_promedio = (
        ventas_netas / ordenes if ordenes > 0 else 0
    )

    return {
        "ventas_netas": ventas_netas,
        "ventas_brutas": ventas_brutas,
        "ordenes": ordenes,
        "unidades": unidades,
        "ticket_promedio": ticket_promedio
    }
