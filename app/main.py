"""
Servidor MCP remoto para consultar la tabla VENTAPF en IBM i (PUB400).

Ejecución:
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

Luego usa:
    http://localhost:8000/sse
en ChatGPT Desktop
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# 🔥 IMPORT CORREGIDO
from app.tools import (
    contar_registros,
    consultar_ventas,
    healthcheck,
    listar_columnas,
    listar_muestras,
    resumen_por_producto,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("mcp_ibmi_ventapf")

# Inicialización MCP
mcp = FastMCP(
    "IBM i VENTAPF MCP",
    instructions=(
        "Servidor MCP de solo lectura para consultar la tabla VENTAPF en IBM i PUB400. "
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

# =========================
# 🔧 TOOLS MCP
# =========================


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


# =========================
# 🚀 APP MCP (SSE)
# =========================

app = mcp.sse_app()


# =========================
# ▶️ EJECUCIÓN LOCAL
# =========================

if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))

    logger.info(f"Iniciando MCP en {host}:{port}")
    mcp.run(transport="sse", host=host, port=port)
