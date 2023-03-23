from fastapi import APIRouter
from src.api.cloudflare import (
        create_dns_record,
        get_dns_records,
        delete_dns_record,
        update_dns_record
)

app = APIRouter()

@app.get("/dns")
async def get_all_dns_records():
    return await get_dns_records()

@app.post("/dns")
async def create_new_dns_record(name: str):
    return await create_dns_record(name)

@app.put("/dns/{dns}")
async def update_dns_record_by_id(dns: str, name: str):
    return await update_dns_record(dns, name)

@app.delete("/dns/{dns}")
async def delete_dns_record_by_id(dns: str):
    return await delete_dns_record(dns)
