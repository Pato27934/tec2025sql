# Asistente de Tienda IA (tec2025sql)

Este proyecto es un asistente conversacional para análisis de datos de ventas, productos y distribuidores, usando FastAPI, OpenAI y una base de datos SQLite. Permite hacer preguntas en lenguaje natural sobre los datos de una tienda y obtener respuestas interpretadas, tablas de resultados y el query SQL generado.

## Estructura del proyecto

- `main.py`: API principal con FastAPI. Recibe preguntas, consulta OpenAI para generar SQL, ejecuta el query en SQLite y responde con interpretación, tabla y query.
- `create_db.py`: Script para crear y poblar la base de datos `store.db` con datos de ejemplo (productos, distribuidores, ventas).
- `prompt.txt`: Prompt base para el modelo de OpenAI, describe la estructura de la base y reglas de negocio.
- `requirements.txt`: Dependencias del proyecto.
- `templates/index.html`: Interfaz web para interactuar con el asistente.
- `store.db`: Base de datos SQLite generada por `create_db.py`.

## Instalación y uso

1. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Crea la base de datos de ejemplo:
   ```bash
   python create_db.py
   ```
3. Exporta tu clave de OpenAI:
   ```bash
   export OPENAI_API_KEY=tu_clave
   ```
4. Ejecuta el servidor:
   ```bash
   uvicorn main:app --reload
   ```
5. Abre el navegador en [http://localhost:8000](http://localhost:8000)

## ¿Cómo funciona?

- El usuario escribe una pregunta de negocio (ej: "¿Cuáles son los productos más vendidos?").
- El backend usa un prompt especializado (`prompt.txt`) y OpenAI para generar un query SQL adecuado.
- El query se adapta a SQLite, se ejecuta y se muestra la respuesta interpretada, la tabla de resultados y el SQL generado.

## Estructura de la base de datos

**Productos**
- CveArticulo (INT, PK)
- Nombre_Articulo (VARCHAR)
- Categoria (VARCHAR)
- TamanioDeFoto (VARCHAR)
- TamanioFotoConNumero (FLOAT)
- NumeroPagina (INT)
- NumeroPaginaCatalogo (VARCHAR)
- Posicion (VARCHAR)
- Rango_PN_Nuevo (VARCHAR)
- Rango_PE_Nuevo (VARCHAR)
- TBasica (VARCHAR)
- Precio_Especial_Unitario (FLOAT)
- Precio_Normal_Unitario (FLOAT)

**Distribuidores**
- ClaveDistribuidor (VARCHAR, PK)
- Clasificacion (VARCHAR)
- Cod_Aso (INT)
- Municipio (VARCHAR)
- Estado (VARCHAR)
- Zona_Metropolitana (VARCHAR)

**Ventas**
- id (INTEGER, PK)
- Catálogo (INT)
- ClaveDistribuidor (VARCHAR)
- CveArticulo (INT)
- Descuento (FLOAT)
- RangoDescuentos (VARCHAR)
- UnidadesVendidas (INT)
- VentaCatalogo (FLOAT)
- Fecha (DATE)

## Reglas de negocio y métricas frecuentes

- Ventas ($): SUM(VentaCatalogo)
- Unidades Vendidas: SUM(UnidadesVendidas)
- Precio Normal Promedio: AVG(Precio_Normal_Unitario)
- Precio Especial Promedio: AVG(Precio_Especial_Unitario)
- Descuento Promedio: AVG(Descuento)
- SKU’s: COUNT(DISTINCT CveArticulo)
- Participación en Ventas: SUM(VentaCatalogo) / SUM(VentaCatalogo Total)

## Interfaz Web

La interfaz web (`templates/index.html`) permite hacer preguntas y ver respuestas en tiempo real, con interpretación, tabla y query SQL.

## Dependencias principales
- fastapi
- uvicorn
- openai
- pydantic
- jinja2
- langgraph
- langchain

## Créditos
Desarrollado para Tec de Monterrey, 2025.
