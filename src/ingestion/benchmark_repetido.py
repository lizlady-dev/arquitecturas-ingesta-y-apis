from pathlib import Path
import time
import pandas as pd

from src.ingestion.compare_lambda_kappa import (
    load_data,
    run_lambda,
    run_kappa,
)

NUM_REPETICIONES = 5
BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def ejecutar_y_extraer(funcion, datos):
    """
    Ejecuta una función y extrae su DataFrame,
    independientemente de los demás valores de retorno.
    """
    inicio = time.perf_counter()
    retorno = funcion(datos)
    duracion_ms = (time.perf_counter() - inicio) * 1000

    if isinstance(retorno, tuple):
        dataframe = next(
            (elemento for elemento in retorno
             if isinstance(elemento, pd.DataFrame)),
            None,
        )
    else:
        dataframe = retorno

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            f"{funcion.__name__} no devolvió un DataFrame."
        )

    return dataframe, duracion_ms


def medir(nombre, funcion, datos):
    # Calentamiento: no se incluye en las métricas.
    ejecutar_y_extraer(funcion, datos)

    resultados = []
    tiempos = []

    for numero in range(1, NUM_REPETICIONES + 1):
        resultado, tiempo_ms = ejecutar_y_extraer(funcion, datos)

        resultados.append(resultado)
        tiempos.append(tiempo_ms)

        print(
            f"{nombre} | Ejecución {numero}: "
            f"{tiempo_ms:.3f} ms"
        )

    return resultados, tiempos


def normalizar_resultado(df):
    """Ordena columnas y filas para comparar los resultados."""
    df = df.copy()
    df = df.reindex(sorted(df.columns), axis=1)
    df = df.sort_values(
        by=list(df.columns),
        na_position="last",
        ignore_index=True,
    )
    return df


def main():
    datos = load_data()
    cantidad = len(datos)

    print(f"Registros de entrada: {cantidad}")

    resultados_lambda, tiempos_lambda = medir(
        "Lambda", run_lambda, datos
    )
    resultados_kappa, tiempos_kappa = medir(
        "Kappa", run_kappa, datos
    )

    # Compara el resultado de cada implementación entre repeticiones.
    for resultado in resultados_lambda[1:]:
        pd.testing.assert_frame_equal(
            normalizar_resultado(resultados_lambda[0]),
            normalizar_resultado(resultado),
            check_dtype=False,
            check_exact=False,
            atol=0.01,
            rtol=0.0001,
        )

    for resultado in resultados_kappa[1:]:
        pd.testing.assert_frame_equal(
            normalizar_resultado(resultados_kappa[0]),
            normalizar_resultado(resultado),
            check_dtype=False,
            check_exact=False,
            atol=0.01,
            rtol=0.0001,
        )

    # Compara Lambda y Kappa, siempre que sus resultados
    # tengan la misma estructura y representen la misma salida.
    pd.testing.assert_frame_equal(
        normalizar_resultado(resultados_lambda[0]),
        normalizar_resultado(resultados_kappa[0]),
        check_dtype=False,
        check_exact=False,
        atol=0.01,
        rtol=0.0001,
    )

    print("\nCorrecto: resultados consistentes entre repeticiones")
    print("y equivalentes entre Lambda y Kappa.")

    filas = []

    for nombre, tiempos in [
        ("Lambda", tiempos_lambda),
        ("Kappa", tiempos_kappa),
    ]:
        promedio = sum(tiempos) / len(tiempos)

        filas.append({
            "arquitectura": nombre,
            "registros": cantidad,
            "repeticiones": len(tiempos),
            "promedio_ms": promedio,
            "mediana_ms": pd.Series(tiempos).median(),
            "p95_ms": pd.Series(tiempos).quantile(0.95),
            "minimo_ms": min(tiempos),
            "maximo_ms": max(tiempos),
            "registros_por_segundo": (
                cantidad / (promedio / 1000)
            ),
        })

    resumen = pd.DataFrame(filas)
    salida = RESULTS_DIR / "benchmark_lambda_kappa_repetido3.csv"
    resumen.to_csv(salida, index=False, encoding="utf-8-sig")

    print("\nResumen del benchmark:")
    print(resumen.round(3).to_string(index=False))
    print(f"\nArchivo guardado en: {salida}")


if __name__ == "__main__":
    main()
