
import os
from pathlib import Path

import pandas as pd
import psycopg

BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG = {
    "host": os.getenv("BI_DB_HOST", "localhost"),
    "port": int(os.getenv("BI_DB_PORT", "5432")),
    "dbname": os.getenv("BI_DB_NAME", "bi_ventas"),
    "user": os.getenv("BI_DB_USER", "postgres"),
    "password": os.environ["BI_DB_PASSWORD"],
}

TABLES = {
    "lambda": BASE_DIR / "results" / "lambda" / "resumen.csv",
    "kappa": BASE_DIR / "results" / "kappa" / "resumen.csv",
}


def cargar_resultado(nombre, archivo):
    if not archivo.exists():
        raise FileNotFoundError(
            f"No existe {archivo}. Ejecuta primero la comparación Lambda/Kappa."
        )

    df = pd.read_csv(archivo)

    columnas = [
        "region",
        "unidades_vendidas",
        "ventas_totales",
        "registros",
    ]

    faltantes = set(columnas) - set(df.columns)
    if faltantes:
        raise ValueError(
            f"Al archivo {archivo.name} le faltan columnas: {faltantes}"
        )

    tabla = f"{nombre}_resultados"

    with psycopg.connect(**CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {tabla}")

            for row in df[columnas].itertuples(index=False, name=None):
                cur.execute(
                    f"""
                    INSERT INTO {tabla}
                    (region, unidades_vendidas, ventas_totales, numero_registros)
                    VALUES (%s, %s, %s, %s)
                    """,
                    row,
                )

    print(f"{nombre.upper()}: {len(df)} regiones cargadas en {tabla}.")


def main():
    for nombre, archivo in TABLES.items():
        cargar_resultado(nombre, archivo)

    print("Carga de resultados completada.")


if __name__ == "__main__":
    main()
