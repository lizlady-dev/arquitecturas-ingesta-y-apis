import os
import statistics
from pathlib import Path
from time import perf_counter

import pandas as pd
import psycopg

# configuracion DE POSTGRESQL

DB_CONFIG = {
    "host": os.getenv("BI_DB_HOST", "localhost"),
    "port": int(os.getenv("BI_DB_PORT", "5432")),
    "dbname": os.getenv("BI_DB_NAME", "bi_ventas"),
    "user": os.getenv("BI_DB_USER", "postgres"),
    "password": os.environ["BI_DB_PASSWORD"],
}

TABLA = "ventas"
REPETICIONES = 10

BASE_DIR = Path(__file__).resolve().parents[1]
SALIDA_DIR = BASE_DIR / "results" / "procesamiento_nuevo"
SALIDA_DIR.mkdir(parents=True, exist_ok=True)


# lee datos de POSTGRESQL


def cargar_datos_postgresql():
    print("Conectando directamente a PostgreSQL...")

    with psycopg.connect(**DB_CONFIG) as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {TABLA}")
            filas = cursor.fetchall()
            columnas = [desc.name.lower() for desc in cursor.description]

    if not filas:
        raise ValueError(f"La tabla {TABLA} no contiene registros.")

    df = pd.DataFrame(filas, columns=columnas)

    print(f"Base de datos: {DB_CONFIG['dbname']}")
    print(f"Tabla consultada: {TABLA}")
    print(f"Registros leídos: {len(df)}")
    print(f"Columnas encontradas: {list(df.columns)}")

    return df

# indentifica columnas de venta

def buscar_columna(df, opciones, descripcion):
    for columna in opciones:
        if columna in df.columns:
            return columna

    raise ValueError(
        f"No se encontró la columna de {descripcion}.\n"
        f"Columnas disponibles: {list(df.columns)}\n"
        f"Columnas candidatas: {opciones}"
    )


def preparar_datos(df):
    region_col = buscar_columna(
        df,
        ["region", "región", "zona"],
        "región",
    )

    cantidad_col = buscar_columna(
        df,
        ["cantidad", "unidades", "unidades_vendidas", "qty", "quantity"],
        "cantidad o unidades",
    )

    # Si existe el importe de cada venta, lo utilizamos.
    # De lo contrario, calculamos cantidad * precio unitario.
    importe_col = next(
        (
            c for c in [
                "importe", "total_venta", "monto_venta",
                "subtotal", "ventas_totales", "total"
            ]
            if c in df.columns
        ),
        None,
    )

    precio_col = next(
        (
            c for c in [
                "precio_unitario", "precio", "unit_price", "price"
            ]
            if c in df.columns
        ),
        None,
    )

    if importe_col is None and precio_col is None:
        raise ValueError(
            "No se encontró una columna de importe total ni de precio "
            "unitario. Revisa las columnas impresas arriba."
        )

    datos = pd.DataFrame({
        "region": df[region_col],
        "cantidad": pd.to_numeric(df[cantidad_col], errors="raise"),
    })

    if importe_col is not None:
        datos["importe"] = pd.to_numeric(
            df[importe_col], errors="raise"
        )
        print(f"Importe calculado usando la columna: {importe_col}")
    else:
        precio = pd.to_numeric(df[precio_col], errors="raise")
        datos["importe"] = datos["cantidad"] * precio
        print(f"Importe calculado como cantidad * {precio_col}")

    if datos.isnull().any().any():
        raise ValueError(
            "Hay valores nulos en región, cantidad o importe. "
            "Revisa los datos antes de medir."
        )

    return datos

#  procesamiento lambda por lote

def procesar_lambda(datos):
    resultado = (
        datos.groupby("region", as_index=False)
        .agg(
            unidades_vendidas=("cantidad", "sum"),
            ventas_totales=("importe", "sum"),
            numero_registros=("region", "size"),
        )
        .sort_values("region")
        .reset_index(drop=True)
    )

    return resultado


# procesamiento secuencuial kappa


def procesar_kappa(datos):
    acumulados = {}

    for region, cantidad, importe in datos[
        ["region", "cantidad", "importe"]
    ].itertuples(index=False, name=None):

        if region not in acumulados:
            acumulados[region] = {
                "unidades_vendidas": 0,
                "ventas_totales": 0,
                "numero_registros": 0,
            }

        acumulados[region]["unidades_vendidas"] += cantidad
        acumulados[region]["ventas_totales"] += importe
        acumulados[region]["numero_registros"] += 1

    filas = [
        {
            "region": region,
            **valores,
        }
        for region, valores in acumulados.items()
    ]

    return (
        pd.DataFrame(filas)
        .sort_values("region")
        .reset_index(drop=True)
    )

# mide tiempo de procesamiento

def medir_procesamiento(funcion, datos):
    tiempos = []
    resultado = None

    for _ in range(REPETICIONES):
        inicio = perf_counter()
        resultado = funcion(datos)
        fin = perf_counter()

        tiempos.append(fin - inicio)

    return resultado, tiempos


def crear_metricas(nombre, tiempos, cantidad_registros):
    ordenados = sorted(tiempos)
    indice_p95 = max(0, int(0.95 * len(ordenados)) - 1)
    promedio = statistics.mean(tiempos)

    return {
        "Arquitectura": nombre,
        "Repeticiones": len(tiempos),
        "Registros": cantidad_registros,
        "Promedio_ms": round(promedio * 1000, 3),
        "Mediana_ms": round(statistics.median(tiempos) * 1000, 3),
        "P95_ms": round(ordenados[indice_p95] * 1000, 3),
        "Minimo_ms": round(min(tiempos) * 1000, 3),
        "Maximo_ms": round(max(tiempos) * 1000, 3),
        "Registros_por_segundo": round(
            cantidad_registros / promedio, 2
        ) if promedio > 0 else None,
    }

# 6. exjuta y valida

def main():
    # La conexión y lectura se realizan antes del cronómetro.
    datos_originales = cargar_datos_postgresql()
    datos = preparar_datos(datos_originales)

    print(f"\nRegistros preparados: {len(datos)}")
    print(f"Regiones distintas: {datos['region'].nunique()}")

    # Calentamiento excluido de las mediciones.
    procesar_lambda(datos)
    procesar_kappa(datos)

    print(f"\nEjecutando {REPETICIONES} repeticiones por prototipo...")

    resultado_lambda, tiempos_lambda = medir_procesamiento(
        procesar_lambda, datos
    )

    resultado_kappa, tiempos_kappa = medir_procesamiento(
        procesar_kappa, datos
    )

    # Confirmar que los dos métodos producen los mismos indicadores.
    pd.testing.assert_frame_equal(
        resultado_lambda,
        resultado_kappa,
        check_dtype=False,
        check_exact=False,
        rtol=1e-9,
        atol=1e-6,
    )

    print("\nVALIDACIÓN CORRECTA: ambos resultados coinciden.")

    resumen = pd.DataFrame([
        crear_metricas("Lambda", tiempos_lambda, len(datos)),
        crear_metricas("Kappa", tiempos_kappa, len(datos)),
    ])

    resumen.to_csv(
        SALIDA_DIR / "resumen_procesamiento.csv",
        index=False,
        encoding="utf-8-sig",
    )

    resultado_lambda.to_csv(
        SALIDA_DIR / "resultado_lambda.csv",
        index=False,
        encoding="utf-8-sig",
    )

    resultado_kappa.to_csv(
        SALIDA_DIR / "resultado_kappa.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("\nRESULTADOS DEL PROCESAMIENTO")
    print(resumen.to_string(index=False))

    print(f"\nArchivos nuevos guardados en: {SALIDA_DIR}")


if __name__ == "__main__":
    main()
