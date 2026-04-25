"""Acceso JDBC de solo lectura a IBM i."""

from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from typing import Any
import os

import jaydebeapi
from dotenv import load_dotenv

load_dotenv()

IBMI_HOST = os.getenv("IBMI_HOST", "pub400.com")
IBMI_USER = os.getenv("IBMI_USER", "")
IBMI_PASSWORD = os.getenv("IBMI_PASSWORD", "")
IBMI_LIBRARY = os.getenv("IBMI_LIBRARY", "")
IBMI_TABLE = os.getenv("IBMI_TABLE", "VENTAPF")
JT400_JAR = os.getenv("JT400_JAR", "./drivers/jt400.jar")
IBMI_JDBC_URL = os.getenv(
    "IBMI_JDBC_URL",
    f"jdbc:as400://{IBMI_HOST};naming=system;errors=full;prompt=false;translate binary=false",
)


def _ensure_settings() -> None:
    missing = []
    if not IBMI_USER:
        missing.append("IBMI_USER")
    if not IBMI_PASSWORD:
        missing.append("IBMI_PASSWORD")
    if not IBMI_LIBRARY:
        missing.append("IBMI_LIBRARY")
    if not JT400_JAR:
        missing.append("JT400_JAR")

    if missing:
        raise RuntimeError(
            "Faltan variables obligatorias en .env: " + ", ".join(missing)
        )


@contextmanager
def get_connection():
    """Abre una conexión JDBC a IBM i."""
    _ensure_settings()

    conn = jaydebeapi.connect(
        "com.ibm.as400.access.AS400JDBCDriver",
        IBMI_JDBC_URL,
        [IBMI_USER, IBMI_PASSWORD],
        JT400_JAR,
    )
    try:
        yield conn
    finally:
        conn.close()



def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        # Convierte enteros exactos a int y el resto a float para facilitar JSON.
        return int(value) if value == value.to_integral_value() else float(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    return value



def rows_to_dicts(cursor) -> list[dict[str, Any]]:
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = {col: _json_safe(val) for col, val in zip(columns, row)}
        result.append(item)
    return result



def execute_query(sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    """Ejecuta una consulta SELECT y devuelve lista de diccionarios."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(sql, params or [])
            return rows_to_dicts(cur)
        finally:
            cur.close()
