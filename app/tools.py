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


def top_productos_por_zona(anio: int = 2025) -> dict[str, Any]:
    """
    Devuelve el producto con mayor TOTALREV por cada SALESZONE para un año dado.
    Usa SQL simple compatible con IBM i y resuelve el ranking en Python.
    """
    sql = f"""
        SELECT
            SALESZONE,
            PRODUCT,
            SUM(TOTALREV) AS TOTAL_VENTAS,
            SUM(QTY) AS TOTAL_QTY,
            SUM(TOTALCOST) AS TOTAL_COSTO,
            SUM(TOTALREV - TOTALCOST) AS MARGEN
        FROM {_qualified_table()}
        WHERE YEAR(ORDERDATE) = ?
        GROUP BY SALESZONE, PRODUCT
        ORDER BY SALESZONE, TOTAL_VENTAS DESC
    """

    rows = execute_query(sql, [anio])

    mejores_por_zona: dict[str, dict[str, Any]] = {}

    for row in rows:
        zona = str(row.get("SALESZONE", "")).strip()
        producto = str(row.get("PRODUCT", "")).strip()

        total_ventas = float(row.get("TOTAL_VENTAS") or 0)
        total_qty = int(row.get("TOTAL_QTY") or 0)
        total_costo = float(row.get("TOTAL_COSTO") or 0)
        margen = float(row.get("MARGEN") or 0)

        if zona not in mejores_por_zona:
            mejores_por_zona[zona] = {
                "SALESZONE": zona,
                "PRODUCT": producto,
                "TOTAL_VENTAS": round(total_ventas, 2),
                "TOTAL_QTY": total_qty,
                "TOTAL_COSTO": round(total_costo, 2),
                "MARGEN": round(margen, 2),
            }

    return {
        "ok": True,
        "anio": anio,
        "total_zonas": len(mejores_por_zona),
        "rows": list(mejores_por_zona.values()),
    }


def dashboard_ventas(anio: int | None = None) -> dict[str, Any]:
    where = ""
    params = []

    if anio:
        where = "WHERE YEAR(ORDERDATE) = ?"
        params.append(anio)

    kpis = execute_query(
        f"""
        SELECT
            SUM(TOTALREV) AS TOTAL_VENTAS,
            SUM(TOTALCOST) AS TOTAL_COSTO,
            SUM(TOTALREV - TOTALCOST) AS MARGEN,
            SUM(QTY) AS UNIDADES,
            DECIMAL(SUM(TOTALREV) / NULLIF(SUM(QTY), 0), 15, 2) AS TICKET_PROMEDIO
        FROM {_qualified_table()}
        {where}
    """,
        params,
    )

    ventas_zona = execute_query(
        f"""
        SELECT SALESZONE, SUM(TOTALREV) AS TOTAL_VENTAS
        FROM {_qualified_table()}
        {where}
        GROUP BY SALESZONE
        ORDER BY TOTAL_VENTAS DESC
    """,
        params,
    )

    ventas_pais = execute_query(
        f"""
        SELECT COUNTRY, SUM(TOTALREV) AS TOTAL_VENTAS
        FROM {_qualified_table()}
        {where}
        GROUP BY COUNTRY
        ORDER BY TOTAL_VENTAS DESC
    """,
        params,
    )

    top_productos = execute_query(
        f"""
        SELECT PRODUCT, SUM(TOTALREV) AS TOTAL_VENTAS, SUM(QTY) AS UNIDADES
        FROM {_qualified_table()}
        {where}
        GROUP BY PRODUCT
        ORDER BY TOTAL_VENTAS DESC
        FETCH FIRST 10 ROWS ONLY
    """,
        params,
    )

    margen_producto = execute_query(
        f"""
        SELECT PRODUCT, SUM(TOTALREV - TOTALCOST) AS MARGEN
        FROM {_qualified_table()}
        {where}
        GROUP BY PRODUCT
        ORDER BY MARGEN DESC
        FETCH FIRST 10 ROWS ONLY
    """,
        params,
    )

    mensual = execute_query(
        f"""
        SELECT
            YEAR(ORDERDATE) AS ANIO,
            MONTH(ORDERDATE) AS MES,
            SUM(TOTALREV) AS TOTAL_VENTAS,
            SUM(TOTALREV - TOTALCOST) AS MARGEN,
            SUM(QTY) AS UNIDADES
        FROM {_qualified_table()}
        {where}
        GROUP BY YEAR(ORDERDATE), MONTH(ORDERDATE)
        ORDER BY ANIO, MES
    """,
        params,
    )

    return {
        "ok": True,
        "anio": anio,
        "kpis": kpis[0] if kpis else {},
        "ventas_por_zona": ventas_zona,
        "ventas_por_pais": ventas_pais,
        "top_productos": top_productos,
        "margen_por_producto": margen_producto,
        "evolucion_mensual": mensual,
    }
