# Diccionario de métricas

## Alcance general

- Las páginas Executive Overview, Customer Analytics y Product & Sales consideran únicamente órdenes con `order_status = Completed`.
- Orders & Operations considera todos los estados de orden.
- Cada país se analiza en la moneda registrada en la fuente. No se convierten ni agregan monedas distintas.
- Los filtros de fecha se aplican sobre `order_date`, incluyendo las fechas inicial y final.

## Métricas comerciales

### Ventas brutas

Suma de `gross_sales` de las órdenes completadas dentro del contexto de filtros.

### Ventas netas

Suma de `net_sales` de las órdenes completadas. La fórmula validada en la fuente es:

`gross_sales - discount_amount + tax_amount + shipping_cost`

### Órdenes

Conteo distinto de `order_id`.

### Unidades

En las páginas de cabecera se utiliza la suma de `quantity` de la tabla principal. En Product & Sales se identifican separadamente las unidades provenientes de `order_items`.

### Ticket promedio

`ventas netas / órdenes únicas completadas`

### Variación frente al período anterior

`(valor actual / valor anterior) - 1`

El período anterior es el intervalo inmediatamente precedente con la misma cantidad de días y los mismos filtros. Si no existe cobertura completa o la base anterior es cero, la variación no se presenta.

## Métricas de clientes

### Clientes únicos

Conteo distinto de `customer_id` con al menos una orden completada en el período.

### Órdenes por cliente

`órdenes únicas completadas / clientes únicos`

Representa frecuencia observada en el rango seleccionado, no frecuencia histórica total.

### Ventas por cliente

`ventas netas / clientes únicos`

## Métricas operativas

### Tasa de cancelación

`órdenes Cancelled / total de órdenes registradas`

### Tasa de devolución

`órdenes Returned / total de órdenes registradas`

### Tasa completada

`órdenes Completed / total de órdenes registradas`

## Productos y categorías

Las ventas por categoría, subcategoría, marca y producto se asignan proporcionalmente desde el `net_sales` de cabecera según el peso del `net_sales` de cada línea de `order_items` dentro de la orden.

Esta asignación es provisional por las diferencias detectadas entre cabecera y detalle. El margen queda fuera del dashboard hasta validar que `product_cost` sea comparable con la definición de ventas netas.
