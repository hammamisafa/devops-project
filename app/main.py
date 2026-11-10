import json
import logging
import time

from fastapi import FastAPI, HTTPException, Request
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel


# --- Logs structurés (JSON) ---
class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        data.update(getattr(record, "fields", {}))
        return json.dumps(data)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("api")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

# --- Tracing (OpenTelemetry, export console) ---
provider = TracerProvider(resource=Resource.create({"service.name": "devops-api"}))
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

app = FastAPI(title="DevOps API", version="1.0.0")

# --- Métriques Prometheus : expose GET /metrics ---
Instrumentator().instrument(app).expose(app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "unhandled error",
            extra={"fields": {"method": request.method, "path": request.url.path}},
        )
        raise
    trace_id = trace.get_current_span().get_span_context().trace_id
    logger.info(
        "request",
        extra={
            "fields": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "trace_id": format(trace_id, "032x"),
            }
        },
    )
    return response


# Après le middleware, pour que la trace soit active dans le log
FastAPIInstrumentor.instrument_app(app)

items: dict[int, dict] = {}


class Item(BaseModel):
    name: str
    price: float


@app.get("/health")
def health():
    """Utilisé par Kubernetes (probes) pour savoir si l'app est vivante."""
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return [{"id": i, **item} for i, item in items.items()]


@app.post("/items", status_code=201)
def create_item(item: Item):
    item_id = max(items, default=0) + 1
    items[item_id] = item.model_dump()
    return {"id": item_id, **items[item_id]}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"id": item_id, **items[item_id]}


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    del items[item_id]