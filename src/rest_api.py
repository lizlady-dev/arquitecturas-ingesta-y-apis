
from fastapi import FastAPI, HTTPException
from src.db import get_sales_summary

app = FastAPI(
    title="BI Ventas - API REST",
    description="Consulta de indicadores de ventas almacenados en PostgreSQL",
    version="1.0.0",
)

@app.get("/")
def home():
    return {
        "proyecto": "Business Intelligence",
        "arquitectura": "REST",
        "estado": "activo",
    }

@app.get("/ventas/resumen")
def resumen_ventas():
    try:
        rows = get_sales_summary()
        return {
            "total_regiones": len(rows),
            "resultados": rows,
        }
    except Exception as exc:
        print(f"ERROR REAL DE REST: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
