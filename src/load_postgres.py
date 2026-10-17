
from pathlib import Path
import getpass
import pandas as pd
import psycopg

BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVO_CSV = BASE_DIR / "data" / "ventas.csv"

# Parámetros de conexión local
HOST = "localhost"
PORT = 5432
DATABASE = "bi_ventas"
USER = "postgres"


def main():
    if not ARCHIVO_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {ARCHIVO_CSV}"
        )

    # La contraseña se solicita al ejecutar el programa.
    password = getpass.getpass("Contraseña de PostgreSQL: ")

    df = pd.read_csv(ARCHIVO_CSV)

    with psycopg.connect(
        host=HOST,
        port=PORT,
        dbname=DATABASE,
        user=USER,
        password=password
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    fecha DATE NOT NULL,
                    producto VARCHAR(100) NOT NULL,
                    region VARCHAR(100) NOT NULL,
                    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
                    precio NUMERIC(12, 2) NOT NULL CHECK (precio >= 0)
                );
            """)

            # Reiniciar la tabla para que cada ejecución
            # cargue una sola copia del CSV de ejemplo.
            cur.execute("TRUNCATE TABLE ventas RESTART IDENTITY;")

            filas = [
                (
                    pd.to_datetime(row.fecha).date(),
                    row.producto,
                    row.region,
                    int(row.cantidad),
                    float(row.precio)
                )
                for row in df.itertuples(index=False)
            ]

            cur.executemany("""
                INSERT INTO ventas
                    (fecha, producto, region, cantidad, precio)
                VALUES (%s, %s, %s, %s, %s);
            """, filas)

            cur.execute("""
                SELECT
                    region,
                    SUM(cantidad) AS unidades,
                    SUM(cantidad * precio) AS ventas_totales
                FROM ventas
                GROUP BY region
                ORDER BY region;
            """)

            resultados = cur.fetchall()

    print("\nDatos guardados correctamente en PostgreSQL.")
    print(f"Registros insertados: {len(df)}")
    print("\nResumen consultado desde la base de datos:")

    for region, unidades, ventas in resultados:
        print(
            f"{region}: {unidades} unidades, "
            f"S/ {ventas:,.2f}"
        )


if __name__ == "__main__":
    main()