
from pathlib import Path
import pandas as pd
import numpy as np

# =====================================================
# 1. CONFIGURACIÓN Y LECTURA DE DATOS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

archivos = {
    "clientes": "customer_master.csv",
    "ventas": "ecommerce_sales_customer_analytics_150k.csv",
    "detalle": "order_items.csv",
    "productos": "product_catalog.csv"
}

datos = {}

for nombre, archivo in archivos.items():
    df = pd.read_csv(DATA_DIR / archivo, low_memory=False)
    datos[nombre] = df

    print(f"\nArchivo: {archivo}")
    print(f"Filas: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")
    print(f"Variables: {df.columns.tolist()}")

clientes = datos["clientes"]
ventas = datos["ventas"]
detalle = datos["detalle"]
productos = datos["productos"]

print("\nValidación inicial finalizada.")

# =====================================================
# 2. ESTADOS DE ÓRDENES Y MONEDAS
# =====================================================

print("\n=== ESTADOS DE ÓRDENES ===")
print(ventas["order_status"].value_counts(dropna=False))

print("\n=== MONEDAS ===")
print(ventas["currency"].value_counts(dropna=False))

# =====================================================
# 3. CONCILIACIÓN ENTRE CABECERA Y DETALLE
# =====================================================

importes_detalle = detalle.groupby(
    "order_id", as_index=False
).agg(
    net_sales_detalle=("net_sales", "sum"),
    gross_sales_detalle=("gross_sales", "sum")
)

comparacion = ventas[
    ["order_id", "order_status", "currency",
     "net_sales", "gross_sales"]
].merge(
    importes_detalle,
    on="order_id",
    how="left",
    validate="one_to_one"
)

comparacion["dif_neta"] = (
    comparacion["net_sales"]
    - comparacion["net_sales_detalle"]
)

comparacion["dif_bruta"] = (
    comparacion["gross_sales"]
    - comparacion["gross_sales_detalle"]
)

print("\n=== CONCILIACIÓN DE VENTAS ===")

print(
    "Órdenes sin detalle:",
    comparacion["net_sales_detalle"].isna().sum()
)

for nombre, columna in [
    ("Ventas netas", "dif_neta"),
    ("Ventas brutas", "dif_bruta")
]:
    print(f"\n{nombre}")
    print(
        "Órdenes con diferencias:",
        comparacion[columna].abs().gt(0.01).sum()
    )
    print(
        "Diferencia absoluta total:",
        round(comparacion[columna].abs().sum(), 2)
    )

# =====================================================
# 4. DIFERENCIAS POR ESTADO DE ORDEN
# =====================================================

comparacion["con_diferencia"] = (
    comparacion["dif_neta"].abs() > 0.01
)

resultado_estados = comparacion.groupby(
    "order_status"
).agg(
    total_ordenes=("order_id", "count"),
    ordenes_con_diferencia=("con_diferencia", "sum"),
    diferencia_absoluta=(
        "dif_neta", lambda x: x.abs().sum()
    )
)

resultado_estados["porcentaje_diferencia"] = (
    resultado_estados["ordenes_con_diferencia"]
    / resultado_estados["total_ordenes"] * 100
)

print("\n=== DIFERENCIAS POR ESTADO DE ORDEN ===")
print(resultado_estados.round(2).to_string())

# =====================================================
# 5. DIRECCIÓN DE LAS DIFERENCIAS
# =====================================================

comparacion["tipo_diferencia"] = np.select(
    [
        comparacion["dif_neta"] > 0.01,
        comparacion["dif_neta"] < -0.01
    ],
    [
        "Cabecera mayor",
        "Detalle mayor"
    ],
    default="Coinciden"
)

print("\n=== DIRECCIÓN DE DIFERENCIAS ===")
print(comparacion["tipo_diferencia"].value_counts())

# =====================================================
# 6. DIFERENCIAS POR MONEDA
# =====================================================

resumen_moneda = comparacion.groupby(
    "currency"
).agg(
    ordenes=("order_id", "count"),
    diferencia_neta=("dif_neta", "sum"),
    diferencia_absoluta=(
        "dif_neta", lambda x: x.abs().sum()
    ),
    ordenes_diferentes=(
        "dif_neta", lambda x: x.abs().gt(0.01).sum()
    )
)

resumen_moneda["porcentaje"] = (
    resumen_moneda["ordenes_diferentes"]
    / resumen_moneda["ordenes"] * 100
)

print("\n=== DIFERENCIAS POR MONEDA ===")
print(resumen_moneda.round(2).to_string())

# =====================================================
# 7. VALIDACIÓN DE LA FÓRMULA DE VENTAS
# =====================================================

print("\n=== VALIDACIÓN DE FÓRMULA DE VENTAS ===")

for nombre, df in [
    ("Cabecera", ventas),
    ("Detalle", detalle)
]:
    neto_calculado = (
        df["gross_sales"]
        - df["discount_amount"]
        + df["tax_amount"]
        + df["shipping_cost"]
    )

    diferencia = df["net_sales"] - neto_calculado

    print(f"\n{nombre}")
    print("Registros evaluados:", len(df))
    print(
        "Registros con diferencia > 0.05:",
        diferencia.abs().gt(0.05).sum()
    )
    print(
        "Diferencia máxima absoluta:",
        round(diferencia.abs().max(), 2)
    )

# =====================================================
# 8. DISTRIBUCIÓN DE MONEDAS POR PAÍS
# =====================================================

print("\n=== MONEDAS POR PAÍS ===")

monedas_pais = pd.crosstab(
    ventas["customer_country"],
    ventas["currency"]
)

print(monedas_pais.to_string())

# =====================================================
# 9. DIFERENCIAS RELATIVAS
# =====================================================

comparacion["diferencia_relativa"] = np.where(
    comparacion["net_sales_detalle"].abs() > 0.01,
    comparacion["dif_neta"]
    / comparacion["net_sales_detalle"].abs() * 100,
    np.nan
)

distintas = comparacion.loc[
    comparacion["dif_neta"].abs() > 0.01,
    "diferencia_relativa"
]

print("\n=== DIFERENCIAS RELATIVAS ===")
print(
    "Mediana (%):",
    round(distintas.median(), 2)
)
print(
    "Mínimo (%):",
    round(distintas.min(), 2)
)
print(
    "Máximo (%):",
    round(distintas.max(), 2)
)

print("\n======================================")
print("AUDITORÍA COMERCIAL FINALIZADA")
print("======================================")
