import os 
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# -------------------------
# 1. CARGA Y PROCESAMIENTO DE DATOS
# -------------------------
DATA_URL = "https://www.datos.gov.co/resource/gwn7-wfu5.json"

print("⏳ Cargando datos...")
try:
    df = pd.read_json(DATA_URL)
    df.columns = [c.strip() for c in df.columns]

    col_fem = [c for c in df.columns if c.startswith("matriculacion_fem")]
    col_masc = [c for c in df.columns if c.startswith("matriculacion_masc")]
    col_tasa = [c for c in df.columns if c.startswith("tasa")]
    col_ipg = [c for c in df.columns if c.startswith("ipg")]

    for c in col_fem + col_masc + col_tasa + col_ipg:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "anno_inf" in df.columns:
        df["anno_inf"] = pd.to_numeric(df["anno_inf"], errors="coerce").astype("Int64")

    df["TOTAL_FEM"] = df[col_fem].sum(axis=1)
    df["TOTAL_MASC"] = df[col_masc].sum(axis=1)
    df["TOTAL"] = df["TOTAL_FEM"] + df["TOTAL_MASC"]

    years = sorted([int(x) for x in df["anno_inf"].dropna().unique()]) if "anno_inf" in df.columns else []
    depts = sorted(df["departamento"].dropna().unique())
    print("✅ Datos cargados exitosamente.")

except Exception as e:
    print(f"❌ Error cargando datos: {e}")
    df = pd.DataFrame()
    years, depts = [], []

age_groups = [
    ("3y4", "matriculacion_fem_3y4", "matriculacion_masc_3y4"),
    ("5", "matriculacion_fem_5", "matriculacion_masc_5"),
    ("6a10", "matriculacion_fem_6a10", "matriculacion_masc_6a10"),
    ("11a14", "matriculacion_fem_11a14", "matriculacion_masc_11a14"),
    ("15y16", "matriculacion_fem_15y16", "matriculacion_masc_15y16"),
]

# -------------------------
# 2. CONFIGURACIÓN DE LA APP (LIGHT MODE)
# -------------------------
# Usamos LITERA para un estilo limpio y profesional
app = Dash(__name__, external_stylesheets=[dbc.themes.LITERA])
server = app.server
app.title = "Dashboard Educativo"

# -------------------------
# 3. DISEÑO (LAYOUT)
# -------------------------
app.layout = html.Div([
    
    html.Button("☰", id="toggle-sidebar", className="sidebar-btn"),

    html.Div(id="sidebar", children=[
        html.Div("Menu de filtros", className="sidebar-title"),
        
        html.Label("📅 AÑO"),
        dcc.Dropdown(id="filtro_ano", 
                     options=[{"label": y, "value": y} for y in years],
                     value=None, placeholder="Todos los años", clearable=True),

        html.Label("📍 DEPARTAMENTO"),
        dcc.Dropdown(id="filtro_dep", 
                     options=[{"label": d, "value": d} for d in depts],
                     value=[], multi=True, placeholder="Seleccionar..."),
        
        html.Label("⚧ GÉNERO"),
        dcc.RadioItems(id="filtro_genero",
                       options=[
                           {"label":" Total", "value":"both"},
                           {"label":" Fem", "value":"fem"},
                           {"label":" Masc", "value":"masc"},
                       ],
                       value="both", inline=True,
                       labelStyle={"marginRight": "15px", "marginTop": "5px"}),
        
        html.Div(style={"marginTop": "auto", "paddingTop": "20px"}, children=[
             html.Hr(style={"borderColor": "#e2e8f0"}),
             html.Small("Fuente: Datos Abiertos Colombia", style={"color": "#64748b"})
        ])
    ]),

    html.Div(id="main-content", children=[
        html.Div(id="kpi-row"),
        
        dcc.Tabs(id="tabs", value="tab_trend", parent_className="custom-tabs", className="custom-tabs-container", children=[
            dcc.Tab(label="📈 TENDENCIAS", value="tab_trend", className="custom-tab", selected_className="custom-tab--selected"),
            dcc.Tab(label="🌍 GEOGRAFÍA", value="tab_dept", className="custom-tab", selected_className="custom-tab--selected"),
            dcc.Tab(label="👥 DEMOGRAFÍA", value="tab_age", className="custom-tab", selected_className="custom-tab--selected"),
            dcc.Tab(label="🔗 CORRELACIONES", value="tab_corr", className="custom-tab", selected_className="custom-tab--selected"),
        ]),
        
        html.Div(id="tab-content"),
        
        html.Div(className="footer", children=[
            html.Div("Dashboard Educativo Interactivo"),
            html.Div("Ingeniería de Sistemas – Universidad Libre • 2025", style={"fontSize": "0.75rem", "marginTop": "5px"})
        ])
    ])
])

# -------------------------
# 4. CALLBACKS
# -------------------------
@app.callback(
    Output("sidebar", "className"),
    Input("toggle-sidebar", "n_clicks"),
    State("sidebar", "className"),
    prevent_initial_call=True
)
def toggle_menu(n, current):
    return "" if current == "open" else "open"

@app.callback(
    [Output("kpi-row", "children"), Output("tab-content", "children")],
    [Input("filtro_ano", "value"), Input("filtro_dep", "value"), 
     Input("filtro_genero", "value"), Input("tabs", "value")]
)
def update_dashboard(filtro_ano, filtro_dep, filtro_genero, active_tab):
    d = df.copy()
    if d.empty: return [], html.Div("⚠️ No hay datos disponibles.", style={"color": "#64748b", "textAlign": "center", "padding": "50px"})
    
    if filtro_ano: 
        d = d[d["anno_inf"] == int(filtro_ano)]
    if filtro_dep and len(filtro_dep) > 0: 
        d = d[d["departamento"].isin(filtro_dep)]

    tf = int(d["TOTAL_FEM"].sum())
    tm = int(d["TOTAL_MASC"].sum())
    ipg = round((tf/tm), 2) if tm > 0 else 0
    top_dep = d.groupby("departamento")["TOTAL"].sum().idxmax() if not d.empty else "-"

    def crear_tarjeta(titulo, valor):
        return html.Div(className="kpi-card", children=[
            html.Div(titulo, className="kpi-title"),
            html.Div(valor, className="kpi-value")
        ])

    kpis = [
        crear_tarjeta("Matrícula Femenina", f"{tf:,.0f}"),
        crear_tarjeta("Matrícula Masculina", f"{tm:,.0f}"),
        crear_tarjeta("Índice de Paridad", f"{ipg}"),
        crear_tarjeta("Top Departamento", top_dep),
    ]

    # Configuración para TEMA CLARO
    light_layout = dict(
        template="plotly_white",     # CLAVE: Tema claro de Plotly
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",  
        margin=dict(t=50, l=20, r=20, b=30),
        font=dict(family="Segoe UI, sans-serif", size=12, color="#1e293b"), # Texto oscuro
        title_font=dict(size=20, color="#0ea5e9") # Título azul acento
    )

    content = html.Div()
    
    if active_tab == "tab_trend":
        if "anno_inf" in d.columns:
            trend = d.groupby("anno_inf")[["TOTAL_FEM","TOTAL_MASC","TOTAL"]].sum().reset_index()
            fig = px.line(trend, x="anno_inf", y=["TOTAL_FEM","TOTAL_MASC","TOTAL"], markers=True,
                          color_discrete_map={"TOTAL_FEM": "#ec4899", "TOTAL_MASC": "#0ea5e9", "TOTAL": "#64748b"}) # Rosa y Azul más vivos
            fig.update_layout(**light_layout, title="Evolución Histórica de Matrículas")
            fig.update_xaxes(showgrid=True, gridcolor="#f1f5f9") # Rejilla muy suave
            fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
        else:
            fig = go.Figure().add_annotation(text="Sin datos de año", showarrow=False)
        content = dcc.Graph(figure=fig)

    elif active_tab == "tab_dept":
        top_df = d.groupby("departamento")["TOTAL"].sum().nlargest(15).reset_index().sort_values("TOTAL", ascending=True)
        fig = px.bar(top_df, x="TOTAL", y="departamento", orientation="h", text="TOTAL",
                     color="TOTAL", color_continuous_scale="Blues") # Escala Azul
        fig.update_layout(**light_layout, title="Top 15 Departamentos", yaxis={'categoryorder':'total ascending'})
        fig.update_traces(texttemplate='%{text:.2s}', textposition='outside')
        content = dcc.Graph(figure=fig, style={"height": "600px"})

    elif active_tab == "tab_age":
        sp = []
        for g, f, m in age_groups:
            sp.append({"Grupo": g, "Fem": d[f].sum() if f in d else 0, "Masc": d[m].sum() if m in d else 0})
        sdf = pd.DataFrame(sp)
        
        fig = go.Figure()
        if filtro_genero in ["both", "fem"]:
            fig.add_trace(go.Bar(x=sdf["Grupo"], y=sdf["Fem"], name="Femenino", marker_color="#ec4899")) 
        if filtro_genero in ["both", "masc"]:
            fig.add_trace(go.Bar(x=sdf["Grupo"], y=sdf["Masc"], name="Masculino", marker_color="#0ea5e9")) 
            
        fig.update_layout(**light_layout, title="Distribución por Grupo de Edad", barmode="group")
        content = dcc.Graph(figure=fig)

    else:
        cols = ["TOTAL","TOTAL_FEM","TOTAL_MASC"] + col_tasa[:3] + col_ipg[:3]
        cols = [c for c in cols if c in d.columns]
        if len(cols) > 1:
            corr = d[cols].corr()
            fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="PuBu", aspect="auto") # Escala Púrpura-Azul
            fig.update_layout(**light_layout, title="Matriz de Correlación")
        else:
            fig = go.Figure().add_annotation(text="Datos insuficientes", showarrow=False)
        content = dcc.Graph(figure=fig)

    return kpis, content

port = int(os.environ.get("PORT", 8080)) 

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=port)
