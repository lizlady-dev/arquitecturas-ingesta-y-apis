
import os

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row

app = FastAPI(
    title="BI - API REST Kappa",
    description="Consulta de resultados de la arquitectura Kappa",
    version="1.0.0",
)


def consultar_resultados():
    with psycopg.connect(
        host=os.getenv("BI_DB_HOST", "localhost"),
        port=int(os.getenv("BI_DB_PORT", "5432")),
        dbname=os.getenv("BI_DB_NAME", "bi_ventas"),
        user=os.getenv("BI_DB_USER", "postgres"),
        password=os.environ["BI_DB_PASSWORD"],
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT region, unidades_vendidas,
                       ventas_totales, numero_registros
                FROM kappa_resultados
                ORDER BY region;
            """)
            filas = cur.fetchall()

    return [
        {
            "region": fila["region"],
            "unidades_vendidas": fila["unidades_vendidas"],
            "ventas_totales": float(fila["ventas_totales"]),
            "numero_registros": fila["numero_registros"],
        }
        for fila in filas
    ]


@app.get("/")
def inicio():
    return {"api": "Kappa", "estado": "activa"}


@app.get("/ventas/resumen")
def resumen():
    try:
        filas = consultar_resultados()
        return {
            "arquitectura": "Kappa",
            "total_regiones": len(filas),
            "resultados": filas,
        }
    except Exception as exc:
        print(f"Error API Kappa: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron consultar los resultados Kappa.",
        ) from exc
