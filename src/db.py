
import os
import psycopg
from psycopg.rows import dict_row


def get_connection():
    return psycopg.connect(
        host=os.getenv("BI_DB_HOST", "localhost"),
        port=int(os.getenv("BI_DB_PORT", "5432")),
        dbname=os.getenv("BI_DB_NAME", "bi_ventas"),
        user=os.getenv("BI_DB_USER", "postgres"),
        password=os.environ["BI_DB_PASSWORD"],
        row_factory=dict_row,
    )


def get_sales_summary():
    query = """
        SELECT
            region,
            SUM(cantidad)::INTEGER AS unidades_vendidas,
            SUM(cantidad * precio)::NUMERIC(12, 2) AS ventas_totales,
            COUNT(*)::INTEGER AS numero_registros
        FROM ventas
        GROUP BY region
        ORDER BY region;
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()
