import requests
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Dashboard Predictivo Ventas IBM i", layout="wide")

# =========================
# Estilos
# =========================

st.markdown(
    """
    <style>
    .main-title {font-size:34px;font-weight:800;margin-bottom:6px;color:#1f2937;}
    .subtitle {font-size:15px;color:#6b7280;margin-bottom:24px;}
    .kpi-card {background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:18px 16px;box-shadow:0 2px 8px rgba(0,0,0,.04);}
    .kpi-label {font-size:13px;color:#6b7280;margin-bottom:6px;}
    .kpi-value {font-size:24px;font-weight:800;color:#111827;}
    .section-title {font-size:21px;font-weight:700;margin-top:22px;margin-bottom:12px;color:#111827;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="main-title">Dashboard Predictivo de Ventas IBM i</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">Analisis historico, proyeccion de ventas, margen esperado e insights automaticos</div>',
    unsafe_allow_html=True,
)

API_URL = "https://mcp.globallearningxxi.com/api/dashboard"
ANIOS = [2024, 2025, 2026]


# =========================
# Utilidades
# =========================


def money(value):
    return f"{float(value or 0):,.2f}"


def number(value):
    return f"{float(value or 0):,.0f}"


def limpiar_texto_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()
    return df


@st.cache_data(ttl=300)
def cargar_dashboard(anio: int) -> dict:
    response = requests.get(API_URL, params={"anio": anio}, timeout=60)
    content_type = response.headers.get("content-type", "")

    if response.status_code != 200:
        raise RuntimeError(
            f"API respondio HTTP {response.status_code}: {response.text[:500]}"
        )

    if "application/json" not in content_type.lower():
        raise RuntimeError(
            "La API no devolvio JSON. "
            f"Content-Type recibido: {content_type}. "
            f"Respuesta inicial: {response.text[:300]}"
        )

    return response.json()


def generar_forecast_lineal(
    mensual_df: pd.DataFrame, meses_futuros: int = 12
) -> pd.DataFrame:
    """
    Forecast simple y explicable:
    - Usa tendencia lineal sobre ventas mensuales historicas.
    - Aplica estacionalidad promedio por mes.
    - No requiere librerias externas como scikit-learn.
    """
    df = mensual_df.copy()
    df = df.sort_values(["ANIO", "MES"]).reset_index(drop=True)
    df["T"] = np.arange(1, len(df) + 1)

    y = df["TOTAL_VENTAS"].astype(float).values
    x = df["T"].astype(float).values

    if len(df) < 3:
        return pd.DataFrame()

    # Regresion lineal simple con numpy
    coef = np.polyfit(x, y, 1)
    pendiente = coef[0]
    intercepto = coef[1]

    # Estacionalidad: factor mensual contra promedio general
    promedio_general = df["TOTAL_VENTAS"].mean()
    estacionalidad = (
        df.groupby("MES")["TOTAL_VENTAS"].mean() / promedio_general
    ).to_dict()

    ultimo_anio = int(df.iloc[-1]["ANIO"])
    ultimo_mes = int(df.iloc[-1]["MES"])
    ultimo_t = int(df.iloc[-1]["T"])

    forecasts = []

    for i in range(1, meses_futuros + 1):
        nuevo_t = ultimo_t + i
        nuevo_mes = ultimo_mes + i
        nuevo_anio = ultimo_anio

        while nuevo_mes > 12:
            nuevo_mes -= 12
            nuevo_anio += 1

        base = intercepto + pendiente * nuevo_t
        factor = estacionalidad.get(nuevo_mes, 1.0)
        prediccion = max(base * factor, 0)

        forecasts.append(
            {
                "ANIO": nuevo_anio,
                "MES": nuevo_mes,
                "PERIODO": f"{nuevo_anio}-{str(nuevo_mes).zfill(2)}",
                "VENTAS_PREDICHAS": round(float(prediccion), 2),
            }
        )

    return pd.DataFrame(forecasts)


# =========================
# Sidebar
# =========================

with st.sidebar:
    st.header("Configuracion")
    meses_forecast = st.slider("Meses a proyectar", min_value=3, max_value=24, value=12)
    recargar = st.button("Recargar datos")

if recargar:
    cargar_dashboard.clear()


# =========================
# Carga de datos
# =========================

try:
    data_anios = {anio: cargar_dashboard(anio) for anio in ANIOS}
except Exception as exc:
    st.error("No se pudo cargar la informacion desde la API REST.")
    st.exception(exc)
    st.stop()


# =========================
# Consolidar KPIs y mensual
# =========================

kpis_rows = []
mensual_rows = []
zonas_rows = []
productos_rows = []

for anio, data in data_anios.items():
    if not data.get("ok", False):
        st.warning(f"La API no devolvio OK para {anio}")
        continue

    k = data.get("kpis", {})
    kpis_rows.append(
        {
            "ANIO": anio,
            "TOTAL_VENTAS": float(k.get("TOTAL_VENTAS") or 0),
            "TOTAL_COSTO": float(k.get("TOTAL_COSTO") or 0),
            "MARGEN": float(k.get("MARGEN") or 0),
            "UNIDADES": float(k.get("UNIDADES") or 0),
            "TICKET_PROMEDIO": float(k.get("TICKET_PROMEDIO") or 0),
        }
    )

    for row in data.get("evolucion_mensual", []):
        mensual_rows.append(row)

    for row in data.get("ventas_por_zona", []):
        row = dict(row)
        row["ANIO"] = anio
        zonas_rows.append(row)

    for row in data.get("top_productos", []):
        row = dict(row)
        row["ANIO"] = anio
        productos_rows.append(row)

kpis_df = pd.DataFrame(kpis_rows)
mensual_df = pd.DataFrame(mensual_rows)
zonas_df = limpiar_texto_df(pd.DataFrame(zonas_rows))
productos_df = limpiar_texto_df(pd.DataFrame(productos_rows))

if mensual_df.empty:
    st.error("No hay datos mensuales suficientes para generar prediccion.")
    st.stop()

mensual_df = mensual_df.sort_values(["ANIO", "MES"]).reset_index(drop=True)
mensual_df["PERIODO"] = (
    mensual_df["ANIO"].astype(str) + "-" + mensual_df["MES"].astype(str).str.zfill(2)
)

forecast_df = generar_forecast_lineal(mensual_df, meses_futuros=meses_forecast)


# =========================
# KPIs principales
# =========================

st.markdown(
    '<div class="section-title">Resumen ejecutivo historico</div>',
    unsafe_allow_html=True,
)

total_ventas = kpis_df["TOTAL_VENTAS"].sum()
total_margen = kpis_df["MARGEN"].sum()
total_unidades = kpis_df["UNIDADES"].sum()
margen_pct = (total_margen / total_ventas * 100) if total_ventas else 0
ticket_promedio = (total_ventas / total_unidades) if total_unidades else 0

c1, c2, c3, c4, c5 = st.columns(5)

items = [
    (c1, "Ventas historicas", money(total_ventas)),
    (c2, "Margen historico", money(total_margen)),
    (c3, "Margen %", f"{margen_pct:.2f}%"),
    (c4, "Unidades historicas", number(total_unidades)),
    (c5, "Ticket promedio", money(ticket_promedio)),
]

for col, label, value in items:
    with col:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================
# KPIs predictivos
# =========================

st.markdown(
    '<div class="section-title">Proyeccion predictiva</div>', unsafe_allow_html=True
)

ventas_predichas_total = (
    forecast_df["VENTAS_PREDICHAS"].sum() if not forecast_df.empty else 0
)
promedio_predicho = (
    forecast_df["VENTAS_PREDICHAS"].mean() if not forecast_df.empty else 0
)

ultimo_anio_completo = kpis_df.sort_values("ANIO").iloc[-1]
ventas_ultimo_anio = ultimo_anio_completo["TOTAL_VENTAS"]
crecimiento_estimado = (
    ((ventas_predichas_total - ventas_ultimo_anio) / ventas_ultimo_anio * 100)
    if ventas_ultimo_anio
    else 0
)

p1, p2, p3 = st.columns(3)

with p1:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Ventas proyectadas proximos {meses_forecast} meses</div>
            <div class="kpi-value">{money(ventas_predichas_total)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with p2:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Promedio mensual proyectado</div>
            <div class="kpi-value">{money(promedio_predicho)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with p3:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">Crecimiento estimado vs ultimo anio</div>
            <div class="kpi-value">{crecimiento_estimado:.2f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# Graficos
# =========================

st.markdown(
    '<div class="section-title">Ventas historicas y forecast</div>',
    unsafe_allow_html=True,
)

historico_chart = mensual_df[["PERIODO", "TOTAL_VENTAS"]].rename(
    columns={"TOTAL_VENTAS": "Historico"}
)
forecast_chart = forecast_df[["PERIODO", "VENTAS_PREDICHAS"]].rename(
    columns={"VENTAS_PREDICHAS": "Forecast"}
)

chart_df = pd.merge(
    historico_chart, forecast_chart, on="PERIODO", how="outer"
).set_index("PERIODO")
st.line_chart(chart_df)


col1, col2 = st.columns(2)

with col1:
    st.markdown(
        '<div class="section-title">Ventas por anio</div>', unsafe_allow_html=True
    )
    ventas_anio = kpis_df.set_index("ANIO")[["TOTAL_VENTAS", "MARGEN"]]
    st.bar_chart(ventas_anio)

with col2:
    st.markdown(
        '<div class="section-title">Ventas por zona y anio</div>',
        unsafe_allow_html=True,
    )
    if not zonas_df.empty:
        zonas_pivot = zonas_df.pivot_table(
            index="SALESZONE",
            columns="ANIO",
            values="TOTAL_VENTAS",
            aggfunc="sum",
        )
        st.bar_chart(zonas_pivot)
    else:
        st.info("No hay datos por zona.")


col3, col4 = st.columns(2)

with col3:
    st.markdown(
        '<div class="section-title">Top productos acumulado</div>',
        unsafe_allow_html=True,
    )
    if not productos_df.empty:
        prod_total = (
            productos_df.groupby("PRODUCT", as_index=False)["TOTAL_VENTAS"]
            .sum()
            .sort_values("TOTAL_VENTAS", ascending=False)
        )
        st.bar_chart(prod_total.set_index("PRODUCT")["TOTAL_VENTAS"])
    else:
        st.info("No hay datos de productos.")

with col4:
    st.markdown(
        '<div class="section-title">Ventas mensuales por anio</div>',
        unsafe_allow_html=True,
    )
    pivot_mensual = mensual_df.pivot_table(
        index="MES",
        columns="ANIO",
        values="TOTAL_VENTAS",
        aggfunc="sum",
    )
    st.line_chart(pivot_mensual)


# =========================
# Insights predictivos
# =========================

st.markdown(
    '<div class="section-title">Insights predictivos</div>', unsafe_allow_html=True
)

if not kpis_df.empty:
    mejor_anio = kpis_df.sort_values("TOTAL_VENTAS", ascending=False).iloc[0]
    st.success(
        f"El mejor anio historico es {int(mejor_anio['ANIO'])} con ventas de {money(mejor_anio['TOTAL_VENTAS'])}."
    )

if not forecast_df.empty:
    mejor_mes_forecast = forecast_df.sort_values(
        "VENTAS_PREDICHAS", ascending=False
    ).iloc[0]
    peor_mes_forecast = forecast_df.sort_values(
        "VENTAS_PREDICHAS", ascending=True
    ).iloc[0]

    st.success(
        f"El mes proyectado mas fuerte es {int(mejor_mes_forecast['MES'])}/{int(mejor_mes_forecast['ANIO'])} "
        f"con ventas estimadas de {money(mejor_mes_forecast['VENTAS_PREDICHAS'])}."
    )

    st.warning(
        f"El mes proyectado mas debil es {int(peor_mes_forecast['MES'])}/{int(peor_mes_forecast['ANIO'])} "
        f"con ventas estimadas de {money(peor_mes_forecast['VENTAS_PREDICHAS'])}."
    )

if crecimiento_estimado > 5:
    st.success(
        "La proyeccion sugiere crecimiento positivo relevante. Recomendacion: preparar inventario y capacidad comercial."
    )
elif crecimiento_estimado < -5:
    st.warning(
        "La proyeccion sugiere posible contraccion. Recomendacion: revisar demanda, promociones y mix de productos."
    )
else:
    st.info(
        "La proyeccion sugiere estabilidad. Recomendacion: optimizar margen y eficiencia operativa."
    )


# =========================
# Tablas
# =========================

st.markdown('<div class="section-title">Detalle de datos</div>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(
    ["KPIs historicos", "Historico mensual", "Forecast", "Productos"]
)

with tab1:
    st.dataframe(kpis_df, use_container_width=True)

with tab2:
    st.dataframe(mensual_df, use_container_width=True)

with tab3:
    st.dataframe(forecast_df, use_container_width=True)

with tab4:
    st.dataframe(productos_df, use_container_width=True)
