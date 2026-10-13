# E-commerce Sales & Customer Analytics Dashboard

Dashboard interactivo desarrollado con Streamlit para explorar ventas, clientes,
productos y operaciones de un e-commerce a partir de un conjunto de datos
sintético.

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run Executive_Overview.py
```

## Alcance analítico

- Executive overview con KPIs y comparación contra el período anterior.
- Análisis de clientes, segmentos y perfiles demográficos.
- Análisis de productos, categorías, subcategorías y marcas.
- Seguimiento de estados de orden, cancelaciones y devoluciones.

Las ventas se presentan por país en la moneda registrada en la fuente, sin
conversiones entre monedas. El análisis comercial utiliza órdenes completadas;
la página operativa considera todos los estados.
