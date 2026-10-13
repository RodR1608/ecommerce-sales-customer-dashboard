# Registro breve de decisiones sobre IA

## Aporte utilizado

Se utilizó IA como apoyo para proponer alternativas de arquitectura, jerarquía visual, comparación temporal y selección de gráficos para el dashboard exploratorio.

## Decisiones humanas aplicadas

1. Se descartaron mapas como elemento principal de Executive Overview porque no aportaban una decisión prioritaria y aumentaban la carga visual. La geografía queda como capacidad secundaria de exploración.
2. Se descartaron donas, pirámides y otros gráficos de comparación imprecisa. Se priorizaron líneas para evolución y barras ordenadas para rankings y participaciones.
3. Categorías y canales dejaron de competir simultáneamente en la vista ejecutiva y se organizaron en pestañas.
4. El análisis de clientes y los estados de órdenes se trasladaron a páginas especializadas para que Executive Overview pueda entenderse rápidamente.
5. El margen bruto no se incorporó porque la existencia de `product_cost` no demuestra por sí sola que sea comparable con ventas netas.

## Validaciones realizadas

- Correspondencia de moneda por país.
- Cobertura y consistencia de `customer_id` entre ventas y `customer_master`.
- Fórmula de ventas netas y tratamiento de descuentos, impuestos y envío.
- Diferencias entre valores de cabecera y `order_items`.
- Pruebas funcionales de filtros, cambios de país y navegación entre páginas.

La IA aportó alternativas y código de apoyo; la selección final, las exclusiones y las definiciones métricas responden al brief, al feedback docente y a la validación del equipo.
