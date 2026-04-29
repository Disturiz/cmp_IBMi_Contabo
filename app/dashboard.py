import requests
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Dashboard Ventas IBM i",
    layout="wide",
)

st.title("馃搳 Dashboard Anal铆tico de Ventas IBM i")

DEFAULT_API_URL = "https://mcp.globallearningxxi.com/api/dashboard"

with st.sidebar:
    st.header("Filtros")
    anio = st.selectbox("A帽o", [2025, 2024, 2026, "Todos"], index=0)
    api_url = st.text_input("API Dashboard", DEFAULT_API_URL)
    recargar = st.button("Recargar datos")

params = {}
if anio != "Todos":
    params["anio"] = int(anio)


@st.cache_data(ttl=300)
def cargar_dashboard(url: str, params: dict) -> dict:
    response = requests.get(url, params=params, timeout=45)
    content_type = response.headers.get("content-type", "")

    if response.status_code != 200:
        raise RuntimeError(
            f"API respondi贸 HTTP {response.status_code}: {response.text[:500]}"
        )

    if "application/json" not in content_type.lower():
        raise RuntimeError(
            "La API no devolvi贸 JSON. "
            f"Content-Type recibido: {content_type}. "
            f"Respuesta inicial: {response.text[:300]}"
        )

    return response.json()


if recargar:
    cargar_dashboard.clear()

try:
    data = cargar_dashboard(api_url, params)
except Exception as exc:
    st.error("No se pudo cargar el dashboard desde la API REST.")
    st.exception(exc)
    st.stop()

if not data.get("ok", False):
    st.error(data.get("error", "La API devolvi贸 una respuesta no exitosa."))
    st.json(data)
    st.stop()


kpis = data.get("kpis", {})
zonas = pd.DataFrame(data.get("ventas_por_zona", []))
paises = pd.DataFrame(data.get("ventas_por_pais", []))
productos = pd.DataFrame(data.get("top_productos", []))
margen_producto = pd.DataFrame(data.get("margen_por_producto", []))
mensual = pd.DataFrame(data.get("evolucion_mensual", []))


def limpiar_texto_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).str.strip()
    return df


zonas = limpiar_texto_df(zonas)
paises = limpiar_texto_df(paises)
productos = limpiar_texto_df(productos)
margen_producto = limpiar_texto_df(margen_producto)
mensual = limpiar_texto_df(mensual)

st.subheader("Indicadores principales")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("馃挵 Ventas", f"{float(kpis.get('TOTAL_VENTAS') or 0):,.2f}")
col2.metric("馃捀 Costo", f"{float(kpis.get('TOTAL_COSTO') or 0):,.2f}")
col3.metric("馃搱 Margen", f"{float(kpis.get('MARGEN') or 0):,.2f}")
col4.metric("馃摝 Unidades", f"{float(kpis.get('UNIDADES') or 0):,.0f}")
col5.metric("馃Ь Ticket Prom.", f"{float(kpis.get('TICKET_PROMEDIO') or 0):,.2f}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Ingresos por Zona")
    if not zonas.empty and {"SALESZONE", "TOTAL_VENTAS"}.issubset(zonas.columns):
        st.bar_chart(zonas.set_index("SALESZONE")["TOTAL_VENTAS"])
    else:
        st.info("No hay datos de ventas por zona.")

with col2:
    st.subheader("Ingresos por Pa铆s")
    if not paises.empty and {"COUNTRY", "TOTAL_VENTAS"}.issubset(paises.columns):
        st.bar_chart(paises.set_index("COUNTRY")["TOTAL_VENTAS"])
    else:
        st.info("No hay datos de ventas por pa铆s.")

col3, col4 = st.columns(2)

with col3:
    st.subheader("Top Productos por Ventas")
    if not productos.empty and {"PRODUCT", "TOTAL_VENTAS"}.issubset(productos.columns):
        st.bar_chart(productos.set_index("PRODUCT")["TOTAL_VENTAS"])
    else:
        st.info("No hay datos de productos.")

with col4:
    st.subheader("Margen por Producto")
    if not margen_producto.empty and {"PRODUCT", "MARGEN"}.issubset(
        margen_producto.columns
    ):
        st.bar_chart(margen_producto.set_index("PRODUCT")["MARGEN"])
    else:
        st.info("No hay datos de margen por producto.")

st.subheader("Evoluci贸n Mensual")
if not mensual.empty and {"ANIO", "MES", "TOTAL_VENTAS", "MARGEN"}.issubset(
    mensual.columns
):
    mensual = mensual.copy()
    mensual["PERIODO"] = (
        mensual["ANIO"].astype(str) + "-" + mensual["MES"].astype(str).str.zfill(2)
    )
    st.line_chart(mensual.set_index("PERIODO")[["TOTAL_VENTAS", "MARGEN"]])
else:
    st.info("No hay datos de evoluci贸n mensual.")

st.subheader("Detalle - Top Productos")
st.dataframe(productos, use_container_width=True)

st.subheader("Detalle - Ventas por Zona")
st.dataframe(zonas, use_container_width=True)

st.subheader("Detalle - Evoluci贸n Mensual")
st.dataframe(mensual, use_container_width=True)

st.subheader("馃 Insights autom谩ticos")

if not zonas.empty and {"SALESZONE", "TOTAL_VENTAS"}.issubset(zonas.columns):
    zona_top = zonas.sort_values("TOTAL_VENTAS", ascending=False).iloc[0]
    st.write(
        f"鉁?La zona con mayor ingreso es **{zona_top['SALESZONE']}** "
        f"con **{zona_top['TOTAL_VENTAS']:,.2f}**."
    )

if not paises.empty and {"COUNTRY", "TOTAL_VENTAS"}.issubset(paises.columns):
    pais_top = paises.sort_values("TOTAL_VENTAS", ascending=False).iloc[0]
    st.write(
        f"鉁?El pa铆s con mayor ingreso es **{pais_top['COUNTRY']}** "
        f"con **{pais_top['TOTAL_VENTAS']:,.2f}**."
    )

if not productos.empty and {"PRODUCT", "TOTAL_VENTAS"}.issubset(productos.columns):
    prod_top = productos.sort_values("TOTAL_VENTAS", ascending=False).iloc[0]
    st.write(
        f"鉁?El producto l铆der es **{prod_top['PRODUCT']}** "
        f"con **{prod_top['TOTAL_VENTAS']:,.2f}** en ventas."
    )

if not mensual.empty and {"ANIO", "MES", "TOTAL_VENTAS"}.issubset(mensual.columns):
    mejor_mes = mensual.sort_values("TOTAL_VENTAS", ascending=False).iloc[0]
    st.write(
        f"鉁?El mejor mes fue **{int(mejor_mes['MES'])}/{int(mejor_mes['ANIO'])}** "
        f"con **{mejor_mes['TOTAL_VENTAS']:,.2f}** en ventas."
    )
