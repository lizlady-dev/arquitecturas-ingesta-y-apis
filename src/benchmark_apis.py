import time
import statistics
from pathlib import Path

import pandas as pd
import requests

REST_URL = "http://127.0.0.1:8000/ventas/resumen"
GRAPHQL_URL = "http://127.0.0.1:8001/graphql"
REPETICIONES = 100
TIMEOUT = 10

GRAPHQL_QUERY = {
    "query": """
    query {
      resumenVentas {
        region
        unidadesVendidas
        ventasTotales
        numeroRegistros
      }
    }
    """
}


def medir_rest():
    inicio = time.perf_counter()
    respuesta = requests.get(REST_URL, timeout=TIMEOUT)
    tiempo_ms = (time.perf_counter() - inicio) * 1000
    respuesta.raise_for_status()
    datos = respuesta.json()
    assert datos["total_regiones"] == 2
    assert len(datos["resultados"]) == 2
    return tiempo_ms


def medir_graphql():
    inicio = time.perf_counter()
    respuesta = requests.post(
        GRAPHQL_URL,
        json=GRAPHQL_QUERY,
        timeout=TIMEOUT,
    )
    tiempo_ms = (time.perf_counter() - inicio) * 1000
    respuesta.raise_for_status()
    datos = respuesta.json()
    if "errors" in datos:
        raise RuntimeError(f"Error GraphQL: {datos['errors']}")
    assert len(datos["data"]["resumenVentas"]) == 2
    return tiempo_ms


def resumir(nombre, tiempos):
    ordenados = sorted(tiempos)
    indice_p95 = max(0, int(0.95 * len(ordenados)) - 1)
    return {
        "API": nombre,
        "Solicitudes": len(tiempos),
        "Tiempo promedio (ms)": round(statistics.mean(tiempos), 3),
        "Mediana (ms)": round(statistics.median(tiempos), 3),
        "P95 (ms)": round(ordenados[indice_p95], 3),
        "Mínimo (ms)": round(min(tiempos), 3),
        "Máximo (ms)": round(max(tiempos), 3),
    }


def main():
    print("Verificando disponibilidad de las API...")
    requests.get("http://127.0.0.1:8000/", timeout=TIMEOUT).raise_for_status()
    requests.get("http://127.0.0.1:8001/graphql", timeout=TIMEOUT).raise_for_status()

    tiempos_rest = []
    tiempos_graphql = []

    print(f"Ejecutando {REPETICIONES} solicitudes por API...")
    for i in range(REPETICIONES):
        # Alterna el orden en cada repetición para reducir el sesgo del orden.
        if i % 2 == 0:
            tiempos_rest.append(medir_rest())
            tiempos_graphql.append(medir_graphql())
        else:
            tiempos_graphql.append(medir_graphql())
            tiempos_rest.append(medir_rest())

    df = pd.DataFrame([
        resumir("REST", tiempos_rest),
        resumir("GraphQL", tiempos_graphql),
    ])

    carpeta = Path("results")
    carpeta.mkdir(parents=True, exist_ok=True)
    salida = carpeta / "benchmark_apis_3.csv"
    df.to_csv(salida, index=False, encoding="utf-8-sig")

    print("\nResultados del benchmark:")
    print(df.to_string(index=False))
    print(f"\nResultados guardados en: {salida.resolve()}")
    print(
        "\nImportante: son mediciones locales de este equipo y esta carga. "
        "No deben interpretarse como rendimiento universal en producción."
    )


if __name__ == "__main__":
    main()
