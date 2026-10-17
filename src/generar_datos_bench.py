from pathlib import Path
import random
import pandas as pd

# Configuración reproducible
SEMILLA = 42
NUM_REGISTROS = 50_000

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ARCHIVO_SALIDA = DATA_DIR / "ventas_benchmark.csv"

random.seed(SEMILLA)

def generar_datos():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    productos = {
        "Laptop": 2500.00,
        "Mouse": 45.00,
        "Teclado": 120.00,
        "Monitor": 850.00,
        "Impresora": 680.00,
    }

    regiones = ["Puno", "Juliaca", "Arequipa", "Cusco", "Tacna"]

    registros = []

    for i in range(NUM_REGISTROS):
        producto = random.choice(list(productos.keys()))
        cantidad = random.randint(1, 10)

        registros.append({
            "evento_id": i + 1,
            "fecha": (
                pd.Timestamp("2026-01-01")
                + pd.Timedelta(days=random.randint(0, 289))
            ).date().isoformat(),
            "producto": producto,
            "region": random.choice(regiones),
            "cantidad": cantidad,
            "precio": productos[producto],
        })

    df = pd.DataFrame(registros)

    df.to_csv(
        ARCHIVO_SALIDA,
        index=False,
        encoding="utf-8-sig",
    )

    print("=== GENERACIÓN DE DATOS COMPLETADA ===")
    print(f"Registros generados: {len(df)}")
    print(f"Semilla aleatoria: {SEMILLA}")
    print(f"Productos: {df['producto'].nunique()}")
    print(f"Regiones: {df['region'].nunique()}")
    print(f"Archivo generado: {ARCHIVO_SALIDA}")

    print("\nPrimeros cinco registros:")
    print(df.head().to_string(index=False))

    print("\nResumen de control:")
    print(f"Unidades totales: {df['cantidad'].sum()}")
    print(
        "Importe total: S/ "
        f"{(df['cantidad'] * df['precio']).sum():,.2f}"
    )


if __name__ == "__main__":
    generar_datos()