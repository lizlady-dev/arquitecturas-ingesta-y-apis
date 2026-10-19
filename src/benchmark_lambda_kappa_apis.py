
import time
import statistics
from pathlib import Path

import requests
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

APIS = {
    "Lambda": "http://127.0.0.1:8002/ventas/resumen",
    "Kappa": "http://127.0.0.1:8003/ventas/resumen",
}

REPETICIONES = 100
CALENTAMIENTO = 5
TIMEOUT_SEGUNDOS = 10


def medir_solicitud(url):
    inicio = time.perf_counter()

    try:
        respuesta = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
        duracion_ms = (time.perf_counter() - inicio) * 1000

        return {
            "tiempo_ms": duracion_ms,
            "estado_http": respuesta.status_code,
            "correcta": respuesta.status_code == 200,
            "detalle": "",
        }

    except requests.RequestException as error:
        duracion_ms = (time.perf_counter() - inicio) * 1000

        return {
            "tiempo_ms": duracion_ms,
            "estado_http": 0,
            "correcta": False,
            "detalle": str(error),
        }


def main():
    registros = []

    print("Verificando y calentando las API...")

    for nombre, url in APIS.items():
        for _ in range(CALENTAMIENTO):
            resultado = medir_solicitud(url)

            if not resultado["correcta"]:
                raise RuntimeError(
                    f"La API {nombre} no responde correctamente. "
                    f"Revisa su terminal y la URL: {url}"
                )

    print(f"Iniciando benchmark: {REPETICIONES} solicitudes por API.")

    # Alternar el orden ayuda a reducir el efecto de ejecutar
    # siempre una arquitectura antes que la otra.
    for i in range(REPETICIONES):
        orden = list(APIS.items())

        if i % 2 == 1:
            orden.reverse()

        for nombre, url in orden:
            resultado = medir_solicitud(url)

            registros.append({
                "arquitectura": nombre,
                "repeticion": i + 1,
                **resultado,
            })

        if (i + 1) % 20 == 0:
            print(f"Completadas {i + 1} rondas de {REPETICIONES}.")

    detalle = pd.DataFrame(registros)

    archivo_detalle = RESULTS_DIR / "benchmark_lambda_kappa_detalle.csv"
    archivo_resumen = RESULTS_DIR / "benchmark_lambda_kappa_resumen.csv"

    detalle.to_csv(archivo_detalle, index=False, encoding="utf-8-sig")

    resumen = []

    for nombre in APIS:
        datos = detalle[
            (detalle["arquitectura"] == nombre)
            & (detalle["correcta"])
        ]["tiempo_ms"].tolist()

        total = len(
            detalle[detalle["arquitectura"] == nombre]
        )
        errores = total - len(datos)

        if datos:
            datos_ordenados = sorted(datos)
            indice_p95 = max(0, int(0.95 * len(datos)) - 1)

            resumen.append({
                "Arquitectura": nombre,
                "Solicitudes": total,
                "Correctas": len(datos),
                "Errores": errores,
                "Promedio_ms": round(statistics.mean(datos), 3),
                "Mediana_ms": round(statistics.median(datos), 3),
                "P95_ms": round(datos_ordenados[indice_p95], 3),
                "Minimo_ms": round(min(datos), 3),
                "Maximo_ms": round(max(datos), 3),
            })

    tabla_resumen = pd.DataFrame(resumen)
    tabla_resumen.to_csv(
        archivo_resumen, index=False, encoding="utf-8-sig"
    )

    print("\nRESULTADOS DEL BENCHMARK")
    print(tabla_resumen.to_string(index=False))

    print(f"\nDetalle guardado en: {archivo_detalle}")
    print(f"Resumen guardado en: {archivo_resumen}")


if __name__ == "__main__":
    main()
