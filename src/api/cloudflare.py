from src.config import env, fetch

CF_HEADERS = {
    "X-Auth-Email": env.CF_EMAIL,
    "X-Auth-Key": env.CF_API_KEY,
    "Content-Type": "application/json",
}


async def update_worker(name: str, script: str):
    """
    Update a worker.
    """
    payload = {"name": name, "script": script}
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/workers/scripts/{name}",
        method="PUT",
        headers=CF_HEADERS,
        json=payload,
    )

async def invoke_worker(name: str):
    """
    Invoke a worker.
    """
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/workers/scripts/{name}/subdomain",
        method="POST",
        headers=CF_HEADERS,
    )

async def get_workers():
    """
    Get all workers.
    """
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/workers/scripts",
        headers=CF_HEADERS,
    )

async def create_worker(name: str, script: str):
    """
    Create a worker.
    """
    payload = {"name": name, "script": script}
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/workers/scripts",
        method="POST",
        headers=CF_HEADERS,
        json=payload,
    )

async def delete_worker(name: str):
    """
    Delete a worker.
    """
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/workers/scripts/{name}",
        method="DELETE",
        headers=CF_HEADERS,
    )

async def create_dns_record(name: str):
    """
    Create a record.
    """
    payload =  {"type": "A", "name": name, "content": env.DOCKER_IP, "ttl": 1, "proxied": True}
    
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/dns_records",
        "POST",
        headers=CF_HEADERS,
        json=payload,
    )

async def get_dns_records():
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/dns_records",
        headers=CF_HEADERS,
    )

async def delete_dns_record(record_id: str):
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/dns_records/{record_id}",
        "DELETE",
        headers=CF_HEADERS,
    )

async def update_dns_record(record_id: str, name: str):
    payload = {"type": "A", "name": name, "content": env.DOCKER_IP, "ttl": 1, "proxied": True}
    return await fetch(
        f"https://api.cloudflare.com/client/v4/zones/{env.CF_ZONE_ID}/dns_records/{record_id}",
        "PUT",
        headers=CF_HEADERS,
        json=payload,
    )
