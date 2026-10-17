
import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from src.db import get_sales_summary


@strawberry.type
class ResumenVenta:
    region: str
    unidades_vendidas: int
    ventas_totales: float
    numero_registros: int


@strawberry.type
class Query:
    @strawberry.field
    def resumen_ventas(self) -> list[ResumenVenta]:
        rows = get_sales_summary()

        return [
            ResumenVenta(
                region=row["region"],
                unidades_vendidas=row["unidades_vendidas"],
                ventas_totales=float(row["ventas_totales"]),
                numero_registros=row["numero_registros"],
            )
            for row in rows
        ]


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)

app = FastAPI(
    title="BI Ventas - API GraphQL",
    version="1.0.0",
)

app.include_router(graphql_app, prefix="/graphql")
