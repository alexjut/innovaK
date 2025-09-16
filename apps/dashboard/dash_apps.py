# apps/dashboard/dash_apps.py
import pandas as pd
import plotly.express as px

from dash import dcc, html
from dash import Input, Output, State
from django_plotly_dash import DjangoDash

from apps.dashboard.services.intent_analyzer import IntentAnalyzer, QueryType
from apps.dashboard.services.query_builder import SafeQueryBuilder

# Inicializa app Dash (nombre estable para DPD)
app = DjangoDash("DashboardAI")

app.layout = html.Div([
    html.H2("🤖 Consulta Inteligente · Personas", style={"textAlign": "center", "marginBottom": "20px"}),

    html.Div([
        dcc.Input(
            id="input-pregunta",
            type="text",
            placeholder="Ej: ¿cuántas personas hay en estrato 2?",
            debounce=True,
            style={"width": "60%"}
        ),
        html.Button("Consultar", id="btn-ejecutar", n_clicks=0, style={"marginLeft": "10px"}),
    ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}),

    html.Div(id="descripcion-consulta", style={"textAlign": "center", "fontWeight": "bold", "marginBottom": "20px"}),
    dcc.Graph(id="resultado-grafico"),
    html.Div(id="tabla-datos", style={"marginTop": "20px", "padding": "0 40px"})
])

@app.callback(
    [Output("descripcion-consulta", "children"),
     Output("resultado-grafico", "figure"),
     Output("tabla-datos", "children")],
    [Input("btn-ejecutar", "n_clicks")],
    [State("input-pregunta", "value")]
)
def ejecutar_consulta(n_clicks, pregunta):
    if not pregunta:
        return "❗ Ingresa una pregunta para consultar.", {}, ""

    try:
        # 1) Analizar intención (solo Persona)
        intent = IntentAnalyzer.analyze(pregunta)

        # 2) Construir consulta segura
        qb = SafeQueryBuilder.build(intent)

        # 3) Ejecutar según tipo
        if intent["type"] == QueryType.COUNT.value:
            total = qb["executable"]()
            fig = px.bar(x=["Resultado"], y=[total], labels={"x": "Consulta", "y": "Total"})
            return qb["description"], fig, ""

        if intent["type"] == QueryType.FILTER.value:
            rows = qb["executable"]()  # devuelve list(dict) con columnas por defecto
            if not rows:
                return "Sin resultados.", {}, ""

            df = pd.DataFrame(rows)

            # Si al menos hay 2 columnas, grafiquemos algo rápido (1a vs 2a)
            if len(df.columns) >= 2:
                fig = px.bar(df, x=df.columns[0], y=df.columns[1])
            else:
                fig = {}

            # Render de tabla sencilla
            header = html.Thead(html.Tr([html.Th(col) for col in df.columns]))
            body = html.Tbody([
                html.Tr([html.Td(row.get(col, "")) for col in df.columns])
                for row in rows
            ])
            table = html.Table([header, body], style={"width": "100%", "overflowX": "auto"})

            return qb["description"], fig, table

        return "⚠️ Tipo de consulta no reconocida.", {}, ""

    except Exception as e:
        return f"❌ Error al procesar la consulta: {e}", {}, ""
