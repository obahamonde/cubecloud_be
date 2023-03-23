from fastapi import APIRouter
from src.api.cloudflare import (
    create_worker,
    update_worker,
    invoke_worker,
    get_workers,
    delete_worker,
)

app = APIRouter()

@app.get("/workers", tags=["workers"])
async def get_all_workers():
    return await get_workers()

@app.post("/workers", tags=["workers"])
async def create_new_worker(name: str, script: str):
    return await create_worker(name, script)

@app.put("/workers/{worker}", tags=["workers"])
async def update_worker_by_id(worker: str, script: str):
    return await update_worker(worker, script)

@app.post("/workers/{worker}", tags=["workers"])
async def invoke_worker_by_id(worker: str):
    return await invoke_worker(worker)

@app.delete("/workers/{worker}", tags=["workers"])
async def delete_worker_by_id(worker: str):
    return await delete_worker(worker)  