
from pathlib import Path
import time
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
CSV_FILE = BASE_DIR / "data" / "ventas_benchmark.csv"
RESULTS_DIR = BASE_DIR / "results"

REQUIRED_COLUMNS = {
    "fecha", "producto", "region", "cantidad", "precio"
}


def load_data():
    df = pd.read_csv(CSV_FILE)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas: {missing}")

    if df[list(REQUIRED_COLUMNS)].isnull().any().any():
        raise ValueError("Existen campos vacíos.")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="raise")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="raise")
    df["precio"] = pd.to_numeric(df["precio"], errors="raise")

    if (df["cantidad"] <= 0).any() or (df["precio"] < 0).any():
        raise ValueError("Hay cantidades o precios inválidos.")

    df["importe"] = df["cantidad"] * df["precio"]
    return df


def summarize(df):
    return (
        df.groupby("region", as_index=False)
        .agg(
            unidades_vendidas=("cantidad", "sum"),
            ventas_totales=("importe", "sum"),
            registros=("producto", "count")
        )
        .sort_values("region")
        .reset_index(drop=True)
    )



def run_lambda(df):
    """Prototipo Lambda: batch histórico + vía rápida."""

    start = time.perf_counter()

    split = max(1, int(len(df) * 0.67))
    historical = df.iloc[:split]
    recent = df.iloc[split:]

    # Vía batch: resumen del conjunto histórico.
    batch_result = summarize(historical)

    # Vía speed: resumen de los eventos recientes.
    if recent.empty:
        speed_result = pd.DataFrame(columns=batch_result.columns)
    else:
        speed_result = summarize(recent)

    # Capa de servicio: combinar ambas agregaciones.
    combined = pd.concat(
        [batch_result, speed_result],
        ignore_index=True
    )

    final_result = (
        combined.groupby("region", as_index=False)
        .agg(
            unidades_vendidas=("unidades_vendidas", "sum"),
            ventas_totales=("ventas_totales", "sum"),
            registros=("registros", "sum")
        )
        .sort_values("region")
        .reset_index(drop=True)
    )

    elapsed = time.perf_counter() - start
    return final_result, elapsed, len(batch_result)


def run_kappa(df):
    """Prototipo Kappa: reprocesamiento secuencial de eventos."""

    start = time.perf_counter()

    totals = {}

    # Cada fila representa un evento de venta.
    for row in df.itertuples(index=False):
        region = row.region

        if region not in totals:
            totals[region] = {
                "unidades_vendidas": 0,
                "ventas_totales": 0.0,
                "registros": 0
            }

        totals[region]["unidades_vendidas"] += int(row.cantidad)
        totals[region]["ventas_totales"] += float(row.importe)
        totals[region]["registros"] += 1

    result = pd.DataFrame([
        {
            "region": region,
            **values
        }
        for region, values in totals.items()
    ])

    result = result.sort_values("region").reset_index(drop=True)
    result["ventas_totales"] = result["ventas_totales"].round(2)

    elapsed = time.perf_counter() - start
    return result, elapsed


def main():
    df = load_data()

    lambda_result, lambda_seconds, batch_regions = run_lambda(df)
    kappa_result, kappa_seconds = run_kappa(df)

    lambda_result["ventas_totales"] = (
        lambda_result["ventas_totales"].round(2)
    )
    kappa_result["ventas_totales"] = (
        kappa_result["ventas_totales"].round(2)
    )

    # Verificar que ambas arquitecturas produzcan
    # los mismos resultados agregados.
    pd.testing.assert_frame_equal(
        lambda_result,
        kappa_result,
        check_dtype=False,
        check_exact=False,
        atol=0.01
    )

    lambda_dir = RESULTS_DIR / "lambda"
    kappa_dir = RESULTS_DIR / "kappa"
    lambda_dir.mkdir(parents=True, exist_ok=True)
    kappa_dir.mkdir(parents=True, exist_ok=True)

    lambda_result.to_csv(
        lambda_dir / "resumen.csv", index=False
    )
    kappa_result.to_csv(
        kappa_dir / "resumen.csv", index=False
    )

    benchmark = pd.DataFrame([
        {
            "arquitectura": "Lambda (prototipo)",
            "registros": len(df),
            "tiempo_segundos": lambda_seconds
        },
        {
            "arquitectura": "Kappa (prototipo)",
            "registros": len(df),
            "tiempo_segundos": kappa_seconds
        }
    ])

    benchmark.to_csv(
        RESULTS_DIR / "benchmark_ingesta.csv",
        index=False
    )

    print("\n=== COMPARACIÓN LAMBDA Y KAPPA ===")
    print(f"Registros procesados: {len(df)}")
    print("Verificación: ambas salidas coinciden.")
    print(f"Regiones calculadas en capa batch: {batch_regions}")

    print("\nLambda:")
    print(lambda_result.to_string(index=False))
    print(f"Tiempo: {lambda_seconds:.6f} segundos")

    print("\nKappa:")
    print(kappa_result.to_string(index=False))
    print(f"Tiempo: {kappa_seconds:.6f} segundos")

    print("\nBenchmark:")
    print(benchmark.to_string(index=False))
    print(f"\nResultados guardados en: {RESULTS_DIR}")


if __name__ == "__main__":
    main()