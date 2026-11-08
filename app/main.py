from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="DevOps API", version="1.0.0")
# Stockage en mémoire : clé = id de l'item, valeur = données de l'item
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