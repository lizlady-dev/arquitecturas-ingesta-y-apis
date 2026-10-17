
from pathlib import Path
import time
import pandas as pd

# Directorio principal del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"

DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

ARCHIVO_ENTRADA = DATA_DIR / "ventas.csv"
ARCHIVO_SALIDA = RESULTS_DIR / "ventas_resumen.csv"


def generar_datos_ejemplo():
    """Genera datos ficticios si todavía no existe el CSV."""
    if ARCHIVO_ENTRADA.exists():
        print("Se utilizará el archivo de ventas existente.")
        return

    datos = [
        {"fecha": "2026-10-01", "producto": "Laptop",
         "region": "Puno", "cantidad": 2, "precio": 2500.0},
        {"fecha": "2026-10-01", "producto": "Mouse",
         "region": "Puno", "cantidad": 5, "precio": 45.0},
        {"fecha": "2026-10-02", "producto": "Teclado",
         "region": "Juliaca", "cantidad": 3, "precio": 120.0},
        {"fecha": "2026-10-02", "producto": "Laptop",
         "region": "Juliaca", "cantidad": 1, "precio": 2500.0},
        {"fecha": "2026-10-03", "producto": "Mouse",
         "region": "Puno", "cantidad": 4, "precio": 45.0},
        {"fecha": "2026-10-03", "producto": "Monitor",
         "region": "Juliaca", "cantidad": 2, "precio": 850.0},
    ]

    pd.DataFrame(datos).to_csv(
        ARCHIVO_ENTRADA, index=False, encoding="utf-8"
    )
    print(f"Datos de ejemplo creados: {ARCHIVO_ENTRADA}")


def procesar_ventas():
    inicio = time.perf_counter()

    df = pd.read_csv(ARCHIVO_ENTRADA)

    # Validar las columnas necesarias
    columnas = {
        "fecha", "producto", "region", "cantidad", "precio"
    }

    if not columnas.issubset(df.columns):
        faltantes = columnas - set(df.columns)
        raise ValueError(f"Faltan columnas: {faltantes}")

    if df[list(columnas)].isnull().any().any():
        raise ValueError("Hay campos vacíos en los datos.")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="raise")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="raise")
    df["precio"] = pd.to_numeric(df["precio"], errors="raise")

    if (df["cantidad"] <= 0).any() or (df["precio"] < 0).any():
        raise ValueError("Hay cantidades o precios inválidos.")

    # Transformar los datos para el análisis
    df["importe"] = df["cantidad"] * df["precio"]

    resumen = (
        df.groupby("region", as_index=False)
        .agg(
            unidades_vendidas=("cantidad", "sum"),
            ventas_totales=("importe", "sum"),
            numero_registros=("producto", "count")
        )
    )

    resumen["ventas_totales"] = resumen["ventas_totales"].round(2)
    resumen.to_csv(ARCHIVO_SALIDA, index=False, encoding="utf-8")

    duracion = time.perf_counter() - inicio

    print("\n=== RESULTADOS DE LA INGESTA ===")
    print(f"Registros procesados: {len(df)}")
    print(f"Regiones analizadas: {df['region'].nunique()}")
    print(f"Ventas totales: S/ {df['importe'].sum():,.2f}")
    print(f"Tiempo de procesamiento: {duracion:.6f} segundos")
    print(f"Resumen guardado en: {ARCHIVO_SALIDA}")
    print("\nResumen por región:")
    print(resumen.to_string(index=False))


if __name__ == "__main__":
    generar_datos_ejemplo()
    procesar_ventas()