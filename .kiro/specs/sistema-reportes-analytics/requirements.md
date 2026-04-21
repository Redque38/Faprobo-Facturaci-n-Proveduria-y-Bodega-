# Documento de Requerimientos: Sistema de Reportes y Analytics

## Introducción

El Sistema de Reportes y Analytics es un módulo complementario para Faprobo que permite generar reportes visuales y análisis de datos sobre ventas, compras, inventario y proveedores. Este módulo se integra con la arquitectura MVP existente, utiliza el Event Bus para comunicación desacoplada, y consulta las bases de datos SQLite (`catalogo.db` y `facturas.db`) para extraer información histórica y generar métricas de negocio.

El módulo incluye visualizaciones gráficas (barras, líneas, tortas), exportación de reportes a PDF y CSV, y un dashboard con KPIs clave del negocio.

## Glosario

- **Sistema_Reportes**: Módulo de reportes y analytics de Faprobo
- **Repositorio_Reportes**: Componente que consulta las bases de datos SQLite para extraer datos agregados
- **Vista_Reportes**: Interfaz gráfica PySide6 que muestra reportes y gráficos
- **Presenter_Reportes**: Intermediario MVP que coordina entre modelo y vista
- **Motor_Graficos**: Componente que genera visualizaciones usando matplotlib
- **Exportador**: Componente que genera archivos PDF y CSV
- **Dashboard_KPI**: Panel con indicadores clave de rendimiento
- **Periodo_Analisis**: Rango de fechas seleccionado para análisis (día, semana, mes, año, personalizado)
- **Metrica**: Valor calculado agregado (total ventas, margen, rotación, etc.)
- **Grafico**: Representación visual de datos (barras, líneas, torta, área)

## Requerimientos

### Requerimiento 1: Consulta de Datos Agregados

**User Story:** Como usuario del sistema, quiero consultar datos agregados de ventas, compras e inventario, para poder analizar el rendimiento del negocio en diferentes períodos.

#### Acceptance Criteria

1. WHEN el usuario selecciona un periodo de análisis, THE Repositorio_Reportes SHALL consultar las bases de datos SQLite y retornar datos agregados dentro del rango de fechas
2. THE Repositorio_Reportes SHALL calcular métricas de ventas (total vendido, cantidad de facturas, ticket promedio, impuestos recaudados)
3. THE Repositorio_Reportes SHALL calcular métricas de compras (total comprado, cantidad de facturas, costo promedio)
4. THE Repositorio_Reportes SHALL calcular métricas de inventario (valor total del stock, productos con stock bajo, productos sin movimiento)
5. THE Repositorio_Reportes SHALL calcular métricas por categoría de producto (ventas por categoría, margen por categoría)
6. THE Repositorio_Reportes SHALL calcular métricas por proveedor (compras por proveedor, productos por proveedor)
7. WHEN no existen datos para el periodo seleccionado, THE Repositorio_Reportes SHALL retornar estructuras vacías sin generar errores

### Requerimiento 2: Visualización de Reportes Gráficos

**User Story:** Como usuario del sistema, quiero visualizar reportes en formato gráfico, para poder interpretar tendencias y patrones de manera visual.

#### Acceptance Criteria

1. THE Vista_Reportes SHALL mostrar gráficos de barras para comparar ventas por periodo (diario, semanal, mensual)
2. THE Vista_Reportes SHALL mostrar gráficos de líneas para visualizar tendencias de ventas a lo largo del tiempo
3. THE Vista_Reportes SHALL mostrar gráficos de torta para distribución de ventas por categoría de producto
4. THE Vista_Reportes SHALL mostrar gráficos de barras horizontales para ranking de productos más vendidos (top 10)
5. THE Vista_Reportes SHALL mostrar gráficos de barras para comparar compras por proveedor
6. WHEN el usuario hace clic en un elemento del gráfico, THE Vista_Reportes SHALL mostrar detalles adicionales en un tooltip
7. THE Motor_Graficos SHALL generar gráficos usando matplotlib integrado con PySide6
8. THE Vista_Reportes SHALL aplicar el tema Dracula a los gráficos para mantener consistencia visual

### Requerimiento 3: Dashboard de KPIs

**User Story:** Como usuario del sistema, quiero ver un dashboard con indicadores clave de rendimiento, para poder monitorear el estado del negocio de un vistazo.

#### Acceptance Criteria

1. THE Dashboard_KPI SHALL mostrar el total de ventas del periodo seleccionado con formato de moneda costarricense
2. THE Dashboard_KPI SHALL mostrar el total de compras del periodo seleccionado con formato de moneda costarricense
3. THE Dashboard_KPI SHALL mostrar el margen bruto calculado como (ventas - compras) / ventas * 100
4. THE Dashboard_KPI SHALL mostrar la cantidad de facturas de venta emitidas en el periodo
5. THE Dashboard_KPI SHALL mostrar la cantidad de facturas de compra registradas en el periodo
6. THE Dashboard_KPI SHALL mostrar el ticket promedio calculado como total ventas / cantidad facturas
7. THE Dashboard_KPI SHALL mostrar la cantidad de productos con stock bajo (stock < 10 unidades)
8. THE Dashboard_KPI SHALL mostrar el valor total del inventario actual
9. WHEN un KPI muestra una mejora respecto al periodo anterior, THE Dashboard_KPI SHALL mostrar un indicador visual positivo (verde, flecha arriba)
10. WHEN un KPI muestra un deterioro respecto al periodo anterior, THE Dashboard_KPI SHALL mostrar un indicador visual negativo (rojo, flecha abajo)

### Requerimiento 4: Filtros y Selección de Periodo

**User Story:** Como usuario del sistema, quiero filtrar reportes por diferentes periodos de tiempo, para poder analizar datos históricos y comparar rendimiento.

#### Acceptance Criteria

1. THE Vista_Reportes SHALL proporcionar un selector de periodo con opciones predefinidas (Hoy, Esta semana, Este mes, Este año)
2. THE Vista_Reportes SHALL proporcionar un selector de rango personalizado con fecha inicio y fecha fin usando QDateEdit
3. WHEN el usuario selecciona un periodo predefinido, THE Sistema_Reportes SHALL calcular automáticamente las fechas de inicio y fin
4. WHEN el usuario cambia el periodo seleccionado, THE Presenter_Reportes SHALL emitir un evento al Event Bus para recargar los datos
5. THE Vista_Reportes SHALL proporcionar filtros adicionales por tipo de factura (venta, compra, todos)
6. THE Vista_Reportes SHALL proporcionar filtros adicionales por estado de factura (pendiente, pagada, anulada, todos)
7. THE Vista_Reportes SHALL proporcionar un filtro por categoría de producto
8. WHEN el usuario aplica filtros, THE Sistema_Reportes SHALL actualizar todos los gráficos y KPIs según los criterios seleccionados

### Requerimiento 5: Exportación de Reportes

**User Story:** Como usuario del sistema, quiero exportar reportes a PDF y CSV, para poder compartirlos con otros usuarios o archivarlos.

#### Acceptance Criteria

1. WHEN el usuario solicita exportar a PDF, THE Exportador SHALL generar un documento PDF con el dashboard de KPIs y los gráficos visibles
2. WHEN el usuario solicita exportar a CSV, THE Exportador SHALL generar un archivo CSV con los datos tabulares del reporte
3. THE Exportador SHALL incluir en el PDF el logo de Faprobo, título del reporte, periodo analizado y fecha de generación
4. THE Exportador SHALL incluir en el PDF todos los KPIs con sus valores y unidades
5. THE Exportador SHALL incluir en el PDF imágenes de los gráficos generados por matplotlib
6. THE Exportador SHALL incluir en el CSV encabezados descriptivos para cada columna
7. THE Exportador SHALL formatear números en el CSV usando punto como separador decimal
8. WHEN la exportación es exitosa, THE Vista_Reportes SHALL mostrar un mensaje de confirmación con la ruta del archivo generado
9. WHEN la exportación falla, THE Vista_Reportes SHALL mostrar un mensaje de error descriptivo

### Requerimiento 6: Reporte de Productos Más Vendidos

**User Story:** Como usuario del sistema, quiero ver un reporte de los productos más vendidos, para poder identificar los productos estrella y optimizar el inventario.

#### Acceptance Criteria

1. THE Sistema_Reportes SHALL calcular el ranking de productos más vendidos basado en la cantidad total vendida en el periodo
2. THE Sistema_Reportes SHALL calcular el ranking de productos más rentables basado en el margen total (precio_venta - precio_compra) * cantidad
3. THE Vista_Reportes SHALL mostrar una tabla con los top 10 productos más vendidos incluyendo código, nombre, cantidad vendida y total en colones
4. THE Vista_Reportes SHALL mostrar un gráfico de barras horizontales con los top 10 productos más vendidos
5. WHEN el usuario hace clic en un producto de la tabla, THE Vista_Reportes SHALL mostrar detalles adicionales (categoría, stock actual, precio)
6. THE Sistema_Reportes SHALL excluir productos de facturas anuladas del cálculo

### Requerimiento 7: Reporte de Proveedores

**User Story:** Como usuario del sistema, quiero ver un reporte de compras por proveedor, para poder evaluar relaciones comerciales y negociar mejores condiciones.

#### Acceptance Criteria

1. THE Sistema_Reportes SHALL calcular el total de compras por proveedor en el periodo seleccionado
2. THE Sistema_Reportes SHALL calcular la cantidad de facturas de compra por proveedor
3. THE Sistema_Reportes SHALL calcular el ticket promedio de compra por proveedor
4. THE Vista_Reportes SHALL mostrar una tabla con todos los proveedores activos y sus métricas de compra
5. THE Vista_Reportes SHALL mostrar un gráfico de barras con los top 5 proveedores por volumen de compra
6. THE Vista_Reportes SHALL permitir ordenar la tabla por diferentes columnas (nombre, total comprado, cantidad facturas)
7. WHEN un proveedor no tiene compras en el periodo, THE Vista_Reportes SHALL mostrar cero en las métricas sin excluirlo de la tabla

### Requerimiento 8: Análisis de Inventario

**User Story:** Como usuario del sistema, quiero analizar el estado del inventario, para poder identificar productos con stock bajo o sin movimiento y tomar decisiones de reabastecimiento.

#### Acceptance Criteria

1. THE Sistema_Reportes SHALL identificar productos con stock bajo (stock < 10 unidades)
2. THE Sistema_Reportes SHALL identificar productos sin movimiento (sin ventas en los últimos 30 días)
3. THE Sistema_Reportes SHALL calcular el valor total del inventario como suma de (stock * precio_compra) para todos los productos activos
4. THE Sistema_Reportes SHALL calcular la rotación de inventario por producto como cantidad_vendida / stock_promedio
5. THE Vista_Reportes SHALL mostrar una tabla de alertas con productos que requieren atención (stock bajo o sin movimiento)
6. THE Vista_Reportes SHALL mostrar un gráfico de distribución del valor del inventario por categoría
7. THE Vista_Reportes SHALL resaltar en rojo los productos con stock bajo en la tabla de alertas
8. THE Vista_Reportes SHALL resaltar en amarillo los productos sin movimiento en la tabla de alertas

### Requerimiento 9: Integración con Arquitectura MVP y Event Bus

**User Story:** Como desarrollador del sistema, quiero que el módulo de reportes siga la arquitectura MVP existente y use el Event Bus, para mantener consistencia arquitectónica y facilitar el mantenimiento.

#### Acceptance Criteria

1. THE Sistema_Reportes SHALL implementar el patrón MVP con Model, View y Presenter separados
2. THE Presenter_Reportes SHALL heredar de BasePresenter
3. THE Vista_Reportes SHALL emitir señales PySide6 (Signal) para todas las acciones del usuario
4. THE Presenter_Reportes SHALL suscribirse a las señales de la vista en el método _connect_events
5. THE Presenter_Reportes SHALL emitir eventos al Event Bus cuando se generen reportes o cambien filtros
6. THE Repositorio_Reportes SHALL recibir una instancia de SqliteManager en su constructor
7. THE Repositorio_Reportes SHALL usar transacciones de solo lectura para todas las consultas
8. THE Vista_Reportes SHALL aplicar el tema Dracula usando QSS consistente con el resto de la aplicación
9. THE Sistema_Reportes SHALL registrarse en el Dashboard principal como una nueva sección navegable

### Requerimiento 10: Manejo de Errores y Casos Límite

**User Story:** Como usuario del sistema, quiero que el módulo de reportes maneje errores de manera elegante, para poder continuar trabajando incluso cuando ocurran problemas.

#### Acceptance Criteria

1. WHEN ocurre un error al consultar la base de datos, THE Sistema_Reportes SHALL mostrar un mensaje de error descriptivo sin cerrar la aplicación
2. WHEN no existen datos para el periodo seleccionado, THE Vista_Reportes SHALL mostrar un mensaje informativo "No hay datos disponibles para el periodo seleccionado"
3. WHEN falla la generación de un gráfico, THE Vista_Reportes SHALL mostrar un placeholder con el mensaje de error sin afectar otros gráficos
4. WHEN falla la exportación a PDF o CSV, THE Sistema_Reportes SHALL registrar el error en logs y mostrar un mensaje al usuario
5. IF el usuario selecciona una fecha de inicio posterior a la fecha de fin, THEN THE Vista_Reportes SHALL mostrar una advertencia y no ejecutar la consulta
6. WHEN el cálculo de una métrica resulta en división por cero, THE Sistema_Reportes SHALL retornar cero o N/A según corresponda
7. THE Sistema_Reportes SHALL validar que todas las fechas estén en formato ISO antes de consultar la base de datos
