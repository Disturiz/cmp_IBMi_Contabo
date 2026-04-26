"""
Herramientas de negocio read-only para la tabla VENTASPF.
"""

from __future__ import annotations

from typing import Any
import os
import re

from dotenv import load_dotenv

# 🔥 IMPORT CORREGIDO
from app.db import IBMI_LIBRARY, IBMI_TABLE, execute_query

load_dotenv()

CLIENT_COLUMN = os.getenv("IBMI_CLIENT_COLUMN", "CLIENTE")
PRODUCT_COLUMN = os.getenv("IBMI_PRODUCT_COLUMN", "PRODUCTO")
DEFAULT_ORDER_COLUMN = os.getenv("IBMI_DEFAULT_ORDER_COLUMN", "")

SAFE_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_#$@]*$", re.IGNORECASE)


def _qualified_table() -> str:
    return f"{IBMI_LIBRARY}/{IBMI_TABLE}"


def _validate_identifier(name: str, label: str = "identificador") -> str:
    if not name:
        raise ValueError(f"El {label} no puede estar vacío.")
    if not SAFE_IDENTIFIER.match(name):
        raise ValueError(f"El {label} '{name}' no es válido o seguro.")
    return name.upper()


def _safe_limit(limite: int, max_value: int = 200) -> int:
    if limite < 1:
        return 1
    return min(limite, max_value)


# =========================
# 🔧 TOOLS BASE
# =========================


def healthcheck() -> dict[str, Any]:
    sql = "SELECT CURRENT DATE AS FECHA_ACTUAL, CURRENT TIME AS HORA_ACTUAL FROM SYSIBM/SYSDUMMY1"
    rows = execute_query(sql)

    return {
        "ok": True,
        "host": os.getenv("IBMI_HOST", "pub400.com"),
        "library": IBMI_LIBRARY,
        "table": IBMI_TABLE,
        "connection_test": rows[0] if rows else {},
    }


def listar_columnas() -> dict[str, Any]:
    sql = f"SELECT * FROM {_qualified_table()} FETCH FIRST 1 ROW ONLY"
    rows = execute_query(sql)

    columnas = list(rows[0].keys()) if rows else []

    return {
        "ok": True,
        "columns": columnas,
    }


def listar_muestras(limite: int = 5) -> dict[str, Any]:
    limite = _safe_limit(limite, max_value=20)

    sql = f"SELECT * FROM {_qualified_table()} FETCH FIRST {limite} ROWS ONLY"
    rows = execute_query(sql)

    return {
        "ok": True,
        "total": len(rows),
        "rows": rows,
    }


def contar_registros() -> dict[str, Any]:
    sql = f"SELECT COUNT(*) AS TOTAL FROM {_qualified_table()}"
    rows = execute_query(sql)

    total = rows[0]["TOTAL"] if rows else 0

    return {
        "ok": True,
        "total": total,
    }


# =========================
# 🔎 CONSULTA PRINCIPAL
# =========================


def consultar_ventas(
    limite: int = 20,
    cliente: str | None = None,
    producto: str | None = None,
    order_by: str | None = None,
    descending: bool = True,
) -> dict[str, Any]:

    limite = _safe_limit(limite)

    cliente_col = _validate_identifier(CLIENT_COLUMN)
    producto_col = _validate_identifier(PRODUCT_COLUMN)

    sql = f"SELECT * FROM {_qualified_table()} WHERE 1=1"
    params: list[Any] = []

    if cliente:
        sql += f" AND UPPER(CHAR({cliente_col})) LIKE ?"
        params.append(f"%{cliente.upper()}%")

    if producto:
        sql += f" AND UPPER(CHAR({producto_col})) LIKE ?"
        params.append(f"%{producto.upper()}%")

    if order_by:
        order_by = _validate_identifier(order_by)
        direction = "DESC" if descending else "ASC"
        sql += f" ORDER BY {order_by} {direction}"

    sql += f" FETCH FIRST {limite} ROWS ONLY"

    rows = execute_query(sql, params)

    return {
        "ok": True,
        "total": len(rows),
        "rows": rows,
    }


def resumen_por_producto(limite: int = 10) -> dict[str, Any]:
    limite = _safe_limit(limite, max_value=100)

    producto_col = _validate_identifier(PRODUCT_COLUMN)

    sql = f"""
        SELECT
            PRODUCT,
            SUM(TOTALREV) AS TOTAL_INGRESO
        FROM {TABLE_NAME}
        GROUP BY PRODUCT
        ORDER BY TOTAL_INGRESO DESC
        FETCH FIRST {limite} ROWS ONLY
    """

    rows = execute_query(sql)

    return {
        "ok": True,
        "total": len(rows),
        "rows": rows,
    }


def ventas_por_pais():
    sql = f"""
        SELECT COUNTRY, SUM(TOTALREV) AS TOTAL_VENTAS
        FROM VENTAPF
        GROUP BY COUNTRY
        ORDER BY TOTAL_VENTAS DESC
    """

    return execute_query(sql)


def ejecutar_sql_select(sql: str, limite: int = 100) -> dict:
    sql_clean = sql.strip().rstrip(";")

    prohibidas = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "MERGE",
        "CALL",
        "GRANT",
        "REVOKE",
    ]

    sql_upper = sql_clean.upper()

    if not sql_upper.startswith("SELECT"):
        return {"ok": False, "error": "Solo se permiten consultas SELECT"}

    for palabra in prohibidas:
        if palabra in sql_upper:
            return {"ok": False, "error": f"Consulta no permitida: contiene {palabra}"}

    if "FETCH FIRST" not in sql_upper and "LIMIT" not in sql_upper:
        sql_clean = f"{sql_clean} FETCH FIRST {limite} ROWS ONLY"

    return execute_query(sql_clean)
