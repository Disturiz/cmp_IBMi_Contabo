"""
Servidor MCP remoto para consultar la tabla VENTASPF en IBM i (PUB400).

Ejecución:
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Endpoint MCP SSE:
    https://mcp.globallearningxxi.com/sse

Endpoint REST Dashboard:
    https://mcp.globallearningxxi.com/api/dashboard?anio=2025
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from app.tools import (
    contar_registros,
    consultar_ventas,
    dashboard_ventas,
    ejecutar_sql_select,
    healthcheck,
    listar_columnas,
    listar_muestras,
    resumen_por_producto,
    top_productos_por_zona,
    ventas_por_pais,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("mcp_ibmi_ventapf")


mcp = FastMCP(
    "IBM i VENTAPF MCP",
    instructions=(
        "Servidor MCP de solo lectura para consultar la tabla VENTASPF en IBM i PUB400. "
        "Usa healthcheck o listar_columnas para validar la estructura. "
        "No se permite modificar datos."
    ),
    json_response=True,
    host="0.0.0.0",
    port=8000,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.tool()
def ping_ibmi() -> dict:
    return healthcheck()


@mcp.tool()
def obtener_columnas() -> dict:
    return listar_columnas()


@mcp.tool()
def ver_muestras(limite: int = 5) -> dict:
    return listar_muestras(limite=limite)


@mcp.tool()
def total_registros() -> dict:
    return contar_registros()


@mcp.tool()
def ventas_por_filtros(
    limite: int = 20,
    cliente: str | None = None,
    producto: str | None = None,
    order_by: str | None = None,
    descending: bool = True,
) -> dict:
    return consultar_ventas(
        limite=limite,
        cliente=cliente,
        producto=producto,
        order_by=order_by,
        descending=descending,
    )


@mcp.tool()
def top_productos(limite: int = 10) -> dict:
    return resumen_por_producto(limite=limite)


@mcp.tool()
def ventas_por_country() -> dict:
    return ventas_por_pais()


@mcp.tool()
def consultar_sql(sql: str, limite: int = 100) -> dict:
    """
    Ejecuta consultas SQL SELECT de solo lectura sobre IBM i.
    Usa la tabla GLEARN211.VENTASPF.
    No permite modificaciones de datos.
    """
    return ejecutar_sql_select(sql=sql, limite=limite)


@mcp.tool()
def top_productos_zona(anio: int = 2025) -> dict:
    """
    Devuelve el producto con mayor ingreso por cada zona de ventas para un año.
    """
    return top_productos_por_zona(anio=anio)


@mcp.tool()
def dashboard_completo(anio: int | None = None) -> dict:
    """
    Genera un dashboard completo de ventas con KPIs, zonas, países,
    productos, margen y evolución mensual.
    """
    return dashboard_ventas(anio=anio)


app = mcp.sse_app()


from starlette.requests import Request


async def root(request: Request):
    return JSONResponse(
        {
            "ok": True,
            "service": "IBM i VENTASPF MCP",
            "mcp_sse": "/sse",
            "dashboard_api": "/api/dashboard?anio=2025",
        }
    )


app.add_route("/", root)


@app.route("/api/dashboard")
async def api_dashboard(request):
    """
    Endpoint REST para que Streamlit pueda consumir el dashboard como JSON.

    Ejemplo:
        https://mcp.globallearningxxi.com/api/dashboard?anio=2025
    """
    anio_param = request.query_params.get("anio")

    try:
        anio = int(anio_param) if anio_param else None
    except ValueError:
        return JSONResponse(
            {"ok": False, "error": "El parámetro 'anio' debe ser numérico."},
            status_code=400,
        )

    try:
        return JSONResponse(dashboard_ventas(anio=anio))
    except Exception as exc:
        logger.exception("Error generando dashboard REST")
        return JSONResponse(
            {"ok": False, "error": str(exc)},
            status_code=500,
        )


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))

    logger.info("Iniciando MCP en %s:%s", host, port)
    mcp.run(transport="sse", host=host, port=port)
